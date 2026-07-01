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

CLIENT_CORES = ("xray", "singbox", "hiddify-core", "clash", "sublink")

_SINGBOX_CLIENT_ROOT = "singbox"
_HIDDIFY_CLIENT_ROOT = "hiddify-core"


def _client_proto_stem(combo: ProxyCombination) -> str | None:
    proto = _client_proto_file(combo.proto)
    if combo.proto == "hysteria2":
        return "hysteria"
    return proto


def _uses_v2ray_transport_client(combo: ProxyCombination) -> bool:
    proto = _client_proto_stem(combo)
    return _uses_v2ray_transport_proto(proto)


def _render_shell(core: str, shell_name: str, replacements: dict[str, str]) -> str:
    if core == _HIDDIFY_CLIENT_ROOT and shell_name.startswith("client_outbound"):
        shell_path = f"{core}/client/presets/{shell_name}"
    else:
        shell_path = f"{core}/presets/{shell_name}"
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
    if combo.l3 == "reality" and transport == "tcp":
        return f"{_HIDDIFY_CLIENT_ROOT}/client/stream/none"
    slug = f"{_HIDDIFY_CLIENT_ROOT}/client/stream/{transport}"
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
    if proto == "ss" and transport == "faketls":
        name = "ss_faketls"
    elif combo.proto == "v2ray":
        name = "ss_v2ray"
    else:
        name = proto
    slug = f"{_HIDDIFY_CLIENT_ROOT}/client/protocols/{name}"
    try:
        load_template_slug(slug)
        return slug
    except FileNotFoundError:
        return None


def _hiddify_client_tls_slug(combo: ProxyCombination) -> str:
    if combo.l3 == "reality":
        return f"{_HIDDIFY_CLIENT_ROOT}/client/tls/reality"
    return f"{_HIDDIFY_CLIENT_ROOT}/client/tls/tls_http"


def _sublink_transport_slug(transport: str) -> str:
    mapped = _transport_file(transport) or "tcp"
    slugs = {
        "ws": "sublink/uri/transport/ws",
        "httpupgrade": "sublink/uri/transport/httpupgrade",
        "grpc": "sublink/uri/transport/grpc",
        "tcp": "sublink/uri/transport/tcp",
        "xhttp": "sublink/uri/transport/xhttp",
    }
    return slugs.get(mapped, "sublink/uri/transport/tcp")


_URI_LINK_BODIES = frozenset(
    {
        "sublink/uri/vless",
        "sublink/uri/trojan",
    }
)


def _sublink_link_body_slug(combo: ProxyCombination) -> str:
    if combo.proto == "vmess":
        return "sublink/vmess/base"
    if combo.proto == "trojan":
        return "sublink/uri/trojan"
    return "sublink/uri/vless"


def _sublink_tls_slug(combo: ProxyCombination) -> str:
    if str(combo.l3).lower() == "reality":
        return "sublink/uri/security/reality"
    return "sublink/uri/security/tls_http"


def _vmess_transport_slug(combo: ProxyCombination) -> str:
    transport = str(_transport_file(combo.transport) or "tcp").lower()
    slugs = {
        "tcp": "sublink/vmess/transport/tcp",
        "ws": "sublink/vmess/transport/ws",
        "grpc": "sublink/vmess/transport/grpc",
        "httpupgrade": "sublink/vmess/transport/httpupgrade",
        "xhttp": "sublink/vmess/transport/xhttp",
    }
    return slugs.get(transport, "sublink/vmess/transport/tcp")


def _vmess_security_slug(combo: ProxyCombination) -> str:
    if str(combo.l3).lower() == "reality":
        return "sublink/vmess/security/reality"
    return "sublink/vmess/security/tls_http"


def _apply_sublink_vmess_placeholders(body: str, combo: ProxyCombination) -> str:
    replacements = {
        "__VMESS_TRANSPORT_SLUG__": _vmess_transport_slug(combo),
        "__VMESS_SECURITY_SLUG__": _vmess_security_slug(combo),
    }
    for placeholder, slug in replacements.items():
        body = body.replace(f"{{% include '{placeholder}' %}}", f"{{% include '{slug}' %}}")
    return body


def _apply_sublink_body_placeholders(body: str, combo: ProxyCombination) -> str:
    transport_slug = _sublink_transport_slug(combo.transport)
    tls_slug = _sublink_tls_slug(combo)
    body = body.replace("{% include '__TLS_SLUG__' %}", f"{{% include '{tls_slug}' %}}")
    body = body.replace("{% include '__TRANSPORT_SLUG__' %}", f"{{% include '{transport_slug}' %}}")
    return body


def render_sublink_link_template(combo: ProxyCombination) -> str:
    body_slug = _sublink_link_body_slug(combo)
    body = load_template_slug(body_slug)
    if body_slug in _URI_LINK_BODIES:
        body = _apply_sublink_body_placeholders(body, combo)
    elif body_slug == "sublink/vmess/base":
        body = _apply_sublink_vmess_placeholders(body, combo)
    return body


def build_sublink_client(combo: ProxyCombination) -> tuple[str, list[str]]:
    transport_slug = _sublink_transport_slug(combo.transport)
    body_slug = _sublink_link_body_slug(combo)
    tls_slug = _sublink_tls_slug(combo)
    slugs = ["sublink/tag", body_slug]
    if body_slug in _URI_LINK_BODIES:
        slugs.extend(
            [
                "sublink/uri/final_link_maker",
                tls_slug,
                transport_slug,
            ]
        )
        if transport_slug == "sublink/uri/transport/xhttp":
            slugs.extend(["sublink/uri/xhttp_extra", "sublink/xhttp_download_settings"])
    elif body_slug == "sublink/vmess/base":
        slugs.extend(
            [
                _vmess_transport_slug(combo),
                _vmess_security_slug(combo),
            ]
        )
        if _vmess_transport_slug(combo) == "sublink/vmess/transport/xhttp":
            slugs.extend(["sublink/vmess/xhttp_extra", "sublink/xhttp_download_settings"])
    content = render_sublink_link_template(combo)
    return content, slugs


def _singbox_client_streams_slug(transport: str) -> str | None:
    mapped = _transport_file(transport)
    if not mapped:
        return None
    slug = f"{_SINGBOX_CLIENT_ROOT}/client/streams/{mapped}"
    try:
        load_template_slug(slug)
        return slug
    except FileNotFoundError:
        return None


def _singbox_client_proto_slug(proto: str) -> str | None:
    mapped = _proto_file(proto)
    if not mapped:
        return None
    slug = f"{_SINGBOX_CLIENT_ROOT}/client/protocols/{mapped}"
    try:
        load_template_slug(slug)
        return slug
    except FileNotFoundError:
        return None


def _xray_client_streams_slug(transport: str) -> str | None:
    mapped = _transport_file(transport)
    if not mapped:
        return None
    slug = f"xray/client/streams/{mapped}"
    try:
        load_template_slug(slug)
        return slug
    except FileNotFoundError:
        return "xray/client/streams/tcp"


def _xray_client_proto_slug(proto: str) -> str | None:
    mapped = _proto_file(proto)
    if not mapped:
        return None
    slug = f"xray/client/protocols/{mapped}"
    try:
        load_template_slug(slug)
        return slug
    except FileNotFoundError:
        return None


def _unwrap_json_array_shell(body: str) -> str:
    stripped = (body or "").strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        return stripped[1:-1].strip()
    return stripped


def _client_outbound_block_name(core: str, combo: ProxyCombination) -> str:
    if _client_proto_file(combo.proto) == "wireguard":
        return "endpoints"
    return "outbounds"


def _wrap_client_outbound_block(body: str, core: str, combo: ProxyCombination) -> str:
    block = _client_outbound_block_name(core, combo)
    inner = _unwrap_json_array_shell((body or "").strip())
    return f"{{% block {block} %}}\n{inner}\n{{% endblock %}}"


def build_xray_client_outbound(combo: ProxyCombination) -> tuple[str, list[str]]:
    proto_slug = _xray_client_proto_slug(combo.proto)
    stream_slug = _xray_client_streams_slug(combo.transport)
    if not proto_slug or not stream_slug:
        raise ValueError(f"Unsupported xray client preset: {combo.name}")
    security_slug = _xray_security_slug(combo)
    slugs = [proto_slug, stream_slug, security_slug, "xray/snippets/stream_sockopt", "xray/snippets/sniffing"]
    flow_line = ""
    alpn_line = ""
    if combo.proto == "vless":
        flow_line = "{% set FLOW = hconfig.vless_flow %}"
    if security_slug == "xray/common/security/tls_alpn":
        alpn = combo.params["download"]["alpn"]
        alpn_line = f'{{% set ALPN = "{alpn}" %}}'
    content = _render_shell(
        "xray",
        "client_outbound_v2ray",
        {
            "__PROTO_SLUG__": proto_slug,
            "__STREAM_SLUG__": stream_slug,
            "__SECURITY_SLUG__": security_slug,
        },
    )
    if flow_line:
        content = flow_line + "\n" + content
    if alpn_line:
        sec_inc = f"{{% include '{security_slug}' %}}"
        content = content.replace(sec_inc, f"{alpn_line}\n    {sec_inc}")
    return _wrap_client_outbound_block(f"[{content}]", "xray", combo), slugs


def build_singbox_client_outbound(combo: ProxyCombination) -> tuple[str, list[str]]:
    proto_slug = _singbox_client_proto_slug(combo.proto)
    stream_slug = _singbox_client_streams_slug(combo.transport)
    if not proto_slug or not stream_slug:
        raise ValueError(f"Unsupported sing-box client preset: {combo.name}")
    slugs = [proto_slug, stream_slug, f"{_SINGBOX_CLIENT_ROOT}/client/tls"]
    content = _render_shell(
        _SINGBOX_CLIENT_ROOT,
        "client_outbound_v2ray",
        {
            "__PROTO_SLUG__": proto_slug,
            "__STREAM_SLUG__": stream_slug,
        },
    )
    return _wrap_client_outbound_block(f"[{content}]", "singbox", combo), slugs


def build_hiddify_client_outbound(combo: ProxyCombination) -> tuple[str, list[str]]:
    proto_slug = _hiddify_client_proto_slug(combo)
    if not proto_slug:
        raise ValueError(f"Unsupported hiddify-core client preset: {combo.name}")
    if not _uses_v2ray_transport_client(combo):
        tls_slug = _hiddify_client_tls_slug(combo)
        shadowtls_slug = f"{_HIDDIFY_CLIENT_ROOT}/client/protocols/shadowtls"
        is_shadowtls_ss = _raw_transport(combo.transport) == "shadowtls" and _client_proto_file(combo.proto) == "ss"
        slugs = [proto_slug]
        shell_name = "client_outbound_standalone"
        replacements = {"__PROTO_SLUG__": proto_slug, "__TLS_SLUG__": tls_slug}
        if is_shadowtls_ss:
            shell_name = "client_outbound_shadowtls_ss"
            slugs.append(shadowtls_slug)
            replacements["__SHADOWTLS_SLUG__"] = shadowtls_slug
        else:
            slugs.append(tls_slug)
        content = _render_shell(_HIDDIFY_CLIENT_ROOT, shell_name, replacements)
        if is_shadowtls_ss:
            return _wrap_client_outbound_block(content, _HIDDIFY_CLIENT_ROOT, combo), slugs
        return _wrap_client_outbound_block(f"[{content}]", _HIDDIFY_CLIENT_ROOT, combo), slugs
    stream_slug = _hiddify_client_streams_slug(combo)
    if not stream_slug:
        raise ValueError(f"Unsupported hiddify-core client preset: {combo.name}")
    tls_slug = _hiddify_client_tls_slug(combo)
    shadowtls_slug = f"{_HIDDIFY_CLIENT_ROOT}/client/protocols/shadowtls"
    is_shadowtls_ss = _raw_transport(combo.transport) == "shadowtls" and _client_proto_file(combo.proto) == "ss"
    slugs = [proto_slug]
    if is_shadowtls_ss:
        slugs.append(shadowtls_slug)
    else:
        slugs.extend([stream_slug, tls_slug])
    shell_name = "client_outbound_shadowtls_ss" if is_shadowtls_ss else "client_outbound_v2ray"
    replacements = {
        "__PROTO_SLUG__": proto_slug,
        "__STREAM_SLUG__": stream_slug,
        "__TLS_SLUG__": tls_slug,
    }
    if is_shadowtls_ss:
        replacements["__SHADOWTLS_SLUG__"] = shadowtls_slug
    content = _render_shell(_HIDDIFY_CLIENT_ROOT, shell_name, replacements)
    if is_shadowtls_ss:
        return _wrap_client_outbound_block(content, _HIDDIFY_CLIENT_ROOT, combo), slugs
    return _wrap_client_outbound_block(f"[{content}]", _HIDDIFY_CLIENT_ROOT, combo), slugs


def build_clash_client_outbound(combo: ProxyCombination) -> tuple[str, list[str]]:
    """Mihomo/Clash JSON proxy entry (YAML grammar JSON subset)."""
    network = _transport_file(combo.transport) or "tcp"
    proto = _proto_file(combo.proto) or "vless"
    content = (
        "{\n"
        '  "proxies": [\n'
        "    {\n"
        "      {% include 'clash/client/tag' %}\n"
        f'      "type": "{proto}",\n'
        '      "server": "{{ proxy.server }}",\n'
        '      "port": {{ proxy.tcp_port or proxy.udp_port }},\n'
        '      "uuid": "{{ user.uuid }}",\n'
        f'      "network": "{network}",\n'
        '      "tls": {% if proxy.tls %}true{% else %}false{% endif %},\n'
        '      "servername": "{{ domain.sni }}",\n'
        '      "udp": true\n'
        "    }\n"
        "  ]\n"
        "}"
    )
    return content, ["clash/client/tag"]


def _builtin_client_core_entry(core: str, outbound: str) -> dict[str, Any]:
    return {
        "core": core,
        "version": "",
        "slug": f"client-{core}",
        "is_builtin": True,
        "outbounds_template": outbound,
    }


def build_all_client_configs(combo: ProxyCombination, server_core: str) -> list[dict[str, Any]]:
    """Four client cores per builtin preset: xray, singbox, hiddify-core, sublink."""
    configs: list[dict[str, Any]] = []

    if supports_xray_preset(combo):
        try:
            outbound, _slugs = build_xray_client_outbound(combo)
            configs.append(_builtin_client_core_entry("xray", outbound))
        except ValueError:
            pass

    if supports_hiddify_preset(combo) or supports_xray_preset(combo):
        try:
            outbound, _slugs = build_singbox_client_outbound(combo)
            configs.append(_builtin_client_core_entry("singbox", outbound))
        except ValueError:
            pass

    if supports_hiddify_preset(combo) or combo.proto == "wireguard":
        try:
            outbound, _slugs = build_hiddify_client_outbound(combo)
            configs.append(_builtin_client_core_entry("hiddify-core", outbound))
        except ValueError:
            pass

    try:
        link, _slugs = build_sublink_client(combo)
        configs.append(_builtin_client_core_entry("sublink", link))
    except (ValueError, FileNotFoundError):
        pass

    if supports_xray_preset(combo):
        try:
            clash_outbound, _clash_slugs = build_clash_client_outbound(combo)
            configs.append(_builtin_client_core_entry("clash", clash_outbound))
        except ValueError:
            pass

    present = {c["core"] for c in configs}
    if "sublink" not in present:
        link = default_sublink_link_template()
        configs.append(_builtin_client_core_entry("sublink", link))
    for core in ("xray", "singbox", "hiddify-core", "clash"):
        if core not in present and server_core in ("xray", "hiddify-core"):
            configs.append(_builtin_client_core_entry(core, "[]"))

    order = {name: idx for idx, name in enumerate(CLIENT_CORES)}
    configs.sort(key=lambda c: order.get(c["core"], 99))
    return configs
