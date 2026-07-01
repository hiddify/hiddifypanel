from __future__ import annotations

from .fragment_loader import fragment_slug, list_fragments, load_template_slug
from .proxy_matrix import ProxyCombination

# Map legacy matrix names to on-disk fragment basenames.
PROTO_SLUG: dict[str, str] = {
    'ss': 'ss',
    'v2ray': 'vmess',
    'hysteria2': 'hysteria',
}

TRANSPORT_SLUG: dict[str, str] = {
    'WS': 'ws',
    'ws': 'ws',
    'h2': 'tcp',
    'grpc': 'grpc',
    'tcp': 'tcp',
    'httpupgrade': 'httpupgrade',
    'xhttp': 'xhttp',
    'faketls': 'tcp',
    'shadowtls': 'tcp',
    'custom': 'none',
    'ssh': 'none',
    'shadowsocks': 'none',
    'udp': 'none',
}

# Protos that use xray/v2ray stream settings (ws, grpc, tcp, xhttp, …) on hiddify-core.
V2RAY_TRANSPORT_PROTOS: frozenset[str] = frozenset({
    'vless', 'vmess', 'trojan',
})

CLIENT_PROTO_SLUG: dict[str, str] = {
    'v2ray': 'ss',
}

L3_STREAM_SECURITY: dict[str, str] = {
    'tls': 'tls',
    'tls_h2': 'tls',
    'h3_quic': 'tls_h3',
    'http': 'none',
    'reality': 'reality',
}


def _proto_file(proto: str) -> str | None:
    return PROTO_SLUG.get(proto, proto)


def _client_proto_file(proto: str) -> str | None:
    return CLIENT_PROTO_SLUG.get(proto, _proto_file(proto))


def _inbound_proto_file(combo: ProxyCombination) -> str | None:
    if _raw_transport(combo.transport) == 'shadowtls':
        return 'shadowtls'
    return _proto_file(combo.proto)


def _raw_transport(transport: str) -> str:
    return str(getattr(transport, 'value', transport) or transport).lower()


def _transport_file(transport: str) -> str | None:
    return TRANSPORT_SLUG.get(transport, transport)


def _path_keys(proto: str, transport: str) -> tuple[str, str]:
    proto_key = PROTO_SLUG.get(proto, proto)
    transport_key = 'ws' if transport in ('WS', 'ws') else transport
    return proto_key, transport_key


def _preset_shell_slug(core: str, name: str) -> str:
    if core == 'hiddify-core' and name == 'inbound':
        return f'{core}/server/presets/inbound'
    return f'{core}/presets/{name}'


def _hiddify_tls_slug(combo: ProxyCombination) -> str:
    if combo.l3 == 'reality':
        return 'hiddify-core/server/tls/reality'
    if combo.l3 in ('tls', 'tls_h2', 'h3_quic'):
        return 'hiddify-core/server/tls/tls'
    return 'hiddify-core/server/tls/none'


def supports_xray_preset(combo: ProxyCombination) -> bool:
    proto = _proto_file(combo.proto)
    transport = _transport_file(combo.transport)
    if not proto or not transport:
        return False
    return proto in list_fragments('xray', 'protocols') and transport in list_fragments('xray', 'streams')


def _server_proto_stem(combo: ProxyCombination) -> str | None:
    if _raw_transport(combo.transport) == 'shadowtls':
        return 'shadowtls'
    return PROTO_SLUG.get(combo.proto, combo.proto)


def _uses_v2ray_transport_proto(proto: str | None) -> bool:
    return bool(proto and proto in V2RAY_TRANSPORT_PROTOS)


def _is_standalone_hiddify_server(combo: ProxyCombination) -> bool:
    proto = _server_proto_stem(combo)
    return bool(proto) and not _uses_v2ray_transport_proto(proto)


def supports_hiddify_preset(combo: ProxyCombination) -> bool:
    if combo.proto == 'wireguard':
        return False
    if _is_standalone_hiddify_server(combo):
        proto = _server_proto_stem(combo)
        return bool(proto and proto in list_fragments('hiddify-core', 'protocols', side='server'))
    proto = _inbound_proto_file(combo)
    transport = _transport_file(combo.transport)
    if not proto or not transport:
        return False
    return (
        proto in list_fragments('hiddify-core', 'protocols', side='server')
        and transport in list_fragments('hiddify-core', 'stream', side='server')
    )


def _xray_security_slug(combo: ProxyCombination) -> str:
    security = L3_STREAM_SECURITY.get(combo.l3, 'tls')
    if security == 'none':
        return 'xray/common/security/none'
    if security == 'reality':
        return 'xray/common/security/reality'
    if combo.l3 == 'h3_quic':
        return 'xray/common/security/tls_h3'
    if combo.params.get('download', {}).get('alpn'):
        return 'xray/common/security/tls_alpn'
    return 'xray/common/security/tls'


def _render_preset_shell(
    core: str,
    *,
    proto_slug: str,
    stream_slug: str,
    security_slug: str | None,
    proto_key: str,
    transport_key: str,
    flow_line: str = '',
    alpn_line: str = '',
    tls_slug: str | None = None,
) -> str:
    resolved_security = security_slug or 'xray/common/security/none'
    shell = load_template_slug(_preset_shell_slug(core, 'inbound'), normalize=False)
    replacements = {
        '__PROTO_SLUG__': proto_slug,
        '__STREAM_SLUG__': stream_slug,
        '__PROTO_KEY__': proto_key,
        '__TRANSPORT_KEY__': transport_key,
        '__FLOW_LINE__': flow_line,
        '__SECURITY_SLUG__': resolved_security,
        '__TLS_SLUG__': tls_slug or 'hiddify-core/server/tls/none',
    }
    for key, value in replacements.items():
        shell = shell.replace(key, value)
    if alpn_line:
        sec_inc = f"{{% include '{resolved_security}' %}}"
        shell = shell.replace(sec_inc, f'{alpn_line}\n    {sec_inc}')
    return shell


def build_xray_inbound_template(combo: ProxyCombination) -> tuple[str, list[str]]:
    proto = _proto_file(combo.proto)
    transport = _transport_file(combo.transport)
    if not proto or not transport:
        raise ValueError(f'Unsupported xray preset: {combo.name}')

    proto_key, transport_key = _path_keys(combo.proto, combo.transport)
    proto_slug = fragment_slug('xray', 'protocols', proto)
    stream_slug = fragment_slug('xray', 'streams', transport)
    security_slug = _xray_security_slug(combo)
    listen_slug = 'xray/inbound/listen'
    sockopt_slug = 'xray/snippets/stream_sockopt'
    sniffing_slug = 'xray/snippets/sniffing'
    slugs = [listen_slug, proto_slug, stream_slug, security_slug, sockopt_slug, sniffing_slug]

    flow_line = '{% set FLOW = hconfig.vless_flow %}' if combo.proto == 'vless' else '{% set FLOW = "" %}'
    alpn_line = ''
    if security_slug == 'xray/common/security/tls_alpn':
        alpn = combo.params['download']['alpn']
        alpn_line = f'{{% set ALPN = "{alpn}" %}}'

    content = _render_preset_shell(
        'xray',
        proto_slug=proto_slug,
        stream_slug=stream_slug,
        security_slug=security_slug,
        proto_key=proto_key,
        transport_key=transport_key,
        flow_line=flow_line,
        alpn_line=alpn_line,
    )
    return content, slugs


_DOMAIN_LOOP_PROTOS: frozenset[str] = frozenset({'tuic', 'hysteria'})


def build_hiddify_standalone_inbound(combo: ProxyCombination) -> tuple[str, list[str]]:
    proto = _server_proto_stem(combo)
    if not proto:
        raise ValueError(f'Unsupported hiddify-core standalone preset: {combo.name}')
    proto_slug = fragment_slug('hiddify-core', 'protocols', proto, side='server')
    slugs = [proto_slug]
    if proto in ('socks', 'ss'):
        listen_slug = 'hiddify-core/server/snippets/listen'
        meta_slug = 'hiddify-core/server/snippets/inbound_meta'
        slugs = [listen_slug, proto_slug, meta_slug]
        content = (
            '{% block inbounds %}\n'
            '{\n'
            f"  {{% include '{listen_slug}' %}},\n"
            f"  {{% include '{proto_slug}' %}},\n"
            f"  {{% include '{meta_slug}' %}}\n"
            '}\n'
            '{% endblock %}'
        )
        return content, slugs
    if proto in _DOMAIN_LOOP_PROTOS:
        content = (
            '{% block inbounds %}\n'
            '{% for domain in domains %}\n'
            '{% set proxy = proxy.with_domain(domain) %}\n'
            '{\n'
            f"  {{% include '{proto_slug}' %}}\n"
            '}\n'
            '{%- if not loop.last %},{%- endif %}\n'
            '{% endfor %}\n'
            '{% endblock %}'
        )
        return content, slugs
    content = (
        '{% block inbounds %}\n'
        '{\n'
        f"  {{% include '{proto_slug}' %}}\n"
        '}\n'
        '{% endblock %}'
    )
    return content, slugs


def build_hiddify_wireguard_server_stub() -> tuple[str, list[str]]:
    return '{% block inbounds %}\n{% skip() if true %}\n{% endblock %}', []


def build_hiddify_inbound_template(
    combo: ProxyCombination,
    *,
    l7_gateway: bool = False
) -> tuple[str, list[str]]:
    if combo.proto == 'wireguard':
        return build_hiddify_wireguard_server_stub()
    if _is_standalone_hiddify_server(combo):
        return build_hiddify_standalone_inbound(combo)
    proto = _inbound_proto_file(combo)
    transport = _transport_file(combo.transport)
    if not proto or not transport:
        raise ValueError(f'Unsupported hiddify-core preset: {combo.name}')

    proto_key, transport_key = _path_keys(combo.proto, combo.transport)
    proto_slug = fragment_slug('hiddify-core', 'protocols', proto, side='server')
    stream_slug = fragment_slug('hiddify-core', 'stream', transport, side='server')
    tls_slug = 'hiddify-core/server/tls/none' if l7_gateway else _hiddify_tls_slug(combo)
    listen_slug = 'hiddify-core/server/snippets/listen'
    meta_slug = 'hiddify-core/server/snippets/inbound_meta'
    multiplex_slug = 'hiddify-core/server/snippets/multiplex'
    slugs = [listen_slug, meta_slug, proto_slug, stream_slug, tls_slug, multiplex_slug]

    content = _render_preset_shell(
        'hiddify-core',
        proto_slug=proto_slug,
        stream_slug=stream_slug,
        security_slug=None,
        proto_key=proto_key,
        transport_key=transport_key,
        tls_slug=tls_slug,
    )
    return content, slugs
