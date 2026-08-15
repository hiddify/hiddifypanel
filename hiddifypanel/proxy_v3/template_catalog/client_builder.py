from __future__ import annotations

import json
from typing import Any

from ..alpn_helpers import alpn_list_for_tag, alpn_tag_uses_tls

from .fragment_loader import load_template_slug
from .paths import preset_shell_slug
from .inbound_builder import (
    _client_proto_file,
    _proto_file,
    _raw_transport,
    _transport_file,
    _uses_v2ray_transport_proto,
    _xray_client_security_slug,
    supports_hiddify_preset,
    supports_xray_preset,
)
from .proxy_matrix import ProxyCombination
from .template_defaults import default_sublink_link_template

CLIENT_CORES = ("xray", "singbox", "hiddify-core", "clash", "sublink")

_SINGBOX_CLIENT_ROOT = "singbox"
_HIDDIFY_CLIENT_ROOT = "hiddify-core"


def _client_proto_stem(combo: ProxyCombination) -> str | None:
    return _client_proto_file(combo.proto)


def _uses_v2ray_transport_client(combo: ProxyCombination) -> bool:
    proto = _client_proto_stem(combo)
    return _uses_v2ray_transport_proto(proto)


def _xhttp_combo_alpn_tags(combo: ProxyCombination) -> tuple[str, str]:
    upload = combo.params.get("upload_alpn")
    download = combo.params.get("download_alpn")
    if not upload or not download:
        default = "http" if str(combo.l3).lower() == "http" else "tls_h2"
        upload = upload or default
        download = download or default
    return str(upload), str(download)


def _xhttp_with_replacements(combo: ProxyCombination) -> dict[str, str]:
    upload_tag, download_tag = _xhttp_combo_alpn_tags(combo)
    return {
        "__ALPNS__": json.dumps(alpn_list_for_tag(upload_tag)),
        "__DOWNLOAD_ALPNS__": json.dumps(alpn_list_for_tag(download_tag)),
        "__TLS_MODE__": "true" if alpn_tag_uses_tls(upload_tag) else "false",
        "__DOWNLOAD_TLS_MODE__": "true" if alpn_tag_uses_tls(download_tag) else "false",
    }


def _render_shell(core: str, shell_name: str, replacements: dict[str, str]) -> str:
    shell = load_template_slug(preset_shell_slug(core, "client", shell_name), normalize=False)
    for key, value in replacements.items():
        shell = shell.replace(key, value)
    return shell


def _hiddify_client_streams_slug(combo: ProxyCombination) -> str | None:
    if not _uses_v2ray_transport_client(combo):
        return None
    transport = _transport_file(combo.transport)
    if not transport:
        return None
    if transport == "tcp":
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
    if combo.proto in ("ss", "shadowsocks", "v2ray"):
        return "sublink/uri/ss"
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
    if body_slug == "sublink/uri/ss":
        content = load_template_slug(body_slug)
        return content, slugs
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


def build_xray_client_outbound(combo: ProxyCombination) -> tuple[str, list[str]]:
    proto_slug = _xray_client_proto_slug(combo.proto)
    stream_slug = _xray_client_streams_slug(combo.transport)
    if not proto_slug or not stream_slug:
        raise ValueError(f"Unsupported xray client preset: {combo.name}")
    security_slug = _xray_client_security_slug(combo)
    slugs = [
        proto_slug,
        stream_slug,
        security_slug,
        "xray/client/tag",
        "xray/client/snippets/mux",
        "xray/client/snippets/fragment",
    ]
    shell_name = "outbound_xhttp" if str(combo.transport).lower() == "xhttp" else "outbound_v2ray"
    replacements = {
        "__PROTO_SLUG__": proto_slug,
        "__STREAM_SLUG__": stream_slug,
        "__SECURITY_SLUG__": security_slug,
    }
    if shell_name == "outbound_xhttp":
        replacements.update(_xhttp_with_replacements(combo))
    content = _render_shell("xray", shell_name, replacements)
    if shell_name != "outbound_xhttp" and str(combo.l3).lower() == "h3_quic":
        sec_inc = f"{{% include '{security_slug}' %}}"
        content = content.replace(sec_inc, '{% set alpns = ["h3"] %}\n    ' + sec_inc)
    return content, slugs


# Sing-box client outbounds reuse hiddify-core (same JSON dialect) unless a core-specific
# template is needed. Drivers resolve this marker to the proxy's hiddify-core client config.
USE_HIDDIFY_CORE_PLACEHOLDER = "{#use_hiddify_core()#}"


def build_singbox_client_outbound(combo: ProxyCombination) -> tuple[str, list[str]]:
    """Sing-box client: reuse hiddify-core via placeholder; mieru is not supported in sing-box."""
    if _client_proto_file(combo.proto) == "mieru":
        return "skip('mieru is not supported by sing-box')\n", []
    content = f"{{% block outbounds %}}\n{USE_HIDDIFY_CORE_PLACEHOLDER}\n{{% endblock %}}\n"
    return content, []


def _build_mieru_hiddify_client_outbound(combo: ProxyCombination) -> tuple[str, list[str]]:
    """Mieru lives on sing-box only (hiddify-core client config is empty)."""
    proto_slug = f"{_HIDDIFY_CLIENT_ROOT}/client/protocols/mieru"
    tls_slug = _hiddify_client_tls_slug(combo)
    content = _render_shell(
        _HIDDIFY_CLIENT_ROOT,
        "outbound_general",
        {"__PROTO_SLUG__": proto_slug, "__TLS_SLUG__": tls_slug},
    )
    return content, [proto_slug, tls_slug]


def build_hiddify_client_outbound(combo: ProxyCombination) -> tuple[str, list[str]]:
    if _client_proto_file(combo.proto) == "mieru":
        return _build_mieru_hiddify_client_outbound(combo)
    proto_slug = _hiddify_client_proto_slug(combo)
    if not proto_slug:
        raise ValueError(f"Unsupported hiddify-core client preset: {combo.name}")
    if not _uses_v2ray_transport_client(combo):
        tls_slug = _hiddify_client_tls_slug(combo)
        shadowtls_slug = f"{_HIDDIFY_CLIENT_ROOT}/client/protocols/shadowtls"
        is_shadowtls_ss = _raw_transport(combo.transport) == "shadowtls" and _client_proto_file(combo.proto) == "ss"
        slugs = [proto_slug]
        if _client_proto_file(combo.proto) == "wireguard":
            shell_name = "endpoint_general"
        else:
            shell_name = "outbound_general"
        replacements = {"__PROTO_SLUG__": proto_slug, "__TLS_SLUG__": tls_slug}
        if is_shadowtls_ss:
            shell_name = "outbound_with_detour"
            slugs.append(shadowtls_slug)
            replacements["__SHADOWTLS_SLUG__"] = shadowtls_slug
        else:
            slugs.append(tls_slug)
        content = _render_shell(_HIDDIFY_CLIENT_ROOT, shell_name, replacements)
        return content, slugs
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
    shell_name = "outbound_with_detour" if is_shadowtls_ss else ("outbound_xhttp" if combo.transport.lower() == "xhttp" else "outbound_v2ray")
    replacements = {
        "__PROTO_SLUG__": proto_slug,
        "__STREAM_SLUG__": stream_slug,
        "__TLS_SLUG__": tls_slug,
    }
    if is_shadowtls_ss:
        replacements["__SHADOWTLS_SLUG__"] = shadowtls_slug
    if combo.transport.lower() == "xhttp":
        replacements.update(_xhttp_with_replacements(combo))
    content = _render_shell(_HIDDIFY_CLIENT_ROOT, shell_name, replacements)
    return content, slugs


def build_clash_client_outbound(combo: ProxyCombination) -> tuple[str, list[str]]:
    """Mihomo/Clash JSON proxy entry (YAML grammar JSON subset)."""
    network = _transport_file(combo.transport) or "tcp"
    proto = _proto_file(combo.proto) or "vless"
    content = _render_shell(
        "clash",
        "outbound_general",
        {
            "__PROTO__": proto,
            "__NETWORK__": network,
        },
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

    if supports_hiddify_preset(combo) or supports_xray_preset(combo) or combo.proto == "mieru":
        try:
            outbound, _slugs = build_singbox_client_outbound(combo)
            configs.append(_builtin_client_core_entry("singbox", outbound))
        except ValueError:
            pass

    # Always pair singbox's use_hiddify_core() marker with a hiddify-core client config
    # (mieru gets an empty hiddify-core template).
    if supports_hiddify_preset(combo) or combo.proto in ("wireguard", "mieru") or supports_xray_preset(combo):
        try:
            outbound, _slugs = build_hiddify_client_outbound(combo)
            configs.append(_builtin_client_core_entry("hiddify-core", outbound))
        except ValueError:
            if combo.proto == "mieru":
                configs.append(_builtin_client_core_entry("hiddify-core", "{% block outbounds %}\n{% endblock %}\n"))

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
