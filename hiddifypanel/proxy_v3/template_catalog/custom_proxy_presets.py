from __future__ import annotations

import zlib
from dataclasses import replace

from hiddifypanel import hutils
from hiddifypanel.models import ConfigEnum, hconfig
from hiddifypanel.models.custom_proxy import (
    CustomProxyMode,
    InboundTcpUdp,
    _parse_transport,
    normalize_custom_path,
    proxy_slug,
    xhttp_alpn_is_quic,
)
from hiddifypanel.proxy_v3.builtin_proxy_sync.types import (
    CustomProxyPreset,
    PresetClientCore,
    PresetServerConfig,
)
from hiddifypanel.proxy_v3.domain_mode_filter import (
    CDN_CAPABLE_TRANSPORTS,
    DNS_DIRECT_DOMAIN_MODES,
    DOMAIN_MODE_CDN,
    REALITY_DIRECT_RELAY_DOMAIN_MODES,
    V2RAY_ALL_DOMAIN_MODES,
    VALID_DIRECT_RELAY_DOMAIN_MODES,
    VALID_FAKE_DIRECT_RELAY_DOMAIN_MODES,
    filter_domain_modes_without_reality,
    transport_tls_supports_reality,
)

from ..alpn_helpers import alpn_tag_to_category
from .client_builder import build_all_client_configs
from .fragment_loader import load_template_slug
from .inbound_builder import (
    _path_keys,
    _raw_transport,
    build_hiddify_inbound_template,
    build_xray_inbound_template,
    supports_hiddify_preset,
    supports_xray_preset,
)
from .preset_slots import H3_PROTOS, PresetSlot, iter_grouped_preset_slots, preset_display_name, preset_slug_name, tls_layer_for_xhttp_alpn

V2RAY_GATEWAY_PROTOS = frozenset({"vless", "vmess", "trojan"})

SNI_GATEWAY_PROTOS = frozenset({"anytls"})
DNS_GATEWAY_PROTOS = frozenset({"dnstt", "slipstream", "masterdns"})
# Direct UDP listeners with a single public port (IP-based).
IP_BASED_UDP_PROTOS = frozenset({"tuic", "hysteria", "hysteria2"})
DIRECT_RELAY_DOMAIN_MODES = VALID_DIRECT_RELAY_DOMAIN_MODES
DIRECT_DNS_DOMAIN_MODES = DNS_DIRECT_DOMAIN_MODES
UDP_ONLY_PROTOS = frozenset({"tuic", "hysteria", "hysteria2", "wireguard", "dnstt", "slipstream", "masterdns"})
TCP_ONLY_PROTOS = frozenset({"ssh", "anytls"})
TCP_ONLY_TRANSPORTS = frozenset({"grpc", "http", "httpupgrade", "tcp", "ws"})
BOTH_PROTOS = frozenset({"mieru", "socks", "shadowsocks", "ss"})
REALITY_TERMINATION_TEMPLATE_SLUG = "xray/server/presets/reality_termination"
REALITY_TERMINATION_TAG = "reality-termination"
ADDITIONAL_CONFIG_SLUG = "additional-config"
ADDITIONAL_CONFIG_SERVER_SLUG = "hiddify-core/server/additional_config"
ADDITIONAL_CONFIG_CLIENT_SLUGS = {
    "hiddify-core": "hiddify-core/client/additional_config",
    "xray": "xray/client/additional_config",
    "clash": "clash/client/additional_config",
    "sublink": "sublink/additional_config",
}
NODE_CONFIGS_SLUG = "node-configs"
NODE_CONFIGS_SERVER_SLUG = "hiddify-core/server/node_configs"
NODE_CONFIGS_CLIENT_SLUGS = {
    "hiddify-core": "hiddify-core/client/node_configs",
    "xray": "xray/client/node_configs",
    "clash": "clash/client/node_configs",
    "sublink": "sublink/node_configs",
}


def build_reality_termination_preset(child_id: int = 0) -> CustomProxyPreset:
    inbound_template = load_template_slug(REALITY_TERMINATION_TEMPLATE_SLUG)
    display_name = "REALITY Termination"
    return CustomProxyPreset(
        name=display_name,
        slug=proxy_slug(f"xray-{display_name}"),
        enable=True,
        mode=CustomProxyMode.domains_sni_gateway,
        proto="vless",
        transport="tcp",
        tls_layer="tls",
        l7_reverse_proto=None,
        categories=("vless", "tcp", "reality", "sni"),
        domain_modes=REALITY_DIRECT_RELAY_DOMAIN_MODES,
        custom_path="",
        server_config=PresetServerConfig(
            core="xray",
            inbound_template=inbound_template,
            template_slugs=(REALITY_TERMINATION_TEMPLATE_SLUG,),
            tag=REALITY_TERMINATION_TAG,
        ),
        client_cores=(),
        tcp_udp=InboundTcpUdp.tcp,
        is_common_proxy=False,
    )


def build_additional_config_preset(child_id: int = 0) -> CustomProxyPreset:
    """Client-only proxy that merges remote configs via Jinja ``download()``. Disabled by default."""
    del child_id  # presets are child-agnostic; sync applies child_id
    server_template = load_template_slug(ADDITIONAL_CONFIG_SERVER_SLUG)
    client_cores = (
        PresetClientCore(
            core="hiddify-core",
            version="",
            slug="client-hiddify-core",
            outbounds_template=load_template_slug(ADDITIONAL_CONFIG_CLIENT_SLUGS["hiddify-core"]),
        ),
        PresetClientCore(
            core="singbox",
            version="",
            slug="client-singbox",
            # Reuse hiddify-core client template (avoids a second download pass).
            outbounds_template="{#use_hiddify_core()#}",
        ),
        PresetClientCore(
            core="xray",
            version="",
            slug="client-xray",
            outbounds_template=load_template_slug(ADDITIONAL_CONFIG_CLIENT_SLUGS["xray"]),
        ),
        PresetClientCore(
            core="clash",
            version="",
            slug="client-clash",
            outbounds_template=load_template_slug(ADDITIONAL_CONFIG_CLIENT_SLUGS["clash"]),
        ),
        PresetClientCore(
            core="sublink",
            version="",
            slug="client-sublink",
            outbounds_template=load_template_slug(ADDITIONAL_CONFIG_CLIENT_SLUGS["sublink"]),
        ),
    )
    return CustomProxyPreset(
        name="Additional Config",
        slug=ADDITIONAL_CONFIG_SLUG,
        enable=False,
        mode=CustomProxyMode.ip,
        proto="vless",
        transport="other",
        tls_layer="http",
        l7_reverse_proto=None,
        categories=("additional_config",),
        domain_modes=(),
        custom_path="",
        server_config=PresetServerConfig(
            core="hiddify-core",
            inbound_template=server_template,
            template_slugs=(ADDITIONAL_CONFIG_SERVER_SLUG,),
            tag="additional-config",
        ),
        client_cores=client_cores,
        tcp_udp=InboundTcpUdp.both,
    )


def build_node_configs_preset(child_id: int = 0) -> CustomProxyPreset:
    """Client-only proxy that merges child-node configs via Jinja ``get_nodes_configs()``. Enabled by default."""
    del child_id  # presets are child-agnostic; sync applies child_id
    server_template = load_template_slug(NODE_CONFIGS_SERVER_SLUG)
    client_cores = (
        PresetClientCore(
            core="hiddify-core",
            version="",
            slug="client-hiddify-core",
            outbounds_template=load_template_slug(NODE_CONFIGS_CLIENT_SLUGS["hiddify-core"]),
        ),
        PresetClientCore(
            core="singbox",
            version="",
            slug="client-singbox",
            # Reuse hiddify-core client template (same JSON shape).
            outbounds_template="{#use_hiddify_core()#}",
        ),
        PresetClientCore(
            core="xray",
            version="",
            slug="client-xray",
            outbounds_template=load_template_slug(NODE_CONFIGS_CLIENT_SLUGS["xray"]),
        ),
        PresetClientCore(
            core="clash",
            version="",
            slug="client-clash",
            outbounds_template=load_template_slug(NODE_CONFIGS_CLIENT_SLUGS["clash"]),
        ),
        PresetClientCore(
            core="sublink",
            version="",
            slug="client-sublink",
            outbounds_template=load_template_slug(NODE_CONFIGS_CLIENT_SLUGS["sublink"]),
        ),
    )
    return CustomProxyPreset(
        name="Node Configs",
        slug=NODE_CONFIGS_SLUG,
        enable=True,
        mode=CustomProxyMode.ip,
        proto="vless",
        transport="other",
        tls_layer="http",
        l7_reverse_proto=None,
        categories=("node_configs",),
        domain_modes=(),
        custom_path="",
        server_config=PresetServerConfig(
            core="hiddify-core",
            inbound_template=server_template,
            template_slugs=(NODE_CONFIGS_SERVER_SLUG,),
            tag="node-configs",
        ),
        client_cores=client_cores,
        tcp_udp=InboundTcpUdp.both,
    )


def _preset_l7_reverse_proto(
    transport: str,
    mode: CustomProxyMode,
    slot_l7: str | None,
    *,
    proto: str | None = None,
) -> str | None:
    if mode != CustomProxyMode.domains_l7_gateway:
        return None
    if slot_l7:
        return slot_l7
    if str(proto or "").lower() == "naive":
        return "h2"
    if transport == "xhttp":
        return "h2"
    if transport in ("ws", "httpupgrade", "http"):
        return "h1"
    if transport == "grpc":
        return "h2"
    return "h2"


def _v2ray_domain_modes(tls_layer: str, transport: str = "") -> tuple[str, ...]:
    modes = list(V2RAY_ALL_DOMAIN_MODES)
    if not transport_tls_supports_reality(transport, tls_layer):
        modes = filter_domain_modes_without_reality(modes)
    if str(transport or "").lower() in CDN_CAPABLE_TRANSPORTS and DOMAIN_MODE_CDN not in modes:
        modes.append(DOMAIN_MODE_CDN)
    return tuple(modes)


def _group_domain_modes(combos) -> list[str]:
    if any(str(combo.l3).lower() == "reality" for combo in combos):
        return list(REALITY_DIRECT_RELAY_DOMAIN_MODES)
    return list(VALID_DIRECT_RELAY_DOMAIN_MODES)


def _download_domain_modes_for_combo(combo) -> list[str]:
    if str(combo.l3).lower() == "reality":
        return list(REALITY_DIRECT_RELAY_DOMAIN_MODES)
    return list(VALID_DIRECT_RELAY_DOMAIN_MODES)


def _tls_layer_for_alpn(alpn: str | None, combo=None) -> str:
    reality = combo is not None and str(combo.l3).lower() == "reality"
    return tls_layer_for_xhttp_alpn(alpn, reality=reality)


def _download_tls_layer_for_alpn(alpn: str | None, combo=None) -> str:
    return _tls_layer_for_alpn(alpn, combo)


def _preset_tcp_udp(
    proto: str,
    *,
    transport: str,
    l3: str,
) -> InboundTcpUdp:
    proto_key = (proto or "").lower()
    transport_key = str(transport or "").lower()

    if str(l3).lower() == "reality":
        return InboundTcpUdp.tcp
    if str(l3).lower() == "h3_quic":
        return InboundTcpUdp.udp
    if proto_key in BOTH_PROTOS:
        return InboundTcpUdp.both
    if proto_key in UDP_ONLY_PROTOS:
        return InboundTcpUdp.udp
    if proto_key in TCP_ONLY_PROTOS:
        return InboundTcpUdp.tcp
    if transport_key in TCP_ONLY_TRANSPORTS:
        return InboundTcpUdp.tcp
    return InboundTcpUdp.both


def _preset_protocol(combo) -> CustomProxyMode:
    proto = (combo.proto or "").lower()
    raw_transport = _raw_transport(combo.transport)
    l3 = str(combo.l3 or "").lower()
    if proto in SNI_GATEWAY_PROTOS or raw_transport in ("shadowtls", "faketls"):
        return CustomProxyMode.domains_sni_gateway
    # Naive QUIC is SNI-routed; Naive H2 stays on the L7 gateway.
    if proto == "naive" and l3 == "h3_quic":
        return CustomProxyMode.domains_sni_gateway
    if proto in DNS_GATEWAY_PROTOS:
        return CustomProxyMode.domains_dns_gateway
    if proto in IP_BASED_UDP_PROTOS or proto in ("shadowsocks", "ss", "socks", "wireguard", "ssh", "mieru", "snell") or raw_transport == "tcp":
        return CustomProxyMode.ip
    return CustomProxyMode.domains_l7_gateway


def _stable_public_port(slug: str) -> int:
    """Deterministic public port in [10000, 50000] from the builtin slug."""
    mixed = zlib.crc32(slug.encode("utf-8")) % 40_001
    return 10_000 + mixed


used_paths = set()


def _preset_custom_path(combo, child_id: int = 0) -> str:
    proto_key, transport_key = _path_keys(combo.proto, combo.transport)

    def cfg_path(suffix: str) -> str:
        key = getattr(ConfigEnum, f"path_{suffix}", None)
        path = ""
        try:
            if key is not None:
                path = str(hconfig(key, child_id) or "")
        except Exception:
            pass

        if not path or path in used_paths:
            path = hutils.random.get_random_string(7, 15)
        used_paths.add(path)
        return path

    return normalize_custom_path(f"{cfg_path(proto_key)}{cfg_path(transport_key)}")


def _backend_tag(combo, core: str) -> str:
    proto = combo.proto.lower()
    transport = str(combo.transport).lower()
    if core == "xray" and proto in ("vless", "vmess", "trojan") and transport in ("ws", "grpc", "tcp", "http", "httpupgrade", "xhttp"):
        idx = {"vless": 0, "vmess": 1, "trojan": 2}[proto]
        tidx = {"ws": 0, "grpc": 1, "tcp": 2, "http": 5, "httpupgrade": 3, "xhttp": 4}[transport]
        return f"v10-{proto}-{transport}"
    if transport == "custom" or proto == transport:
        return proto
    return f"{proto}-{transport}"


def _build_categories(slot: PresetSlot) -> tuple[str, ...]:
    primary = slot.primary
    proto = str(primary.proto).lower()
    transport = str(primary.transport).lower()
    categories: list[str] = [proto, transport]

    if slot.upload_alpn or slot.download_alpn:
        for alpn in (slot.upload_alpn, slot.download_alpn):
            if not alpn:
                continue
            cat = alpn_tag_to_category(alpn)
            if cat in ("quic", "http") and cat not in categories:
                categories.append(cat)
        if slot.upload_alpn:
            categories.append(f"up:{alpn_tag_to_category(slot.upload_alpn)}")
        if slot.download_alpn:
            categories.append(f"down:{alpn_tag_to_category(slot.download_alpn)}")
        if slot.tls_layer == "http":
            if "http" not in categories:
                categories.append("http")
        elif "quic" not in categories and "http" not in categories:
            categories.append("tls")
    else:
        l3 = str(primary.l3).lower()
        if l3 == "reality":
            categories.append("reality")
        elif l3 == "http":
            categories.append("http")
        elif l3 == "h3_quic" or proto in H3_PROTOS:
            categories.append("quic")
        elif l3 in ("tls", "tls_h2", "tls_h2_h1"):
            categories.append("tls")

    return tuple(dict.fromkeys(str(t) for t in categories if t))


def _build_preset(
    slot: PresetSlot,
    core: str,
    inbound_template: str,
    template_slugs: list[str],
    child_id: int = 0,
    *,
    is_common_proxy: bool = False,
) -> CustomProxyPreset:
    primary = slot.primary
    display_name = preset_display_name(slot)
    slug = proxy_slug(f"{core}-{preset_slug_name(slot)}")
    if core == "hiddify-core":
        display_name = f"{display_name} HC"
    mode = _preset_protocol(primary)
    custom_path = _preset_custom_path(primary, child_id)
    domain_modes = _group_domain_modes(slot.related)
    proto = primary.proto.lower()
    raw_transport = _raw_transport(primary.transport)
    transport_value = _parse_transport(primary.transport).value
    tls_layer = slot.tls_layer
    if proto in UDP_ONLY_PROTOS or str(primary.l3).lower() == "h3_quic":
        tls_layer = "quic_tls"
    if proto in ("shadowsocks", "ss", "socks") and raw_transport not in ("shadowtls", "faketls"):
        tls_layer = "http"
    if proto in V2RAY_GATEWAY_PROTOS:
        domain_modes = list(_v2ray_domain_modes(tls_layer, transport_value))
    elif raw_transport in ("shadowtls", "faketls"):
        domain_modes = list(VALID_FAKE_DIRECT_RELAY_DOMAIN_MODES)
    elif proto in SNI_GATEWAY_PROTOS or proto == "naive":
        domain_modes = list(DIRECT_RELAY_DOMAIN_MODES)
    elif mode == CustomProxyMode.domains_dns_gateway:
        domain_modes = list(DIRECT_DNS_DOMAIN_MODES)
    elif mode == CustomProxyMode.domains_auto_public_ports:
        domain_modes = list(DIRECT_RELAY_DOMAIN_MODES)
    elif mode == CustomProxyMode.ip:
        domain_modes = list(DIRECT_RELAY_DOMAIN_MODES)
    download_tls_layer = None
    download_domain_modes: tuple[str, ...] = ()
    download_tcp_udp = None
    if transport_value == "xhttp":
        tls_layer = _tls_layer_for_alpn(slot.upload_alpn, primary)
        download_tls_layer = _tls_layer_for_alpn(slot.download_alpn, primary)
        if proto in V2RAY_GATEWAY_PROTOS:
            domain_modes = list(_v2ray_domain_modes(tls_layer, transport_value))
            download_domain_modes = _v2ray_domain_modes(download_tls_layer or tls_layer, transport_value)
        else:
            download_domain_modes = tuple(_download_domain_modes_for_combo(primary))
        if xhttp_alpn_is_quic(slot.upload_alpn):
            domain_modes = filter_domain_modes_without_reality(domain_modes)
        if xhttp_alpn_is_quic(slot.download_alpn):
            download_domain_modes = tuple(filter_domain_modes_without_reality(download_domain_modes))
        # L7 terminates client QUIC; xray/hiddify-core inbound is TCP + h2.
        tcp_udp, download_tcp_udp = InboundTcpUdp.tcp, InboundTcpUdp.tcp
    else:
        tcp_udp = _preset_tcp_udp(
            proto,
            transport=transport_value,
            l3=primary.l3,
        )
    tag = _backend_tag(primary, core)
    l7_reverse = _preset_l7_reverse_proto(transport_value, mode, slot.l7_reverse_proto, proto=proto)
    inbound_tcp_ports: tuple[int, ...] = ()
    inbound_udp_ports: tuple[int, ...] = ()
    if mode == CustomProxyMode.ip:
        public_port = _stable_public_port(slug)
        if tcp_udp != InboundTcpUdp.udp:
            inbound_tcp_ports = (public_port,)
        if tcp_udp != InboundTcpUdp.tcp:
            inbound_udp_ports = (public_port,)

    client_cores = tuple(
        PresetClientCore(
            core=str(item["core"]),
            version=str(item.get("version") or ""),
            slug=str(item.get("slug") or f"client-{item['core']}"),
            outbounds_template=str(item.get("outbounds_template") or item.get("link_template") or ""),
            is_builtin=bool(item.get("is_builtin", True)),
        )
        for item in build_all_client_configs(primary, core)
    )
    return CustomProxyPreset(
        name=display_name,
        slug=slug,
        enable=False if proto == "socks" else bool(primary.enable),
        mode=mode,
        proto=primary.proto.lower(),
        transport=_parse_transport(primary.transport).value,
        tls_layer=tls_layer,
        l7_reverse_proto=l7_reverse,
        download_tls_layer=download_tls_layer,
        download_domain_modes=download_domain_modes,
        categories=_build_categories(slot),
        domain_modes=tuple(domain_modes),
        custom_path=custom_path,
        server_config=PresetServerConfig(
            core=core,
            inbound_template=inbound_template,
            template_slugs=tuple(template_slugs),
            tag=tag,
            inbound_tcp_ports=inbound_tcp_ports,
            inbound_udp_ports=inbound_udp_ports,
        ),
        client_cores=client_cores,
        tcp_udp=tcp_udp,
        download_tcp_udp=download_tcp_udp,
        is_common_proxy=is_common_proxy,
    )


def _dns_gateway_server_template(proto: str) -> str:
    from hiddifypanel.proxy_v3.template_catalog.fragment_loader import load_template_slug

    return load_template_slug(f"dns_proxy/{proto}/server", normalize=False)


def _build_dns_gateway_preset(slot, child_id: int = 0) -> CustomProxyPreset:
    primary = slot.primary
    proto = primary.proto.lower()
    display_name = preset_display_name(slot)
    slug = proxy_slug(f"dns-proxy-{preset_slug_name(slot)}")
    inbound = _dns_gateway_server_template(proto)
    return CustomProxyPreset(
        name=display_name,
        slug=slug,
        enable=False,
        mode=CustomProxyMode.domains_dns_gateway,
        proto=proto,
        transport=_parse_transport(primary.transport).value,
        tls_layer="http",
        l7_reverse_proto=None,
        download_tls_layer=None,
        download_domain_modes=(),
        categories=_build_categories(slot),
        domain_modes=tuple(DIRECT_DNS_DOMAIN_MODES),
        custom_path=_preset_custom_path(primary, child_id),
        server_config=PresetServerConfig(
            core="dns_proxy",
            inbound_template=inbound,
            template_slugs=(f"dns_proxy/{proto}/server", f"dns_proxy/{proto}/args"),
            tag=proxy_slug(display_name),
            inbound_tcp_ports=(),
            inbound_udp_ports=(),
        ),
        client_cores=(),
        tcp_udp=InboundTcpUdp.udp,
        download_tcp_udp=None,
        is_common_proxy=False,
    )


def iter_custom_proxy_presets(child_id: int = 0) -> list[CustomProxyPreset]:
    rows: list[CustomProxyPreset] = []
    for slot in iter_grouped_preset_slots():
        primary = slot.primary
        if primary.proto.lower() in DNS_GATEWAY_PROTOS:
            rows.append(_build_dns_gateway_preset(slot, child_id))
            continue
        l7_gateway = _preset_protocol(primary) == CustomProxyMode.domains_l7_gateway
        xray_built: tuple[str, list[str]] | None = None
        hiddify_built: tuple[str, list[str]] | None = None
        if supports_xray_preset(primary):
            try:
                xray_built = build_xray_inbound_template(primary, l7_gateway=l7_gateway)
            except ValueError:
                pass
        if supports_hiddify_preset(primary) or primary.proto == "wireguard":
            try:
                hiddify_built = build_hiddify_inbound_template(primary, l7_gateway=l7_gateway)
            except ValueError:
                pass
        is_common_proxy = xray_built is not None and hiddify_built is not None
        if xray_built:
            inbound, slugs = xray_built
            rows.append(_build_preset(slot, "xray", inbound, slugs, child_id, is_common_proxy=is_common_proxy))
        if hiddify_built:
            inbound, slugs = hiddify_built
            rows.append(_build_preset(slot, "hiddify-core", inbound, slugs, child_id, is_common_proxy=is_common_proxy))
    rows.append(build_reality_termination_preset(child_id))
    rows.append(build_additional_config_preset(child_id))
    rows.append(build_node_configs_preset(child_id))
    return _mark_common_proxies(rows)


_COMMON_PROXY_CORES = frozenset({"xray", "hiddify-core"})
_COMMON_PROXY_SKIP_SLUGS = frozenset({"additional-config", "node-configs", "xray-reality-termination"})


def _preset_slot_key(preset: CustomProxyPreset) -> str | None:
    slug = preset.slug.strip().lower()
    core = preset.server_config.core
    if core == "hiddify-core" and slug.startswith("hiddify-core-"):
        key = slug[len("hiddify-core-") :]
    elif core == "xray" and slug.startswith("xray-"):
        key = slug[len("xray-") :]
    else:
        return None
    if key.endswith("-hc"):
        key = key[: -len("-hc")]
    return key or None


def _preset_name_key(preset: CustomProxyPreset) -> str:
    raw = " ".join(preset.name.split())
    if raw.endswith(" HC"):
        raw = raw[: -len(" HC")].rstrip()
    return raw.casefold()


def _mark_common_proxies(rows: list[CustomProxyPreset]) -> list[CustomProxyPreset]:
    cores_by_slot: dict[str, set[str]] = {}
    cores_by_name: dict[str, set[str]] = {}
    for row in rows:
        core = row.server_config.core
        if core not in _COMMON_PROXY_CORES or row.slug in _COMMON_PROXY_SKIP_SLUGS:
            continue
        slot = _preset_slot_key(row)
        if slot:
            cores_by_slot.setdefault(slot, set()).add(core)
        name = _preset_name_key(row)
        if name:
            cores_by_name.setdefault(name, set()).add(core)
    marked: list[CustomProxyPreset] = []
    for row in rows:
        if row.slug in _COMMON_PROXY_SKIP_SLUGS:
            is_common = False
        else:
            slot = _preset_slot_key(row)
            name = _preset_name_key(row)
            is_common = (slot is not None and cores_by_slot.get(slot) == _COMMON_PROXY_CORES) or (bool(name) and cores_by_name.get(name) == _COMMON_PROXY_CORES)
        marked.append(row if row.is_common_proxy == is_common else replace(row, is_common_proxy=is_common))
    return marked


def sync_builtin_presets(child_id: int = 0) -> int:
    from hiddifypanel.proxy_v3.builtin_proxy_sync.orchestrator import (
        sync_base_configs,
        sync_custom_proxy_presets,
        sync_templates,
    )
    from hiddifypanel.proxy_v3.tls_store_sync import sync_tls_store_all

    sync_tls_store_all(child_id)
    sync_templates(child_id)
    sync_base_configs(child_id, refresh_builtin=True)
    added, _updated, _removed, _demoted = sync_custom_proxy_presets(child_id)
    return added
