from __future__ import annotations

from dataclasses import replace

from hiddifypanel.models import ConfigEnum, hconfig
from hiddifypanel.models.custom_proxy import (
    CustomProxyMode,
    InboundTcpUdp,
    filter_domain_modes_without_reality,
    normalize_custom_path,
    proxy_slug,
    xhttp_alpn_is_quic,
    _parse_transport,
)
from hiddifypanel.proxy_v3.builtin_proxy_sync.types import (
    CustomProxyPreset,
    PresetClientCore,
    PresetServerConfig,
)

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
from ..alpn_helpers import alpn_tag_to_category
from hiddifypanel import hutils

V2RAY_GATEWAY_PROTOS = frozenset({"vless", "vmess", "trojan"})
V2RAY_GATEWAY_DOMAIN_MODES_WITH_CDN = ("direct", "cdn", "relay")
V2RAY_GATEWAY_DOMAIN_MODES_NO_CDN = ("direct", "relay")
V2RAY_GATEWAY_DOMAIN_MODES_HTTP_WITH_CDN = ("direct", "cdn", "relay")
V2RAY_GATEWAY_DOMAIN_MODES_HTTP_NO_CDN = ("direct", "relay")

SNI_GATEWAY_PROTOS = frozenset({"anytls", "tuic", "hysteria", "hysteria2"})
FAKE_ONLY_DOMAIN_MODES = ("fake",)
DIRECT_RELAY_DOMAIN_MODES = ("direct", "relay")
CDN_CAPABLE_TRANSPORTS = frozenset({"ws", "httpupgrade", "grpc", "xhttp"})
UDP_ONLY_PROTOS = frozenset({"tuic", "hysteria", "hysteria2", "wireguard"})
TCP_ONLY_PROTOS = frozenset({"ssh", "anytls"})
TCP_ONLY_TRANSPORTS = frozenset({"grpc", "httpupgrade", "tcp", "ws"})
BOTH_PROTOS = frozenset({"mieru", "socks", "shadowsocks", "ss"})
XHTTP_QUIC_ALPN_TAGS = frozenset({"tls_h3", "h3"})


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
        domain_modes=("reality",),
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
    if transport in ("ws", "httpupgrade"):
        return "h1"
    if transport == "grpc":
        return "h2"
    return "h2"


def _v2ray_l7_domain_modes(
    transport: str,
    tls_layer: str,
) -> tuple[str, ...]:
    transport_key = str(transport or "").lower()
    cdn_ok = transport_key in CDN_CAPABLE_TRANSPORTS
    if str(tls_layer or "").lower() == "http":
        return V2RAY_GATEWAY_DOMAIN_MODES_HTTP_WITH_CDN if cdn_ok else V2RAY_GATEWAY_DOMAIN_MODES_HTTP_NO_CDN
    if cdn_ok:
        return V2RAY_GATEWAY_DOMAIN_MODES_WITH_CDN
    return V2RAY_GATEWAY_DOMAIN_MODES_NO_CDN


def _group_domain_modes(combos) -> list[str]:
    if any(str(combo.l3).lower() == "reality" for combo in combos):
        return ["reality"]
    modes: list[str] = []
    seen: set[str] = set()
    for combo in combos:
        cdn = (combo.cdn or "direct").lower()
        normalized = "cdn" if cdn == "cdn" else cdn
        if normalized in ("direct", "relay", "cdn", "fake") and normalized not in seen:
            seen.add(normalized)
            modes.append(normalized)
    return modes


def _download_domain_modes_for_combo(combo) -> list[str]:
    if str(combo.l3).lower() == "reality":
        return ["reality"]
    cdn = (combo.cdn or "direct").lower()
    return ["cdn" if cdn == "cdn" else cdn]


def _tls_layer_for_alpn(alpn: str | None, combo=None) -> str:
    reality = combo is not None and str(combo.l3).lower() == "reality"
    return tls_layer_for_xhttp_alpn(alpn, reality=reality)


def _download_tls_layer_for_alpn(alpn: str | None, combo=None) -> str:
    return _tls_layer_for_alpn(alpn, combo)


def _xhttp_alpn_is_quic(alpn: str | None) -> bool:
    return bool(alpn and str(alpn).lower() in XHTTP_QUIC_ALPN_TAGS)


def _preset_xhttp_tcp_udp(
    upload_alpn: str | None,
    download_alpn: str | None,
) -> tuple[InboundTcpUdp, InboundTcpUdp]:
    upload = InboundTcpUdp.udp if _xhttp_alpn_is_quic(upload_alpn) else InboundTcpUdp.tcp
    download = InboundTcpUdp.udp if _xhttp_alpn_is_quic(download_alpn) else InboundTcpUdp.tcp
    return upload, download


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
    if proto in SNI_GATEWAY_PROTOS or raw_transport in ("shadowtls", "faketls"):
        return CustomProxyMode.domains_sni_gateway
    if proto in (
        "wireguard",
        "ssh",
        "mieru",
        "socks",
        "shadowsocks",
        "ss",
        "dnstt",
        "snell",
    ):
        return CustomProxyMode.domains_auto_public_ports
    return CustomProxyMode.domains_l7_gateway


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
    if core == "xray" and proto in ("vless", "vmess", "trojan") and transport in ("ws", "grpc", "tcp", "httpupgrade", "xhttp"):
        idx = {"vless": 0, "vmess": 1, "trojan": 2}[proto]
        tidx = {"ws": 0, "grpc": 1, "tcp": 2, "httpupgrade": 3, "xhttp": 4}[transport]
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
    if mode == CustomProxyMode.domains_l7_gateway and proto in V2RAY_GATEWAY_PROTOS:
        domain_modes = list(_v2ray_l7_domain_modes(transport_value, tls_layer))
    elif raw_transport in ("shadowtls", "faketls"):
        domain_modes = list(FAKE_ONLY_DOMAIN_MODES)
    elif proto in SNI_GATEWAY_PROTOS or proto == "naive":
        domain_modes = list(DIRECT_RELAY_DOMAIN_MODES)
    elif mode == CustomProxyMode.domains_auto_public_ports:
        domain_modes = list(DIRECT_RELAY_DOMAIN_MODES)
    download_tls_layer = None
    download_domain_modes: tuple[str, ...] = ()
    download_tcp_udp = None
    if transport_value == "xhttp":
        tls_layer = _tls_layer_for_alpn(slot.upload_alpn, primary)
        download_tls_layer = _tls_layer_for_alpn(slot.download_alpn, primary)
        if mode == CustomProxyMode.domains_l7_gateway and proto in V2RAY_GATEWAY_PROTOS:
            domain_modes = list(_v2ray_l7_domain_modes(transport_value, tls_layer))
        if proto in V2RAY_GATEWAY_PROTOS:
            download_domain_modes = _v2ray_l7_domain_modes(
                transport_value,
                download_tls_layer or tls_layer,
            )
        else:
            download_domain_modes = tuple(_download_domain_modes_for_combo(primary))
        if xhttp_alpn_is_quic(slot.upload_alpn):
            domain_modes = filter_domain_modes_without_reality(domain_modes)
        if xhttp_alpn_is_quic(slot.download_alpn):
            download_domain_modes = tuple(filter_domain_modes_without_reality(download_domain_modes))
        tcp_udp, download_tcp_udp = _preset_xhttp_tcp_udp(slot.upload_alpn, slot.download_alpn)
    else:
        tcp_udp = _preset_tcp_udp(
            proto,
            transport=transport_value,
            l3=primary.l3,
        )
    tag = _backend_tag(primary, core)
    l7_reverse = _preset_l7_reverse_proto(transport_value, mode, slot.l7_reverse_proto, proto=proto)

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
        enable=bool(primary.enable),
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
        ),
        client_cores=client_cores,
        tcp_udp=tcp_udp,
        download_tcp_udp=download_tcp_udp,
        is_common_proxy=is_common_proxy,
    )


def iter_custom_proxy_presets(child_id: int = 0) -> list[CustomProxyPreset]:
    rows: list[CustomProxyPreset] = []
    for slot in iter_grouped_preset_slots():
        primary = slot.primary
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
    return _mark_common_proxies(rows)


def _common_proxy_slot_key(slug: str, server_core: str | None) -> str | None:
    raw = str(slug or "")
    if server_core == "hiddify-core" and raw.startswith("hiddify-core-"):
        return raw[len("hiddify-core-") :]
    if server_core == "xray" and raw.startswith("xray-"):
        return raw[len("xray-") :]
    return None


def _mark_common_proxies(rows: list[CustomProxyPreset]) -> list[CustomProxyPreset]:
    cores: dict[str, set[str]] = {}
    for row in rows:
        core = row.server_config.core
        if core not in {"xray", "hiddify-core"}:
            continue
        key = _common_proxy_slot_key(row.slug, core)
        if key:
            cores.setdefault(key, set()).add(core)
    marked: list[CustomProxyPreset] = []
    for row in rows:
        core = row.server_config.core
        key = _common_proxy_slot_key(row.slug, core) if core in {"xray", "hiddify-core"} else None
        is_common = bool(key) and cores.get(key) == {"xray", "hiddify-core"}
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
