from __future__ import annotations

from collections import defaultdict
from typing import Any

from hiddifypanel.models import ConfigEnum, hconfig
from loguru import logger

from hiddifypanel.database import db
from hiddifypanel.hutils.proxy.alpn_helpers import alpns_for_combo, download_alpns_for_l3
from hiddifypanel.models.custom_proxy import (
    CustomProxy,
    CustomProxyMode,
    normalize_custom_path,
    proxy_slug,
)

from .client_builder import build_all_client_configs
from .inbound_builder import (
    _path_keys,
    build_hiddify_inbound_template,
    build_xray_inbound_template,
    supports_hiddify_preset,
    supports_xray_preset,
)
from .proxy_matrix import ProxyCombination, iter_proxy_combinations

_CDN_TOKENS = frozenset({'direct', 'relay', 'cdn', 'fake', 'special'})

# v10 port formula: 5000 + proto_idx * 10 + transport_idx
_V10_PROTO_IDX: dict[str, int] = {'vless': 0, 'vmess': 1, 'trojan': 2}
_V10_TRANSPORT_IDX: dict[str, int] = {'ws': 0, 'grpc': 1, 'tcp': 2, 'httpupgrade': 3, 'xhttp': 4}
_L3_TAG_PREFIXES: dict[str, str] = {'reality': 'r', 'h3_quic': 'h3', 'tls_h2': 'h2', 'http': 'http'}


def _v10_inbound_port(combo: ProxyCombination) -> int | None:
    ip = _V10_PROTO_IDX.get(combo.proto.lower())
    is_ = _V10_TRANSPORT_IDX.get(combo.transport.lower())
    if ip is None or is_ is None:
        return None
    return 5000 + ip * 10 + is_


def _backend_tag(combo: ProxyCombination, core: str) -> str:
    proto = combo.proto.lower()
    transport = combo.transport.lower()
    l3 = combo.l3.lower()

    if core == 'xray' and proto in _V10_PROTO_IDX and transport in _V10_TRANSPORT_IDX:
        return f'v10-{proto}-{transport}'

    if transport == 'custom' or proto == transport:
        base = proto
    else:
        base = f'{proto}-{transport}'

    prefix = _L3_TAG_PREFIXES.get(l3, '')
    if prefix:
        base = f'{prefix}-{base}'
    return base


# Transports that carry HTTP/1.1 traffic (WebSocket upgrade, HTTP upgrade)
_H1_TRANSPORTS: frozenset[str] = frozenset({'ws', 'httpupgrade'})

# Transports where HAProxy routes by TLS SNI rather than HTTP path
_SNI_TRANSPORTS: frozenset[str] = frozenset({'shadowtls', 'faketls'})


def _haproxy_route(combo: ProxyCombination) -> str | None:
    """Explicit HAProxy routing type for this combo.

    'l7'  — routes by HTTP path (path_v10 map → -http backend)
    'sni' — routes by TLS SNI (sni map → TCP passthrough backend)
    None  — not routed through HAProxy (direct / per-domain port)
    """
    if combo.l3.lower() == 'reality':
        return None  # handled by per-domain port backends, not custom_proxies

    if combo.transport.lower() in _SNI_TRANSPORTS:
        return 'sni'

    return 'l7'


def _haproxy_proto(combo: ProxyCombination, route: str | None) -> str | None:
    """Explicit HAProxy backend protocol.

    'h1'  — HTTP/1.1 (WebSocket / HTTP Upgrade transports)
    'h2'  — HTTP/2 (gRPC, xHTTP, plain TCP-over-HTTP)
    'tcp' — raw TCP passthrough (SNI-routed proxies)
    None  — not applicable (not through HAProxy)
    """
    if route is None:
        return None
    if route == 'sni':
        return 'tcp'
    # l7 route: h1 for WebSocket/HTTPUpgrade, h2 for everything else
    if combo.transport.lower() in _H1_TRANSPORTS:
        return 'h1'
    dl = (combo.params.get('download') or {}).get('alpn', '')
    if dl == 'http/1.1':
        return 'h1'
    return 'h2'


def _http_alpn(combo: ProxyCombination) -> str:
    dl = (combo.params.get('download') or {}).get('alpn')
    if dl == 'http/1.1':
        return 'tls_h1'
    if dl == 'h2':
        return 'tls_h2'
    if dl == 'h3':
        return 'tls_h3'
    l3 = combo.l3
    if l3 == 'h3_quic':
        return 'tls_h3_quic'
    if l3 == 'tls_h2':
        return 'tls_h2'
    if l3 == 'http':
        return 'h2c'
    if l3 in ('tls', 'tls_h2_h1', 'reality'):
        return 'tls_h2_h1'
    return 'tls_h2'


def _domain_modes(cdn: str) -> list[str]:
    normalized = (cdn or 'direct').lower()
    if normalized == 'cdn':
        return ['cdn']
    if normalized in _CDN_TOKENS:
        return [normalized]
    return ['direct']


def _combo_identity(combo: ProxyCombination) -> tuple[Any, ...]:
    return (combo.l3, combo.transport, combo.proto)


def _preset_protocol(combo: ProxyCombination) -> CustomProxyMode:
    proto = (combo.proto or '').lower()
    if combo.l3 == 'reality' or proto == 'anytls' or combo.transport == 'shadowtls':
        return CustomProxyMode.domains_sni_gateway
    if proto in ('tuic', 'hysteria2', 'hysteria', 'wireguard', 'ssh', 'mieru', 'socks', 'ss'):
        return CustomProxyMode.domains_auto_public_ports
    if proto == 'naive':
        return CustomProxyMode.domains_l7_gateway
    return CustomProxyMode.domains_l7_gateway


def _group_name(primary: ProxyCombination) -> str:
    parts = primary.name.split()
    filtered = [part for part in parts if part.lower() not in _CDN_TOKENS]
    return ' '.join(filtered) if filtered else primary.name


def _group_domain_modes(combos: list[ProxyCombination]) -> list[str]:
    modes: list[str] = []
    seen: set[str] = set()
    for combo in combos:
        for mode in _domain_modes(combo.cdn):
            if mode not in seen:
                seen.add(mode)
                modes.append(mode)
    return modes


def _grouped_combinations() -> list[tuple[list[ProxyCombination], ProxyCombination]]:
    groups: dict[tuple[Any, ...], list[ProxyCombination]] = defaultdict(list)
    for combo in iter_proxy_combinations():
        groups[_combo_identity(combo)].append(combo)
    grouped: list[tuple[list[ProxyCombination], ProxyCombination]] = []
    for combos in groups.values():
        primary = next((c for c in combos if c.cdn == 'direct'), combos[0])
        grouped.append((combos, primary))
    return grouped


def _preset_custom_path(combo: ProxyCombination, child_id: int = 0) -> str:
    proto_key, transport_key = _path_keys(combo.proto, combo.transport)

    def cfg_path(suffix: str) -> str:
        key = getattr(ConfigEnum, f'path_{suffix}', None)
        if key is None:
            return ''
        try:
            return str(hconfig(key, child_id) or '')
        except Exception:
            return ''

    return normalize_custom_path(f'{cfg_path(proto_key)}{cfg_path(transport_key)}')


def _custom_proxy_row(
    combos: list[ProxyCombination],
    primary: ProxyCombination,
    core: str,
    inbound_template: str,
    template_slugs: list[str],
    child_id: int = 0
) -> dict[str, Any]:
    display_name = _group_name(primary)
    slug = proxy_slug(f'{core}-{display_name}')
    mode = _preset_protocol(primary)
    custom_path = _preset_custom_path(primary, child_id)
    domain_modes = _group_domain_modes(combos)
    alpns = alpns_for_combo(primary.l3, primary.transport)
    download_alpns = (
        download_alpns_for_l3(primary.l3)
        if primary.transport.lower() == 'xhttp'
        else []
    )
    if mode == CustomProxyMode.domains_sni_gateway:
        domain_modes = ['special']
    elif mode == CustomProxyMode.domains_auto_public_ports:
        domain_modes = _group_domain_modes(combos) or ['direct', 'relay']
    tag = _backend_tag(primary, core)
    route = _haproxy_route(primary)
    raw_proto = _haproxy_proto(primary, route)
    l7_proto = raw_proto if mode == CustomProxyMode.domains_l7_gateway and raw_proto in ('h1', 'h2', 'h3') else None
    return {
        'name': display_name,
        'slug': slug,
        'enable': bool(primary.enable),
        'mode': mode.value,
        'l7_proto': l7_proto,
        'alpns': alpns,
        'download_alpns': download_alpns,
        'tags': list(dict.fromkeys([primary.proto, primary.l3, primary.transport])),
        'domain_modes': domain_modes,
        'custom_path': custom_path,
        'server_config': {
            'core': core,
            'inbound_template': inbound_template,
            'template_slugs': template_slugs,
            'tag': tag,
            'inbound_tcp_ports': [],
            'inbound_udp_ports': [],
            'sni_domains': [],
        },
        'client_config': {
            'core_configs': build_all_client_configs(primary, core),
        },
        'sort_order': 0,
    }


def iter_custom_proxy_presets(child_id: int = 0) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for combos, primary in _grouped_combinations():
        l7_gateway = _preset_protocol(primary) == CustomProxyMode.domains_l7_gateway
        if supports_xray_preset(primary):
            try:
                inbound, slugs = build_xray_inbound_template(primary)
                rows.append(_custom_proxy_row(combos, primary, 'xray', inbound, slugs, child_id))
            except ValueError:
                pass
        if supports_hiddify_preset(primary) or primary.proto == 'wireguard':
            try:
                inbound, slugs = build_hiddify_inbound_template(primary, l7_gateway=l7_gateway)
                rows.append(_custom_proxy_row(combos, primary, 'hiddify-core', inbound, slugs, child_id))
            except ValueError:
                pass
    return rows


def seed_custom_proxy_presets(child_id: int = 0) -> int:
    from hiddifypanel.models.custom_proxy import CustomProxy, _parse_mode
    from hiddifypanel.panel.template_catalog.builtin_sync import sync_builtin_custom_proxy

    presets = iter_custom_proxy_presets(child_id)
    presets_by_slug = {p['slug']: p for p in presets}
    added = 0
    upgraded = 0
    for data in presets:
        slug = data['slug']
        row = CustomProxy.query.filter(CustomProxy.child_id == child_id, CustomProxy.slug == slug).first()
        if row:
            expected_mode = _parse_mode(data.get('mode'))
            if row.mode != expected_mode:
                row.mode = expected_mode
            if not row.is_builtin:
                row.is_builtin = True
            if sync_builtin_custom_proxy(row, data):
                upgraded += 1
            continue
        row = CustomProxy.add_or_update(
            child_id=child_id,
            commit=False,
            is_builtin=True,
            name=data['name'],
            slug=slug,
            enable=bool(data.get('enable', True)),
            mode=data['mode'],
            l7_proto=data.get('l7_proto'),
            alpns=list(data.get('alpns') or []),
            download_alpns=list(data.get('download_alpns') or []),
            tags=list(data.get('tags') or []),
            domain_modes=list(data.get('domain_modes') or []),
            custom_path=data.get('custom_path') or '',
            server_config=data.get('server_config') or {},
        )
        db.session.flush()
        sync_builtin_custom_proxy(row, data)
        added += 1
    if added or upgraded:
        db.session.commit()
    for row in CustomProxy.query.filter(CustomProxy.child_id == child_id).all():
        if row.slug in presets_by_slug and not row.is_builtin:
            row.is_builtin = True
        path = normalize_custom_path(row.custom_path)
        if row.custom_path != path:
            row.custom_path = path
    db.session.commit()
    logger.info(
        'Custom proxy presets: child_id={} added={} upgraded={} total={}',
        child_id, added, upgraded, len(presets),
    )
    return added
