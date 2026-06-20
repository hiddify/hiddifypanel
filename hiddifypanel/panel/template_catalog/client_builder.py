from __future__ import annotations

from typing import Any

from .fragment_loader import load_template_slug
from .inbound_builder import (
    _client_proto_file,
    _proto_file,
    _raw_transport,
    _transport_file,
    _uses_v2ray_transport_proto,
    _xray_security_slug,
    supports_hiddify_preset,
    supports_xray_preset,
)
from .proxy_matrix import ProxyCombination
from .template_defaults import default_sublink_link_template

CLIENT_CORES = ('xray', 'singbox', 'hiddify-core', 'clash', 'sublink')

_SINGBOX_CLIENT_ROOT = 'singbox'
_HIDDIFY_CLIENT_ROOT = 'hiddify-core'


def _client_proto_stem(combo: ProxyCombination) -> str | None:
    proto = _client_proto_file(combo.proto)
    if combo.proto == 'hysteria2':
        return 'hysteria'
    return proto


def _uses_v2ray_transport_client(combo: ProxyCombination) -> bool:
    proto = _client_proto_stem(combo)
    return _uses_v2ray_transport_proto(proto)


def _render_shell(core: str, shell_name: str, replacements: dict[str, str]) -> str:
    if core == _HIDDIFY_CLIENT_ROOT and shell_name.startswith('client_outbound'):
        shell_path = f'{core}/client/presets/{shell_name}'
    else:
        shell_path = f'{core}/presets/{shell_name}'
    shell = load_template_slug(shell_path, normalize=False)
    for key, value in replacements.items():
        shell = shell.replace(key, value)
    return shell


def _hiddify_client_streams_slug(combo: ProxyCombination) -> str | None:
    if not _uses_v2ray_transport_client(combo):
        return None
    transport = _transport_file(combo.transport)
    if not transport:
        return None
    if combo.l3 == 'reality' and transport == 'tcp':
        return f'{_HIDDIFY_CLIENT_ROOT}/client/stream/none'
    slug = f'{_HIDDIFY_CLIENT_ROOT}/client/stream/{transport}'
    try:
        load_template_slug(slug)
        return slug
    except FileNotFoundError:
        return None


def _hiddify_client_proto_slug(combo: ProxyCombination) -> str | None:
    proto = _client_proto_file(combo.proto)
    if not proto:
        return None
    transport = _raw_transport(combo.transport)
    if proto == 'ss' and transport == 'faketls':
        name = 'ss_faketls'
    elif combo.proto == 'v2ray':
        name = 'ss_v2ray'
    else:
        name = proto
    slug = f'{_HIDDIFY_CLIENT_ROOT}/client/protocols/{name}'
    try:
        load_template_slug(slug)
        return slug
    except FileNotFoundError:
        return None


def _hiddify_client_tls_slug(combo: ProxyCombination) -> str:
    if combo.l3 == 'reality':
        return f'{_HIDDIFY_CLIENT_ROOT}/client/tls/reality'
    if combo.l3 in ('http', 'h2c'):
        return f'{_HIDDIFY_CLIENT_ROOT}/client/tls/none'
    if combo.l3 in ('tls', 'tls_h2', 'tls_h2_h1', 'h3_quic'):
        return f'{_HIDDIFY_CLIENT_ROOT}/client/tls/tls'
    return f'{_HIDDIFY_CLIENT_ROOT}/client/tls/none'


def _singbox_client_streams_slug(transport: str) -> str | None:
    mapped = _transport_file(transport)
    if not mapped:
        return None
    slug = f'{_SINGBOX_CLIENT_ROOT}/client/streams/{mapped}'
    try:
        load_template_slug(slug)
        return slug
    except FileNotFoundError:
        return None


def _singbox_client_proto_slug(proto: str) -> str | None:
    mapped = _proto_file(proto)
    if not mapped:
        return None
    slug = f'{_SINGBOX_CLIENT_ROOT}/client/protocols/{mapped}'
    try:
        load_template_slug(slug)
        return slug
    except FileNotFoundError:
        return None


def _xray_client_streams_slug(transport: str) -> str | None:
    mapped = _transport_file(transport)
    if not mapped:
        return None
    slug = f'xray/client/streams/{mapped}'
    try:
        load_template_slug(slug)
        return slug
    except FileNotFoundError:
        return 'xray/client/streams/tcp'


def _xray_client_proto_slug(proto: str) -> str | None:
    mapped = _proto_file(proto)
    if not mapped:
        return None
    slug = f'xray/client/protocols/{mapped}'
    try:
        load_template_slug(slug)
        return slug
    except FileNotFoundError:
        return None


def _unwrap_json_array_shell(body: str) -> str:
    stripped = (body or '').strip()
    if stripped.startswith('[') and stripped.endswith(']'):
        return stripped[1:-1].strip()
    return stripped


def _client_outbound_block_name(core: str, combo: ProxyCombination) -> str:
    if _client_proto_file(combo.proto) == 'wireguard':
        return 'endpoints'
    return 'outbounds'


def _wrap_client_outbound_block(body: str, core: str, combo: ProxyCombination) -> str:
    block = _client_outbound_block_name(core, combo)
    inner = _unwrap_json_array_shell((body or '').strip())
    return f'{{% block {block} %}}\n{inner}\n{{% endblock %}}'


def _sublink_link_slug(combo: ProxyCombination) -> str:
    transport = _transport_file(combo.transport)
    if transport in ('ws', 'httpupgrade'):
        return 'sublink/links/vless_ws'
    return 'sublink/links/vless_tcp'


def build_xray_client_outbound(combo: ProxyCombination) -> tuple[str, list[str]]:
    proto_slug = _xray_client_proto_slug(combo.proto)
    stream_slug = _xray_client_streams_slug(combo.transport)
    if not proto_slug or not stream_slug:
        raise ValueError(f'Unsupported xray client preset: {combo.name}')
    security_slug = _xray_security_slug(combo)
    slugs = [proto_slug, stream_slug, security_slug, 'xray/snippets/stream_sockopt', 'xray/snippets/sniffing']
    flow_line = ''
    alpn_line = ''
    if combo.proto == 'vless':
        flow_line = '{% set FLOW = hconfig.vless_flow %}'
    if security_slug == 'xray/common/security/tls_alpn':
        alpn = combo.params['download']['alpn']
        alpn_line = f'{{% set ALPN = "{alpn}" %}}'
    content = _render_shell('xray', 'client_outbound', {
        '__PROTO_SLUG__': proto_slug,
        '__STREAM_SLUG__': stream_slug,
        '__SECURITY_SLUG__': security_slug,
    })
    if flow_line:
        content = flow_line + '\n' + content
    if alpn_line:
        sec_inc = f"{{% include '{security_slug}' %}}"
        content = content.replace(sec_inc, f'{alpn_line}\n    {sec_inc}')
    return _wrap_client_outbound_block(f'[{content}]', 'xray', combo), slugs


def build_singbox_client_outbound(combo: ProxyCombination) -> tuple[str, list[str]]:
    proto_slug = _singbox_client_proto_slug(combo.proto)
    stream_slug = _singbox_client_streams_slug(combo.transport)
    if not proto_slug or not stream_slug:
        raise ValueError(f'Unsupported sing-box client preset: {combo.name}')
    slugs = [proto_slug, stream_slug, f'{_SINGBOX_CLIENT_ROOT}/client/tls']
    content = _render_shell(_SINGBOX_CLIENT_ROOT, 'client_outbound', {
        '__PROTO_SLUG__': proto_slug,
        '__STREAM_SLUG__': stream_slug,
    })
    return _wrap_client_outbound_block(f'[{content}]', 'singbox', combo), slugs


def build_hiddify_client_outbound(combo: ProxyCombination) -> tuple[str, list[str]]:
    proto_slug = _hiddify_client_proto_slug(combo)
    if not proto_slug:
        raise ValueError(f'Unsupported hiddify-core client preset: {combo.name}')
    if not _uses_v2ray_transport_client(combo):
        tls_slug = _hiddify_client_tls_slug(combo)
        shadowtls_slug = f'{_HIDDIFY_CLIENT_ROOT}/client/protocols/shadowtls'
        is_shadowtls_ss = (
            _raw_transport(combo.transport) == 'shadowtls'
            and _client_proto_file(combo.proto) == 'ss'
        )
        slugs = [proto_slug]
        shell_name = 'client_outbound_standalone'
        replacements = {'__PROTO_SLUG__': proto_slug, '__TLS_SLUG__': tls_slug}
        if is_shadowtls_ss:
            shell_name = 'client_outbound_shadowtls_ss'
            slugs.append(shadowtls_slug)
            replacements['__SHADOWTLS_SLUG__'] = shadowtls_slug
        else:
            slugs.append(tls_slug)
        content = _render_shell(_HIDDIFY_CLIENT_ROOT, shell_name, replacements)
        if is_shadowtls_ss:
            return _wrap_client_outbound_block(content, _HIDDIFY_CLIENT_ROOT, combo), slugs
        return _wrap_client_outbound_block(f'[{content}]', _HIDDIFY_CLIENT_ROOT, combo), slugs
    stream_slug = _hiddify_client_streams_slug(combo)
    if not stream_slug:
        raise ValueError(f'Unsupported hiddify-core client preset: {combo.name}')
    tls_slug = _hiddify_client_tls_slug(combo)
    shadowtls_slug = f'{_HIDDIFY_CLIENT_ROOT}/client/protocols/shadowtls'
    is_shadowtls_ss = (
        _raw_transport(combo.transport) == 'shadowtls'
        and _client_proto_file(combo.proto) == 'ss'
    )
    slugs = [proto_slug]
    if is_shadowtls_ss:
        slugs.append(shadowtls_slug)
    else:
        slugs.extend([stream_slug, tls_slug])
    shell_name = 'client_outbound_shadowtls_ss' if is_shadowtls_ss else 'client_outbound'
    replacements = {
        '__PROTO_SLUG__': proto_slug,
        '__STREAM_SLUG__': stream_slug,
        '__TLS_SLUG__': tls_slug,
    }
    if is_shadowtls_ss:
        replacements['__SHADOWTLS_SLUG__'] = shadowtls_slug
    content = _render_shell(_HIDDIFY_CLIENT_ROOT, shell_name, replacements)
    if is_shadowtls_ss:
        return _wrap_client_outbound_block(content, _HIDDIFY_CLIENT_ROOT, combo), slugs
    return _wrap_client_outbound_block(f'[{content}]', _HIDDIFY_CLIENT_ROOT, combo), slugs


def build_clash_client_outbound(combo: ProxyCombination) -> tuple[str, list[str]]:
    """Mihomo/Clash JSON proxy entry (YAML grammar JSON subset)."""
    network = _transport_file(combo.transport) or 'tcp'
    proto = _proto_file(combo.proto) or 'vless'
    content = (
        '{\n'
        '  "proxies": [\n'
        '    {\n'
        '      {% include \'clash/client/tag\' %}\n'
        f'      "type": "{proto}",\n'
        '      "server": "{{ proxy.server }}",\n'
        '      "port": {{ proxy.tcp_port or proxy.udp_port }},\n'
        '      "uuid": "{{ user.uuid }}",\n'
        f'      "network": "{network}",\n'
        '      "tls": {% if proxy.tls %}true{% else %}false{% endif %},\n'
        '      "servername": "{{ domain.sni }}",\n'
        '      "udp": true\n'
        '    }\n'
        '  ]\n'
        '}'
    )
    return content, ['clash/client/tag']


def build_sublink_client(combo: ProxyCombination) -> tuple[str, list[str]]:
    link_slug = _sublink_link_slug(combo)
    slugs = [
        'sublink/common/vless_uri',
        'sublink/common/encryption_none',
        'sublink/common/tls_params',
        link_slug,
    ]
    transport = _transport_file(combo.transport)
    if transport in ('ws', 'httpupgrade'):
        slugs.append('sublink/common/ws_params')
    content = load_template_slug(link_slug)
    return content, slugs


def build_all_client_configs(combo: ProxyCombination, server_core: str) -> list[dict[str, Any]]:
    """Four client cores per builtin preset: xray, singbox, hiddify-core, sublink."""
    configs: list[dict[str, Any]] = []

    if supports_xray_preset(combo):
        try:
            outbound, slugs = build_xray_client_outbound(combo)
            configs.append({
                'core': 'xray',
                'version': '',
                'outbounds_template': outbound,
                'template_slugs': slugs,
            })
        except ValueError:
            pass

    if supports_hiddify_preset(combo) or supports_xray_preset(combo):
        try:
            outbound, slugs = build_singbox_client_outbound(combo)
            configs.append({
                'core': 'singbox',
                'version': '',
                'outbounds_template': outbound,
                'template_slugs': slugs,
            })
        except ValueError:
            pass

    if supports_hiddify_preset(combo) or combo.proto == 'wireguard':
        try:
            outbound, slugs = build_hiddify_client_outbound(combo)
            configs.append({
                'core': 'hiddify-core',
                'version': '',
                'outbounds_template': outbound,
                'template_slugs': slugs,
            })
        except ValueError:
            pass

    try:
        link, slugs = build_sublink_client(combo)
        configs.append({
            'core': 'sublink',
            'version': '',
            'do_base64_after': False,
            'outbounds_template': link,
            'template_slugs': slugs,
        })
    except (ValueError, FileNotFoundError):
        pass

    if supports_xray_preset(combo):
        try:
            clash_outbound, clash_slugs = build_clash_client_outbound(combo)
            configs.append({
                'core': 'clash',
                'version': '',
                'outbounds_template': clash_outbound,
                'template_slugs': clash_slugs,
            })
        except ValueError:
            pass

    present = {c['core'] for c in configs}
    if 'sublink' not in present:
        link = default_sublink_link_template()
        configs.append({
            'core': 'sublink',
            'version': '',
            'do_base64_after': False,
            'outbounds_template': link,
            'template_slugs': [
                'sublink/common/vless_uri',
                'sublink/common/encryption_none',
                'sublink/common/tls_params',
                'sublink/links/vless_tcp',
            ],
        })
    for core in ('xray', 'singbox', 'hiddify-core', 'clash'):
        if core not in present and server_core in ('xray', 'hiddify-core'):
            configs.append({
                'core': core,
                'version': '',
                'outbounds_template': '[]',
                'template_slugs': [],
            })

    order = {name: idx for idx, name in enumerate(CLIENT_CORES)}
    configs.sort(key=lambda c: order.get(c['core'], 99))
    return configs
