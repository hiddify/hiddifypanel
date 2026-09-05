from __future__ import annotations

from .fragment_loader import fragment_slug, list_fragments, load_template_slug
from .paths import preset_shell_slug
from .proxy_matrix import ProxyCombination

# Map legacy matrix names to on-disk fragment basenames.
PROTO_SLUG: dict[str, str] = {
    "shadowsocks": "ss",
    "v2ray": "vmess",
}

TRANSPORT_SLUG: dict[str, str] = {
    "WS": "ws",
    "ws": "ws",
    "h2": "tcp",
    "grpc": "grpc",
    "tcp": "tcp",
    "http": "http",
    "httpupgrade": "httpupgrade",
    "xhttp": "xhttp",
    "faketls": "tcp",
    "shadowtls": "tcp",
    "custom": "none",
    "ssh": "none",
    "shadowsocks": "none",
    "udp": "none",
}

# Protos that use xray/v2ray stream settings (ws, grpc, tcp, xhttp, …) on hiddify-core.
V2RAY_TRANSPORT_PROTOS: frozenset[str] = frozenset(
    {
        "vless",
        "vmess",
        "trojan",
    }
)

CLIENT_PROTO_SLUG: dict[str, str] = {
    "v2ray": "ss",
}

L3_STREAM_SECURITY: dict[str, str] = {
    "tls": "tls",
    "tls_h2": "tls",
    "h3_quic": "tls",
    "http": "none",
    "reality": "reality",
}


def _proto_file(proto: str) -> str | None:
    return PROTO_SLUG.get(proto, proto)


def _client_proto_file(proto: str) -> str | None:
    return CLIENT_PROTO_SLUG.get(proto, _proto_file(proto))


def _inbound_proto_file(combo: ProxyCombination) -> str | None:
    if _raw_transport(combo.transport) == "shadowtls":
        return "shadowtls"
    return _proto_file(combo.proto)


def _raw_transport(transport: str) -> str:
    return transport.lower()


def _transport_file(transport: str) -> str | None:
    return TRANSPORT_SLUG.get(transport, transport)


def _path_keys(proto: str, transport: str) -> tuple[str, str]:
    proto_key = PROTO_SLUG.get(proto, proto)
    transport_key = "ws" if transport in ("WS", "ws") else transport
    return proto_key, transport_key


def _preset_shell_slug(core: str, name: str) -> str:
    return preset_shell_slug(core, "server", name)


def _hiddify_tls_slug(combo: ProxyCombination) -> str:
    if combo.l3 == "reality":
        return "hiddify-core/server/tls/reality"
    if combo.l3 in ("tls", "tls_h2", "h3_quic"):
        return "hiddify-core/server/tls/tls"
    return "hiddify-core/server/tls/none"


# Transports that are not real Xray stream fragments (even if TRANSPORT_SLUG maps them to tcp/none).
_XRAY_UNSUPPORTED_TRANSPORTS: frozenset[str] = frozenset(
    {
        "faketls",
        "shadowtls",
        "custom",
        "ssh",
        "shadowsocks",
        "udp",
        "none",
    }
)


def supports_xray_preset(combo: ProxyCombination) -> bool:
    # REALITY TLS termination is a dedicated preset (reality_termination), not a matrix inbound.
    if str(combo.l3).lower() == "reality":
        return False
    # Legacy "v2ray" matrix rows are Shadowsocks + v2ray-plugin (hiddify-core / sublink), not Xray vmess.
    if str(combo.proto).lower() == "v2ray":
        return False
    if _raw_transport(combo.transport) in _XRAY_UNSUPPORTED_TRANSPORTS:
        return False
    proto = _proto_file(combo.proto)
    transport = _transport_file(combo.transport)
    if not proto or not transport:
        return False
    return proto in list_fragments("xray", "protocols") and transport in list_fragments("xray", "streams")


def _server_proto_stem(combo: ProxyCombination) -> str | None:
    if _raw_transport(combo.transport) == "shadowtls":
        return "shadowtls"
    return PROTO_SLUG.get(combo.proto, combo.proto)


def _uses_v2ray_transport_proto(proto: str | None) -> bool:
    return bool(proto and proto in V2RAY_TRANSPORT_PROTOS)


def _is_standalone_hiddify_server(combo: ProxyCombination) -> bool:
    proto = _server_proto_stem(combo)
    return bool(proto) and not _uses_v2ray_transport_proto(proto)


def supports_hiddify_preset(combo: ProxyCombination) -> bool:
    if combo.proto == "wireguard":
        return False
    # sing-box / hiddify-core has no raw TCP stream (header none / IP).
    if _uses_v2ray_transport_proto(_server_proto_stem(combo)) and _raw_transport(combo.transport) == "tcp":
        return False
    if _is_standalone_hiddify_server(combo):
        proto = _server_proto_stem(combo)
        return bool(proto and proto in list_fragments("hiddify-core", "protocols", side="server"))
    proto = _inbound_proto_file(combo)
    transport = _transport_file(combo.transport)
    if not proto or not transport:
        return False
    return proto in list_fragments("hiddify-core", "protocols", side="server") and transport in list_fragments("hiddify-core", "streams", side="server")


def _xray_security_slug(combo: ProxyCombination, *, l7_gateway: bool = False) -> str:
    # Behind HAProxy / L7 gateway, Xray terminates PROXY protocol only (TLS already stripped).
    if l7_gateway and combo.l3 != "reality":
        return "xray/server/security/none"
    security = L3_STREAM_SECURITY.get(combo.l3, "tls")
    if security == "none":
        return "xray/server/security/none"
    if security == "reality":
        return "xray/server/security/reality"
    return "xray/server/security/tls"


def _xray_client_security_slug(combo: ProxyCombination) -> str:
    # Single client template handles none / tls / reality / alpn (incl. h3).
    return "xray/client/security/tls"


def _render_preset_shell(
    core: str,
    *,
    shell_name: str,
    proto_slug: str,
    stream_slug: str,
    security_slug: str | None,
    proto_key: str,
    transport_key: str,
    alpn_line: str = "",
    tls_slug: str | None = None,
) -> str:
    resolved_security = security_slug or "xray/server/security/none"
    shell = load_template_slug(_preset_shell_slug(core, shell_name), normalize=False)
    replacements = {
        "__PROTO_SLUG__": proto_slug,
        "__STREAM_SLUG__": stream_slug,
        "__PROTO_KEY__": proto_key,
        "__TRANSPORT_KEY__": transport_key,
        "__SECURITY_SLUG__": resolved_security,
        "__TLS_SLUG__": tls_slug or "hiddify-core/server/tls/none",
    }
    for key, value in replacements.items():
        shell = shell.replace(key, value)
    if alpn_line:
        sec_inc = f"{{% include '{resolved_security}' %}}"
        shell = shell.replace(sec_inc, f"{alpn_line}\n    {sec_inc}")
    return shell


def build_xray_inbound_template(combo: ProxyCombination, *, l7_gateway: bool = False) -> tuple[str, list[str]]:
    proto = _proto_file(combo.proto)
    transport = _transport_file(combo.transport)
    if not proto or not transport:
        raise ValueError(f"Unsupported xray preset: {combo.name}")

    proto_key, transport_key = _path_keys(combo.proto, combo.transport)
    proto_slug = fragment_slug("xray", "protocols", proto)
    stream_slug = fragment_slug("xray", "streams", transport)
    security_slug = _xray_security_slug(combo, l7_gateway=l7_gateway)
    listen_slug = "xray/inbound/listen"
    sockopt_slug = "xray/snippets/stream_sockopt"
    sniffing_slug = "xray/snippets/sniffing"
    slugs = [listen_slug, proto_slug, stream_slug, security_slug, sockopt_slug, sniffing_slug]

    alpn_line = ""
    if security_slug == "xray/server/security/tls":
        download_alpn = (combo.params.get("download") or {}).get("alpn")
        if download_alpn:
            alpn_line = f'{{% set ALPN = "{download_alpn}" %}}'
        elif combo.l3 == "h3_quic":
            alpn_line = '{% set alpns = ["h3"] %}'

    content = _render_preset_shell(
        "xray",
        shell_name="inbound",
        proto_slug=proto_slug,
        stream_slug=stream_slug,
        security_slug=security_slug,
        proto_key=proto_key,
        transport_key=transport_key,
        alpn_line=alpn_line,
    )
    return content, slugs


_DOMAIN_LOOP_PROTOS: frozenset[str] = frozenset({"tuic", "hysteria", "hysteria2", "shadowtls"})


def build_hiddify_standalone_inbound(combo: ProxyCombination) -> tuple[str, list[str]]:
    proto = _server_proto_stem(combo)
    if not proto:
        raise ValueError(f"Unsupported hiddify-core standalone preset: {combo.name}")
    proto_slug = fragment_slug("hiddify-core", "protocols", proto, side="server")
    slugs = [proto_slug]
    if proto in _DOMAIN_LOOP_PROTOS:
        content = f"{{% block inbounds %}}\n{{% for ctx in ctx.iter_domains() %}}\n{{\n  {{% include '{proto_slug}' %}}\n}}\n{{%- if not loop.last %}},{{%- endif %}}\n{{% endfor %}}\n{{% endblock %}}"
        return content, slugs

    listen_slug = "hiddify-core/server/snippets/listen"
    meta_slug = "hiddify-core/server/snippets/inbound_meta"
    multiplex_slug = "hiddify-core/server/snippets/multiplex"
    proto_key, transport_key = _path_keys(combo.proto, combo.transport)
    slugs = [listen_slug, proto_slug, meta_slug, multiplex_slug]
    content = _render_preset_shell(
        "hiddify-core",
        shell_name="inbound_other",
        proto_slug=proto_slug,
        stream_slug="",
        security_slug=None,
        proto_key=proto_key,
        transport_key=transport_key,
    )
    return content, slugs


def build_hiddify_wireguard_server_stub() -> tuple[str, list[str]]:
    return "{% block inbounds %}\n{{ skip() if true }}\n{% endblock %}", []


def build_hiddify_inbound_template(combo: ProxyCombination, *, l7_gateway: bool = False) -> tuple[str, list[str]]:
    if combo.proto == "wireguard":
        return build_hiddify_wireguard_server_stub()
    if _is_standalone_hiddify_server(combo):
        return build_hiddify_standalone_inbound(combo)
    proto = _inbound_proto_file(combo)
    transport = _transport_file(combo.transport)
    if not proto or not transport:
        raise ValueError(f"Unsupported hiddify-core preset: {combo.name}")

    proto_key, transport_key = _path_keys(combo.proto, combo.transport)
    proto_slug = fragment_slug("hiddify-core", "protocols", proto, side="server")
    stream_slug = fragment_slug("hiddify-core", "streams", transport, side="server")
    tls_slug = "hiddify-core/server/tls/none" if l7_gateway else _hiddify_tls_slug(combo)
    listen_slug = "hiddify-core/server/snippets/listen"
    meta_slug = "hiddify-core/server/snippets/inbound_meta"
    multiplex_slug = "hiddify-core/server/snippets/multiplex"
    slugs = [listen_slug, meta_slug, proto_slug, stream_slug, tls_slug, multiplex_slug]

    content = _render_preset_shell(
        "hiddify-core",
        shell_name="inbound_v2ray",
        proto_slug=proto_slug,
        stream_slug=stream_slug,
        security_slug=None,
        proto_key=proto_key,
        transport_key=transport_key,
        tls_slug=tls_slug,
    )
    return content, slugs
