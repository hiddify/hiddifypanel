from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from typing import Any

import json5
import yaml
from jinja2 import TemplateSyntaxError, UndefinedError
from jinja2.exceptions import TemplateError

from hiddifypanel import hutils
from hiddifypanel.hutils.flask import parse_user_agent
from hiddifypanel.models import CustomProxy, CustomProxyMode
from hiddifypanel.models.proxy_base_config import BaseConfigSide, default_base_content

from .alpn_helpers import (
    alpn_http_for_tag,
    alpn_list_for_tag,
    alpn_tls_for_tag,
    alpns_for_combo,
    normalize_alpn_tag,
    normalize_alpn_tags,
)
from .client_core_auto import (
    resolve_auto_client_cores,
    resolve_default_client_core,
    resolve_primary_auto_client_core,
)
from .sublink_format import build_sublink_formats


def _client_outbounds_template(cc: dict[str, Any]) -> str:
    return str(cc.get("outbounds_template") or cc.get("link_template") or "")


def _keep_common_proxy_client_core(data: dict[str, Any], core_name: str, child_id: int) -> bool:
    if not data.get("is_common_proxy"):
        return True
    return not common_proxy_core_blocks(True, core_name, hconfig(ConfigEnum.common_proxy_core, child_id))


from hiddifypanel.models.config import hconfig
from hiddifypanel.models.config_enum import ConfigEnum
from hiddifypanel.proxy_v3.context_vars.builder.utils import common_proxy_core_blocks, fix_duplicate_json_commas
from hiddifypanel.proxy_v3.context_vars.version import PlatformPart as _PlatformPart
from hiddifypanel.proxy_v3.context_vars.version import TemplateVersion

from .custom_proxy_ports import mode_requires_static_ports, mode_uses_auto_ports, mode_uses_gateway_port, normalize_port_list, primary_resolved_port, resolve_inbound_ports
from .jinja_context import TemplateSkip, build_template_context
from .outbound_tags import deduplicate_client_tags
from hiddifypanel.proxy_v3.config_builder.base_config import resolve_base_config_content
from hiddifypanel.proxy_v3.config_builder.jinja_render import render_template_text as _render_template_text
from hiddifypanel.proxy_v3.config_builder.render import render_fragment_section as _render_fragment_section_impl
from hiddifypanel.proxy_v3.config_builder.render import render_section as _render_section_impl
from hiddifypanel.proxy_v3.config_builder.template_blocks import (
    extract_block_body as _extract_block_body,
    fragment_block_body as _fragment_block_body,
    inject_named_fragment_blocks as _inject_named_fragment_blocks,
    inject_template_block as _inject_template_block,
)
from .template_variables import build_domain_context, build_user_context

SAMPLE_UUID = "00000000-0000-0000-0000-000000000001"

SERVER_BUNDLE_CORES: tuple[str, ...] = ("hiddify-core", "xray", "haproxy", "nginx", "rust-rpxy-l4")


@dataclass(frozen=True)
class _ClientRenderVariant:
    alpn_tag: str
    download_alpn_tag: str | None = None
    domain_mode: str | None = None


def _proxy_server_tag(data: dict[str, Any], proxy_id: int | None = None) -> str:
    pid = int(proxy_id if proxy_id is not None else data.get("id") or 0)
    name = str(data.get("name") or data.get("slug") or "proxy")
    safe_name = re.sub(r"[^\w.-]+", "_", name.strip()).strip("_") or "proxy"
    return f"{pid}_{safe_name}"


def _client_outbound_tag(
    data: dict[str, Any],
    proxy_id: int | None,
    alpn_tag: str,
    domain_mode: str | None = None,
) -> str:
    base = _proxy_server_tag(data, proxy_id)
    if domain_mode:
        return f"{base}_{alpn_tag}_{domain_mode}"
    return f"{base}_{alpn_tag}"


_PROXY_JSON_KEY_ORDER: tuple[str, ...] = (
    "type",
    "protocol",
    "tag",
    "listen",
    "listen_port",
    "port",
    "server",
    "server_port",
    "network",
    "transport",
    "streamSettings",
    "sniffing",
    "settings",
    "tls",
    "multiplex",
    "uuid",
    "password",
    "version",
)


def _order_proxy_dict(item: dict[str, Any]) -> dict[str, Any]:
    ordered: dict[str, Any] = {}
    for key in _PROXY_JSON_KEY_ORDER:
        if key in item:
            ordered[key] = item[key]
    for key, value in item.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def _sanitize_parsed_config(parsed: Any) -> Any:
    if isinstance(parsed, list):
        return [_order_proxy_dict(item) if isinstance(item, dict) else item for item in parsed]
    if not isinstance(parsed, dict):
        return parsed
    for key in ("outbounds", "endpoints", "inbounds"):
        items = parsed.get(key)
        if isinstance(items, list):
            parsed[key] = [_order_proxy_dict(item) if isinstance(item, dict) else item for item in items if isinstance(item, dict) and item]
    return parsed


EXAMPLE_USER_AGENTS: list[dict[str, str]] = [
    {
        "id": "hiddify",
        "label": "HiddifyNext 4.2 (Android)",
        "value": "HiddifyNext/4.2.0 (android) like ClashMeta v2ray sing-box",
    },
    {
        "id": "sfa",
        "label": "SFA / sing-box 1.7",
        "value": "SFA/1.7.0 (sing-box 1.7.0)",
    },
    {
        "id": "foxray",
        "label": "FoXray (iOS)",
        "value": "FoXray",
    },
    {
        "id": "xray",
        "label": "xray 26.3.27",
        "value": "xray/26.3.27",
    },
    {
        "id": "clash",
        "label": "Clash Meta",
        "value": "ClashMeta/1.18.0",
    },
]


def build_render_context(
    child_id: int = 0,
    data: dict[str, Any] | None = None,
    *,
    tag: str | None = None,
    port: int | None = None,
    ip: str | None = None,
    custom_path: str | None = None,
    domain_binding: str | None = None,
    server_side: bool = False,
    domain_id: int | None = None,
    domain_host: str | None = None,
    user_id: int | None = None,
    user_uuid: str | None = None,
    user_agent: str | None = None,
    skip_network_lookup: bool = False,
    proxy_id: int | None = None,
    alpn_tag: str | None = None,
    download_alpn_tag: str | None = None,
    outbound_tag: str | None = None,
    domain_mode: str | None = None,
    core: str | None = None,
    core_version: str | None = None,
) -> dict[str, Any]:
    data = data or {}
    server_config = data.get("server_config") or {}
    base_tag = tag or server_config.get("tag") or data.get("slug") or "example-tag"
    effective_proxy_id = proxy_id if proxy_id is not None else data.get("id")
    download_alpn = ""
    download_alpn_list: list[str] = []
    alpn_tags = normalize_alpn_tags(data.get("alpns") or [], {})
    download_alpn_tags = normalize_alpn_tags(data.get("download_alpns") or [], {})
    if not alpn_tags:
        from hiddifypanel.models import get_hconfigs

        from hiddifypanel.proxy_v3.alpn_helpers import resolve_proxy_alpn_pairs
        from hiddifypanel.proxy_v3.context_vars.hconfig import HConfigVar

        hconfigs = HConfigVar(get_hconfigs(child_id), server_side=server_side)
        pairs = resolve_proxy_alpn_pairs(
            tls_layer=str(data.get("tls_layer") or "").lower() or None,
            transport=_infer_proxy_transport(data),
            proto=_infer_proxy_proto(data),
            hconfigs=hconfigs,
            categories=list(data.get("categories") or []),
        )
        alpn_tags = [upload.to_tag() for upload, _ in pairs if upload.to_tag()]
        download_alpn_tags = [download.to_tag() for _, download in pairs if download and download.to_tag()]
    if server_side and effective_proxy_id:
        resolved_tag = _proxy_server_tag(data, int(effective_proxy_id))
        proxy_l3 = _infer_proxy_l3(data)
        if not alpn_tags:
            alpn_tags = alpns_for_combo(proxy_l3, _infer_proxy_transport(data), _infer_proxy_proto(data))
        resolved_alpn = normalize_alpn_tag(str(server_config.get("tag") or base_tag))
        use_tls = alpn_tls_for_tag(resolved_alpn) if resolved_alpn else False
        alpn_list = alpn_list_for_tag(resolved_alpn) if resolved_alpn else []
    else:
        server_tag = str(server_config.get("tag") or base_tag).strip()
        default_alpn = normalize_alpn_tag(str((alpn_tags or [server_tag])[0]))
        resolved_alpn = normalize_alpn_tag(alpn_tag) if alpn_tag else default_alpn
        if not alpn_tags:
            proxy_l3 = _infer_proxy_l3(data)
            alpn_tags = alpns_for_combo(proxy_l3, _infer_proxy_transport(data), _infer_proxy_proto(data))
        use_tls = alpn_tls_for_tag(resolved_alpn)
        proxy_l3 = _infer_proxy_l3(data)
        resolved_tag = server_tag
        download_alpn = normalize_alpn_tag(download_alpn_tag) if download_alpn_tag else ""
        alpn_list = alpn_list_for_tag(resolved_alpn) if resolved_alpn else []
        download_alpn_list = alpn_list_for_tag(download_alpn) if download_alpn else []
    resolved_path = custom_path if custom_path is not None else (data.get("custom_path") or "test-path")
    protocol = _proxy_mode_value(data)
    binding = domain_binding
    if binding is None:
        binding = "ip" if protocol == CustomProxyMode.ip.value else "domain"
    resolved_ip = (ip or "").strip()
    if not resolved_ip:
        if skip_network_lookup:
            resolved_ip = "203.0.113.1"
        else:
            resolved_ip = hutils.network.get_ip_str(4) or "203.0.113.1"
    effective_domain_id = domain_id
    stored_tcp = normalize_port_list(server_config.get("inbound_tcp_ports") or server_config.get("inbound_port"))
    stored_udp = normalize_port_list(server_config.get("inbound_udp_ports"))
    if not protocol:
        from hiddifypanel.proxy_v3.context_vars.ports import ResolvedInboundPorts

        resolved_ports = ResolvedInboundPorts([443], [443], 443, 443)
    elif effective_proxy_id:
        resolved_ports = resolve_inbound_ports(
            protocol,
            int(effective_proxy_id),
            domain_id=effective_domain_id,
            db_tcp_ports=stored_tcp,
            db_udp_ports=stored_udp,
            server_side=server_side,
            tls_layer=data.get("tls_layer"),
        )
    else:
        resolved_ports = resolve_inbound_ports(
            protocol,
            0,
            domain_id=effective_domain_id,
            db_tcp_ports=stored_tcp,
            db_udp_ports=stored_udp,
            server_side=server_side,
            tls_layer=data.get("tls_layer"),
        )
    if port is not None:
        resolved_port = port
    else:
        resolved_port = primary_resolved_port(resolved_ports)
    domain_data = build_domain_context(
        child_id,
        domain_id=domain_id,
        domain_host=domain_host,
        server_ip=resolved_ip if binding == "ip" else None,
        skip_network_lookup=skip_network_lookup,
    )
    if domain_mode:
        domain_data = dict(domain_data)
        domain_data["mode"] = domain_mode
    if binding == "ip":
        domain_data = dict(domain_data)
        domain_data["server"] = resolved_ip
        domain_data["ip"] = resolved_ip
    user, users = build_user_context(user_id=user_id, user_uuid=user_uuid)
    ua = user_agent or EXAMPLE_USER_AGENTS[1]["value"]
    ua_parsed = parse_user_agent(ua)
    direct_port_access = bool(server_config.get("direct_port_access"))
    ctx = build_template_context(
        child_id,
        user=user,
        domain_data=domain_data,
        tag=resolved_tag,
        port=resolved_port,
        ip=resolved_ip,
        custom_path=resolved_path,
        domain_binding=binding,
        user_agent=ua,
        user_agent_parsed=ua_parsed,
        server_side=server_side,
        users=users,
        proxy_data={
            "id": effective_proxy_id,
            "mode": protocol,
            "tag": resolved_tag,
            "port": resolved_port,
            "tcp_ports": resolved_ports.tcp_ports,
            "udp_ports": resolved_ports.udp_ports,
            "tcp_port": resolved_ports.tcp_port,
            "udp_port": resolved_ports.udp_port,
            "direct_port_access": direct_port_access,
            "domain_binding": binding,
            "alpn": resolved_alpn if not server_side else "",
            "alpns": alpn_tags,
            "download_alpns": download_alpn_tags,
            "alpn_list": alpn_list,
            "download_alpn": download_alpn if not server_side else "",
            "download_alpn_list": download_alpn_list if not server_side else [],
            "tls": use_tls if not server_side else False,
            "http": alpn_http_for_tag(resolved_alpn) if not server_side else False,
            "l3": proxy_l3,
            "reality": proxy_l3 == "reality",
            "transport": _infer_proxy_transport(data),
            "proto": _infer_proxy_proto(data),
            "tls_layer": str(data.get("tls_layer") or "").lower() or None,
            "download_tls_layer": str(data.get("download_tls_layer") or "").lower() or None,
            "download_domain_modes": list(data.get("download_domain_modes") or []),
            "domain_modes": list(data.get("domain_modes") or []),
            "server_inbound_tcp_ports": stored_tcp,
            "server_inbound_udp_ports": stored_udp,
        },
    )
    ctx["alpns"] = alpn_list
    adapted = ctx.get("ctx")
    if server_side and core:
        version = TemplateVersion((core_version or "").strip() or "1.0.0")
        platform = adapted.get("platform") if adapted is not None else None
        if platform is not None and hasattr(platform, "_data"):
            platform._data["app"] = _PlatformPart(core, version)
            platform._data["app_version"] = version
    if not server_side:
        outbound_tag = (outbound_tag or base_tag or "").strip()
        if adapted is not None:
            adapted["client_proxy_tags"] = [outbound_tag] if outbound_tag else []
            if resolved_alpn:
                adapted["alpn_builtin_value"] = resolved_alpn
            download_tls_layer = str(data.get("download_tls_layer") or "").lower()
            if download_tls_layer:
                adapted["download_tls"] = download_tls_layer != "http"
            elif download_alpn:
                adapted["download_tls"] = alpn_tls_for_tag(download_alpn)
        else:
            ctx["client_proxy_tags"] = [outbound_tag] if outbound_tag else []
            if resolved_alpn:
                ctx["alpn_builtin_value"] = resolved_alpn
            download_tls_layer = str(data.get("download_tls_layer") or "").lower()
            if download_tls_layer:
                ctx["download_tls"] = download_tls_layer != "http"
            elif download_alpn:
                ctx["download_tls"] = alpn_tls_for_tag(download_alpn)
    return ctx


def build_sample_context(
    child_id: int = 0,
    tag: str = "validate-tag",
    port: int = 2080,
    *,
    ip: str = "203.0.113.1",
    custom_path: str = "test-path",
    domain_binding: str = "domain",
    server_side: bool = False,
    proxy_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = build_render_context(
        child_id,
        tag=tag,
        port=port,
        ip=ip,
        custom_path=custom_path,
        domain_binding=domain_binding,
        server_side=server_side,
        user_agent="HiddifyNext/3.0.0 (android) like ClashMeta v2ray sing-box",
    )
    if proxy_data:
        adapted = ctx.get("ctx")
        existing = adapted.get("proxy") if adapted is not None else ctx.get("proxy")
        if existing is not None and hasattr(existing, "model_dump"):
            merged = existing.model_dump()
        elif isinstance(existing, dict):
            merged = dict(existing)
        else:
            merged = {}
        merged.update(proxy_data)
        if adapted is not None:
            adapted["proxy"] = merged
        else:
            ctx["proxy"] = merged
    return ctx


def _client_core_label(core_name: str, version: str) -> str:
    ver = (version or "").strip()
    if core_name == "hiddify-core":
        return f"hiddify-core ≥ {ver}" if ver else "hiddify-core"
    return f"{core_name}{f' ≥ {ver}' if ver else ''}"


def _strip_empty_link_lines(text: str) -> str:
    return "\n".join(line for line in (text or "").splitlines() if line.strip())


def render_template_text(template_text: str, child_id: int = 0, context: dict[str, Any] | None = None) -> str:
    ctx = context or build_sample_context(child_id=child_id)
    return _render_template_text(template_text, child_id, ctx)


def _trim_leading_empty_lines(text: str) -> str:
    if not text:
        return text
    lines = text.splitlines()
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    if start == 0:
        return text
    trimmed = "\n".join(lines[start:])
    if text.endswith("\n") and not trimmed.endswith("\n"):
        trimmed += "\n"
    return trimmed


def parse_json5(text: str) -> tuple[Any | None, str | None]:
    stripped = _trim_leading_empty_lines(fix_duplicate_json_commas(text.strip()))
    if not stripped:
        return None, None
    try:
        return json5.loads(stripped), None
    except Exception as e:
        return None, str(e)


def _parse_error_location(message: str) -> tuple[int | None, int | None]:
    line_match = re.search(r"<string>:(\d+)", message or "")
    col_match = re.search(r"column (\d+)", message or "")
    line = int(line_match.group(1)) if line_match else None
    column = int(col_match.group(1)) if col_match else None
    return line, column


def _error_excerpt(source: str, line: int | None, *, context: int = 4) -> str:
    if not source:
        return ""
    if not line or line < 1:
        return source
    lines = source.splitlines()
    start = max(0, line - 1 - context)
    end = min(len(lines), line + context)
    parts: list[str] = []
    for index in range(start, end):
        marker = ">>>" if index == line - 1 else "   "
        parts.append(f"{marker} {index + 1:4}| {lines[index]}")
    return "\n".join(parts)


def _infer_jinja_error_line(template_source: str, message: str) -> int | None:
    if not template_source:
        return None
    lower_msg = (message or "").lower()
    lines = template_source.splitlines()
    if "non-namespace" in lower_msg or "cannot assign attribute" in lower_msg:
        for idx, line in enumerate(lines, 1):
            if re.search(r"\{%[-\s]*set\s+\w+\.\w+\s*=", line):
                return idx
    if "unexpected end" in lower_msg or "endblock" in lower_msg:
        depth = 0
        last_open: int | None = None
        for idx, line in enumerate(lines, 1):
            for match in re.finditer(r"\{%-?\s*(block|endblock)\b", line):
                if match.group(1) == "block":
                    depth += 1
                    last_open = idx
                elif depth > 0:
                    depth -= 1
        if depth > 0 and last_open:
            return last_open
    return None


def _error_detail_phase(message: str) -> str:
    return "json5" if _parse_error_location(message)[0] else "jinja"


def _render_error_detail(
    message: str,
    *,
    source: str = "",
    phase: str = "render",
    line: int | None = None,
    column: int | None = None,
    label: str | None = None,
    template_source: str | None = None,
) -> dict[str, Any]:
    parsed_line, parsed_column = _parse_error_location(message)
    resolved_line = line or parsed_line
    resolved_column = column if column is not None else parsed_column
    resolved_phase = phase if phase != "render" else _error_detail_phase(message)
    template_text = template_source or ""
    if resolved_phase == "jinja":
        if not resolved_line and template_text:
            resolved_line = _infer_jinja_error_line(template_text, message)
        display_source = template_text or source
    else:
        display_source = source or template_text
    detail: dict[str, Any] = {
        "phase": resolved_phase,
        "line": resolved_line,
        "column": resolved_column,
        "message": message,
        "source": display_source,
        "excerpt": _error_excerpt(display_source, resolved_line),
    }
    if template_text and template_text != display_source:
        detail["template_source"] = template_text
        detail["template_excerpt"] = _error_excerpt(template_text, resolved_line)
    if label:
        detail["label"] = label
    return detail


def _build_error_detail_for_section(
    section: dict[str, Any],
    *,
    label: str | None = None,
) -> dict[str, Any] | None:
    error = section.get("error")
    if not error:
        return None
    phase = _error_detail_phase(error)
    prior = section.get("error_detail") or {}
    template_source = prior.get("template_source") or prior.get("source") or ""
    if phase == "json5":
        source = section.get("rendered") or prior.get("source") or ""
        return _render_error_detail(error, source=source, phase="json5", label=label)
    return _render_error_detail(
        error,
        source=template_source,
        template_source=template_source or None,
        phase="jinja",
        line=prior.get("line"),
        column=prior.get("column"),
        label=label,
    )


def _ensure_section_error_detail(section: dict[str, Any] | None) -> dict[str, Any]:
    if not section:
        return {}
    error = section.get("error")
    if not error:
        if section.get("error_detail"):
            return {**section, "error_detail": None}
        return section
    detail = section.get("error_detail")
    if detail and detail.get("message") == error:
        return section
    rebuilt = _build_error_detail_for_section(section)
    return {**section, "error_detail": rebuilt}


def _append_render_issue(
    issues: list[dict[str, Any]],
    *,
    code: str,
    message: str,
    section: dict[str, Any] | None = None,
    label: str | None = None,
) -> None:
    issue: dict[str, Any] = {"code": code, "message": message}
    synced = _ensure_section_error_detail(section)
    detail = synced.get("error_detail")
    if detail:
        if label and not detail.get("label"):
            detail = {**detail, "label": label}
        issue["detail"] = detail
    issues.append(issue)


def _wrap_as_json_object(fragment: str) -> str:
    fragment = fragment.strip().rstrip(",")
    if not fragment:
        return "{}"
    if fragment.startswith("["):
        return fragment
    # Comma-separated objects (e.g. {% for domain %} presets) → JSON array.
    if re.search(r"\}\s*,\s*\{", fragment):
        return "[\n" + fragment + "\n]"
    if fragment.startswith("{"):
        return fragment
    return "{\n" + fragment + "\n}"


def _looks_like_jinja_template(text: str) -> bool:
    return "{%" in (text or "") or "{{" in (text or "")


def _json5_text_for_parse(text: str) -> str:
    stripped = (text or "").strip().rstrip(",")
    if not stripped:
        return stripped
    if stripped.startswith("["):
        return stripped
    if re.search(r"\}\s*,\s*\{", stripped):
        return _wrap_as_json_object(stripped)
    if not stripped.startswith("{"):
        return _wrap_as_json_object(stripped)
    return stripped


def validate_listen_rules(
    protocol: str | None,
    compiled_text: str,
    direct_port_access: bool = False,
) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    listen_match = re.search(r'"listen"\s*:\s*"([^"]+)"', compiled_text)
    if not listen_match:
        return warnings
    listen = listen_match.group(1)
    if direct_port_access and listen in ("0.0.0.0", "::"):
        warnings.append(
            {
                "code": "direct_port_access",
                "message": "Direct port access is enabled; binding to all interfaces may make the server discoverable",
            }
        )
    if protocol == CustomProxyMode.domains_auto_public_ports.value:
        if listen not in ("0.0.0.0", "::1"):
            warnings.append(
                {
                    "code": "listen_custom",
                    "message": "For multi-domain auto ports, listen should be 0.0.0.0 or ::1",
                }
            )
    elif protocol and protocol != CustomProxyMode.domains_auto_public_ports.value:
        if direct_port_access:
            if listen not in ("127.0.0.1", "0.0.0.0", "::1"):
                warnings.append(
                    {
                        "code": "listen_direct_port",
                        "message": "With direct port access, listen should be 127.0.0.1 or 0.0.0.0",
                    }
                )
        elif listen != "127.0.0.1":
            warnings.append(
                {
                    "code": "listen_non_custom",
                    "message": "For non-custom protocols, listen should be 127.0.0.1",
                }
            )
    return warnings


def validate_port_rules(compiled_text: str, port: int | None = None) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for p in re.findall(r'"port"\s*:\s*(\d+)', compiled_text):
        if int(p) in (80, 443):
            errors.append({"code": "port_reserved", "message": f"Port {p} is not allowed (80/443)"})
    if port in (80, 443):
        errors.append({"code": "port_reserved", "message": f"Port {port} is not allowed (80/443)"})
    return errors


def validate_core_placeholders(template_text: str, core: str | None) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    has_tag = "proxy.tag" in template_text or "{{TAG}}" in template_text or "{{ TAG }}" in template_text
    has_port = "proxy.tcp_port" in template_text or "proxy.udp_port" in template_text or "{{PORT}}" in template_text or "{{ PORT }}" in template_text
    if core == "xray":
        if not has_tag:
            errors.append({"code": "missing_tag", "message": "Xray template must include proxy.tag (or {{TAG}})"})
        if not has_port:
            errors.append({"code": "missing_port", "message": "Xray template must include proxy.tcp_port or proxy.udp_port (or {{PORT}})"})
        if re.search(r'"port"\s*:\s*\d+', template_text) and not has_port:
            errors.append({"code": "hardcoded_port", "message": "Use proxy.tcp_port or proxy.udp_port instead of a numeric port for xray"})
    elif core == "hiddify-core":
        if not has_tag:
            errors.append({"code": "missing_tag", "message": "Hiddify-core template must include proxy.tag (or {{TAG}})"})
        if not has_port:
            errors.append({"code": "missing_listen_port", "message": "Hiddify-core template must include proxy.tcp_port or proxy.udp_port (or {{PORT}}) for listen_port"})
        if re.search(r'"listen_port"\s*:\s*\d+', template_text) and not has_port:
            errors.append({"code": "hardcoded_port", "message": "Use proxy.tcp_port or proxy.udp_port instead of a numeric listen_port"})
    return errors


def validate_proxy_payload(
    data: dict[str, Any],
    child_id: int = 0,
    proxy_id: int | None = None,
    sections: list[str] | None = None,
) -> dict[str, Any]:
    sections = sections or ["server", "client", "general"]
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    compiled_preview = ""
    compiled_json: Any = None

    if proxy_id:
        proxy = CustomProxy.query.filter(CustomProxy.id == proxy_id, CustomProxy.child_id == child_id).first()
        if proxy:
            merged = proxy.to_dict()
            merged.update(data)
            data = merged

    protocol = _proxy_mode_value(data)
    binding = "ip" if protocol == CustomProxyMode.ip.value else "domain"
    is_builtin = bool(data.get("is_builtin"))
    server_override = bool(data.get("server_override"))
    client_override = bool(data.get("client_override"))
    validate_server = (not is_builtin) or server_override
    validate_client = (not is_builtin) or client_override
    server_config = data.get("server_config") or {}
    client_config = data.get("client_config") or {}
    tag = server_config.get("tag") or data.get("slug") or "validate-tag"
    stored_tcp = normalize_port_list(server_config.get("inbound_tcp_ports") or server_config.get("inbound_port"))
    stored_udp = normalize_port_list(server_config.get("inbound_udp_ports"))
    proxy_row_id = int(proxy_id or data.get("id") or 0)
    client_ports = resolve_inbound_ports(
        protocol or "",
        proxy_row_id,
        db_tcp_ports=stored_tcp,
        db_udp_ports=stored_udp,
        server_side=False,
        tls_layer=data.get("tls_layer"),
    )
    server_ports = resolve_inbound_ports(
        protocol or "",
        proxy_row_id,
        db_tcp_ports=stored_tcp,
        db_udp_ports=stored_udp,
        server_side=True,
        tls_layer=data.get("tls_layer"),
    )
    client_port = primary_resolved_port(client_ports)
    server_port = primary_resolved_port(server_ports)
    core = server_config.get("core") or "xray"
    direct_port_access = bool(server_config.get("direct_port_access"))
    resolved_ip = "203.0.113.1"
    ctx_client = build_render_context(
        child_id,
        data,
        tag=tag,
        port=client_port,
        ip=resolved_ip,
        custom_path=data.get("custom_path") or "test-path",
        domain_binding=binding,
        server_side=False,
        skip_network_lookup=True,
        proxy_id=proxy_id or data.get("id"),
    )
    ctx_server = build_render_context(
        child_id,
        data,
        tag=tag,
        port=server_port,
        ip=resolved_ip,
        custom_path=data.get("custom_path") or "test-path",
        domain_binding=binding,
        server_side=True,
        skip_network_lookup=True,
        proxy_id=proxy_id or data.get("id"),
        core=core,
    )

    if "server" in sections and validate_server:
        inbound_template = server_config.get("inbound_template") or ""
        errors.extend(validate_core_placeholders(inbound_template, core))
        if inbound_template.strip():
            try:
                rendered = fix_duplicate_json_commas(render_template_text(inbound_template, child_id, ctx_server))
                compiled_preview = _wrap_as_json_object(rendered)
                compiled_json, parse_err = parse_json5(compiled_preview)
                if parse_err:
                    errors.append({"code": "json5_parse", "message": parse_err})
                else:
                    warnings.extend(validate_listen_rules(protocol, compiled_preview, direct_port_access))
                    errors.extend(validate_port_rules(compiled_preview, server_port))
            except TemplateSkip:
                warnings.append(
                    {
                        "code": "template_skip",
                        "message": "Server template skipped for current settings (SKIP)",
                    }
                )
            except (TemplateError, TemplateSyntaxError, UndefinedError) as e:
                errors.append({"code": "jinja_error", "message": str(e)})

    if "client" in sections and validate_client:
        for idx, cc in enumerate(client_config.get("core_configs") or []):
            core_name = cc.get("core") or ""
            if core_name == "sublink":
                tpl = _client_outbounds_template(cc)
                if tpl.strip():
                    try:
                        section, formats = _compose_sublink_full_config(
                            child_id,
                            ctx_client,
                            version=cc.get("version") or "",
                            outbounds_template=tpl,
                        )
                        if section.get("error"):
                            errors.append(
                                {
                                    "code": "sublink_jinja_error",
                                    "message": f"core_configs[{idx}]: {section['error']}",
                                }
                            )
                        elif formats.get("parse_error"):
                            warnings.append(
                                {
                                    "code": "sublink_parse",
                                    "message": f"core_configs[{idx}]: {formats['parse_error']}",
                                }
                            )
                    except TemplateSkip:
                        pass
                    except (TemplateError, TemplateSyntaxError, UndefinedError) as e:
                        errors.append({"code": "sublink_jinja_error", "message": f"core_configs[{idx}]: {e}"})
                continue
            tpl = cc.get("outbounds_template") or ""
            if not tpl.strip():
                continue
            if core_name in ("hiddify-core", "singbox"):
                try:
                    version = cc.get("version") or ""
                    outbound_body, endpoint_body, err_section = _collect_client_fragment_bodies(
                        child_id,
                        data,
                        tpl,
                        core_name=core_name,
                        proxy_id=proxy_id or data.get("id"),
                        domain_id=None,
                        domain_host=None,
                        ip=resolved_ip,
                        user_id=None,
                        user_uuid=None,
                        user_agent=None,
                        errors=errors,
                        warnings=warnings,
                        label=f"core_configs[{idx}]",
                    )
                    section = _compose_singbox_client_config(
                        child_id,
                        ctx_client,
                        core=core_name,
                        version=version,
                        outbound_template=tpl,
                        outbound_body=outbound_body if outbound_body else None,
                        endpoint_body=endpoint_body if endpoint_body else None,
                    )
                    if section.get("error"):
                        errors.append(
                            {
                                "code": "client_json5_parse",
                                "message": f"core_configs[{idx}]: {section['error']}",
                            }
                        )
                    elif err_section and err_section.get("error") and not section.get("parsed"):
                        errors.append(
                            {
                                "code": "client_jinja_error",
                                "message": f"core_configs[{idx}]: {err_section['error']}",
                            }
                        )
                except TemplateSkip:
                    pass
                except (TemplateError, TemplateSyntaxError, UndefinedError) as e:
                    errors.append({"code": "client_jinja_error", "message": f"core_configs[{idx}]: {e}"})
                continue
            try:
                block_name = _client_block_name(core_name)
                body = _extract_block_body(tpl, block_name) or tpl
                rendered = fix_duplicate_json_commas(render_template_text(body, child_id, ctx_client))
                wrapped = _wrap_as_json_object(rendered)
                _, parse_err = parse_json5(wrapped)
                if parse_err:
                    errors.append({"code": "client_json5_parse", "message": f"core_configs[{idx}]: {parse_err}"})
            except TemplateSkip:
                pass
            except (TemplateError, TemplateSyntaxError, UndefinedError) as e:
                errors.append({"code": "client_jinja_error", "message": f"core_configs[{idx}]: {e}"})

    if "general" in sections:
        domain_ids = [int(v) for v in (data.get("domain_ids") or []) if v is not None]
        if mode_requires_static_ports(protocol):
            if not stored_tcp:
                errors.append(
                    {
                        "code": "missing_inbound_tcp_ports",
                        "message": "At least one inbound TCP port is required for this mode",
                    }
                )
        elif mode_uses_auto_ports(protocol) or mode_uses_gateway_port(protocol):
            if stored_tcp or stored_udp:
                warnings.append(
                    {
                        "code": "ignored_inbound_ports",
                        "message": "Inbound ports are calculated automatically for this mode and will be ignored",
                    }
                )
        if protocol == CustomProxyMode.domains_l7_gateway.value:
            allowed = {"direct", "cdn", "relay"}
            invalid = [m for m in (data.get("domain_modes") or []) if m not in allowed]
            if invalid:
                errors.append(
                    {
                        "code": "invalid_domain_modes",
                        "message": "L7 gateway domain modes must be direct, cdn, or relay",
                    }
                )
            try:
                from hiddifypanel.models.custom_proxy import (
                    validate_tls_layer_domain_modes,
                    xhttp_download_is_quic,
                    xhttp_upload_is_quic,
                    _parse_tls_layer,
                )

                validate_tls_layer_domain_modes(
                    _parse_tls_layer(data.get("tls_layer")),
                    list(data.get("domain_modes") or []),
                )
                categories = list(data.get("categories") or [])
                if xhttp_upload_is_quic(categories) and "reality" in (data.get("domain_modes") or []):
                    errors.append(
                        {
                            "code": "invalid_domain_modes",
                            "message": "REALITY is incompatible with QUIC upload in xhttp",
                        }
                    )
            except ValueError as exc:
                errors.append({"code": "invalid_tls_layer_domain_modes", "message": str(exc)})
            transport_key = _infer_proxy_transport(data)
            l7_key = str(data.get("l7_reverse_proto") or "").lower()
            if transport_key == "xhttp" and l7_key == "h2":
                allowed_dl_modes = {"direct", "cdn", "relay"}
                dl_modes = [str(m).strip().lower() for m in (data.get("download_domain_modes") or []) if str(m).strip()]
                invalid_dl = [m for m in dl_modes if m not in allowed_dl_modes]
                if invalid_dl:
                    errors.append(
                        {
                            "code": "invalid_download_domain_modes",
                            "message": "download_domain_modes must be direct, cdn, or relay",
                        }
                    )
                dl_tls = str(data.get("download_tls_layer") or "").strip().lower()
                if dl_tls == "http" and "reality" in dl_modes:
                    errors.append(
                        {
                            "code": "invalid_download_tls_layer",
                            "message": "HTTP download TLS layer is incompatible with reality domain modes",
                        }
                    )
                if xhttp_download_is_quic(categories) and "reality" in dl_modes:
                    errors.append(
                        {
                            "code": "invalid_download_domain_modes",
                            "message": "REALITY is incompatible with QUIC download in xhttp",
                        }
                    )
            elif data.get("download_tls_layer") or data.get("download_domain_modes"):
                errors.append(
                    {
                        "code": "invalid_download_xhttp_fields",
                        "message": "download_tls_layer and download_domain_modes apply only to xhttp with l7_reverse_proto=h2",
                    }
                )
        elif protocol == CustomProxyMode.domains_sni_gateway.value:
            allowed = {"fake", "direct", "relay", "reality"}
            invalid = [m for m in (data.get("domain_modes") or []) if m not in allowed]
            if invalid:
                errors.append(
                    {
                        "code": "invalid_domain_modes",
                        "message": "SNI gateway domain modes must be fake, direct, relay, or reality",
                    }
                )
        elif protocol == CustomProxyMode.domains_auto_public_ports.value:
            allowed = {"direct", "relay"}
            invalid = [m for m in (data.get("domain_modes") or []) if m not in allowed]
            if invalid:
                errors.append(
                    {
                        "code": "invalid_domain_modes",
                        "message": "Auto public port domain modes must be direct or relay",
                    }
                )
        elif protocol == CustomProxyMode.domains_single_public_port.value:
            allowed = {"direct", "relay"}
            invalid = [m for m in (data.get("domain_modes") or []) if m not in allowed]
            if invalid:
                errors.append(
                    {
                        "code": "invalid_domain_modes",
                        "message": "Single public port domain modes must be direct or relay",
                    }
                )
        elif protocol == CustomProxyMode.ip.value:
            allowed = {"direct", "relay"}
            invalid = [m for m in (data.get("domain_modes") or []) if m not in allowed]
            if invalid:
                errors.append(
                    {
                        "code": "invalid_domain_modes",
                        "message": "IP mode domain modes must be direct or relay",
                    }
                )

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "compiled_preview": compiled_preview,
        "compiled_json": compiled_json,
    }


def validate_base_config_content(data: dict[str, Any], child_id: int = 0) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    core = data.get("core") or ""
    content = data.get("content") or ""
    if not content.strip():
        return {"ok": True, "errors": errors, "warnings": warnings}
    ctx = build_sample_context(child_id=child_id)
    if core == "sublink":
        try:
            render_template_text(content, child_id, ctx)
        except TemplateSkip:
            pass
        except (TemplateError, TemplateSyntaxError, UndefinedError) as e:
            errors.append({"code": "jinja_error", "message": str(e)})
        return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings}
    try:
        rendered = fix_duplicate_json_commas(render_template_text(content, child_id, ctx))
        wrapped = _wrap_as_json_object(rendered)
        _, parse_err = parse_json5(wrapped)
        if parse_err:
            errors.append({"code": "json5_parse", "message": parse_err})
    except TemplateSkip:
        pass
    except (TemplateError, TemplateSyntaxError, UndefinedError) as e:
        errors.append({"code": "jinja_error", "message": str(e)})
    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings}


def _preview_result_from_section(section: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": not section.get("error") and not section.get("skipped"),
        "rendered": section.get("rendered") or "",
        "parsed": section.get("parsed"),
        "skipped": bool(section.get("skipped")),
        "error": section.get("error"),
        "error_detail": section.get("error_detail"),
        "warnings": [],
    }


def _format_fragment_preview(rendered: str, core: str) -> dict[str, Any]:
    text = (rendered or "").strip()
    if not text:
        return {"ok": True, "rendered": "", "parsed": None, "skipped": False, "error": None, "warnings": []}
    if core == "sublink":
        return {"ok": True, "rendered": rendered, "parsed": None, "skipped": False, "error": None, "warnings": []}
    wrapped = _json5_text_for_parse(text)
    parsed = None
    parse_err = None
    if wrapped.strip().startswith(("{", "[")):
        parsed, parse_err = parse_json5(wrapped)
    if parse_err:
        return {
            "ok": False,
            "rendered": rendered,
            "parsed": None,
            "skipped": False,
            "error": parse_err,
            "warnings": [],
        }
    if parsed is not None:
        return {
            "ok": True,
            "rendered": json.dumps(parsed, indent=2, ensure_ascii=False),
            "parsed": parsed,
            "skipped": False,
            "error": None,
            "warnings": [],
        }
    return {"ok": True, "rendered": rendered, "parsed": None, "skipped": False, "error": None, "warnings": []}


def preview_proxy_template_fragment(
    data: dict[str, Any],
    *,
    child_id: int = 0,
    proxy_id: int | None = None,
    side: str,
    core: str,
    template: str,
    domain: str | None = None,
    domain_id: int | None = None,
    user_id: int | None = None,
    user_uuid: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    ignore_skip: bool = True,
    require_user: bool = False,
) -> dict[str, Any]:
    """Render inbound/outbound template fragment only (no base-config merge)."""
    tpl = (template or "").strip()
    if not tpl:
        return {"ok": True, "rendered": "", "parsed": None, "skipped": False, "error": None, "warnings": []}

    if proxy_id:
        proxy = CustomProxy.query.filter(CustomProxy.id == proxy_id, CustomProxy.child_id == child_id).first()
        if proxy:
            merged = proxy.to_dict()
            merged.update(data)
            data = merged

    side_val = (side or "").strip().lower()
    server_side = side_val == "server"
    if require_user and not server_side:
        user, _users = build_user_context(user_id=user_id, user_uuid=user_uuid)
        if not user.get("uuid"):
            return {
                "ok": False,
                "rendered": "",
                "parsed": None,
                "skipped": False,
                "error": "User is required for client template preview",
                "warnings": [],
            }

    server_config = data.get("server_config") or {}
    protocol = _proxy_mode_value(data)
    tag = server_config.get("tag") or data.get("slug") or "preview-tag"
    resolved_ip = (ip or "").strip() or "203.0.113.1"
    resolved_ua = (user_agent or "").strip() or EXAMPLE_USER_AGENTS[1]["value"]
    stored_tcp = normalize_port_list(server_config.get("inbound_tcp_ports") or server_config.get("inbound_port"))
    stored_udp = normalize_port_list(server_config.get("inbound_udp_ports"))
    resolved_ports = resolve_inbound_ports(
        protocol or "",
        int(proxy_id or data.get("id") or 0),
        domain_id=domain_id,
        db_tcp_ports=stored_tcp,
        db_udp_ports=stored_udp,
        server_side=server_side,
        tls_layer=data.get("tls_layer"),
    )
    port = primary_resolved_port(resolved_ports)

    server_domain_id = domain_id
    server_domain_host = domain
    if protocol == CustomProxyMode.domains_l7_gateway.value:
        server_domain_id = None
        server_domain_host = None

    ctx = build_render_context(
        child_id,
        data,
        tag=tag,
        port=port,
        ip=resolved_ip,
        domain_id=server_domain_id if server_side else domain_id,
        domain_host=server_domain_host if server_side else domain,
        user_id=user_id,
        user_uuid=user_uuid,
        user_agent=resolved_ua,
        server_side=server_side,
        skip_network_lookup=True,
        proxy_id=proxy_id or data.get("id"),
        core=core if server_side else None,
    )
    if ignore_skip:
        ctx["ignore_skip"] = True
    _scope_example_context(
        ctx,
        proxy_id=proxy_id or data.get("id"),
        domain_id=server_domain_id if server_side else domain_id,
        domain_host=server_domain_host if server_side else domain,
        server_side=server_side,
    )

    block_name = _server_block_name(core) if server_side else _client_block_name(core)

    if server_side or core == "sublink":
        frag = _render_fragment_section(child_id, ctx, tpl, block_name, parse_json=False)
        if frag.get("skipped"):
            return {"ok": True, "rendered": "SKIP", "parsed": None, "skipped": True, "error": None, "warnings": []}
        if frag.get("error"):
            return {**_preview_result_from_section(frag), "warnings": []}
        rendered = _normalize_fragment_body(frag.get("rendered") or "")
        return _format_fragment_preview(rendered, core)

    parts: list[str] = []
    variant_errors: list[str] = []
    for variant in _client_render_variants(data):
        alpn_ctx = _build_proxy_context(
            child_id,
            data,
            domain_id=domain_id,
            domain_host=domain,
            ip=resolved_ip,
            user_id=user_id,
            user_uuid=user_uuid,
            user_agent=resolved_ua,
            server_side=False,
            proxy_id=proxy_id or data.get("id"),
            **_variant_context_kwargs(variant),
        )
        alpn_ctx["client_core"] = core
        if ignore_skip:
            alpn_ctx["ignore_skip"] = True
        frag = _render_fragment_section(child_id, alpn_ctx, tpl, block_name, parse_json=False)
        if frag.get("skipped"):
            continue
        if frag.get("error"):
            variant_errors.append(str(frag.get("error")))
            continue
        body = _normalize_fragment_body(frag.get("rendered") or "")
        if body:
            parts.append(body)
    if variant_errors and not parts:
        return {
            "ok": False,
            "rendered": "",
            "parsed": None,
            "skipped": False,
            "error": variant_errors[0],
            "warnings": [{"code": "variant_error", "message": msg} for msg in variant_errors[1:]],
        }
    result = _format_fragment_preview(",\n".join(parts), core)
    if variant_errors:
        result["warnings"] = [{"code": "variant_error", "message": msg} for msg in variant_errors]
    return result


def preview_base_config_content(
    data: dict[str, Any],
    *,
    child_id: int = 0,
    domain: str | None = None,
    domain_id: int | None = None,
    user_id: int | None = None,
    user_uuid: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    ignore_skip: bool = True,
) -> dict[str, Any]:
    """Render full base config shell with preview context (not merged with proxy fragments)."""
    core = data.get("core") or ""
    content = (data.get("content") or "").strip()
    side = data.get("side") or BaseConfigSide.client.value
    if not content:
        return {"ok": True, "rendered": "", "parsed": None, "skipped": False, "error": None, "warnings": []}

    server_side = side == BaseConfigSide.server.value or side == "server"
    resolved_ip = (ip or "").strip() or "203.0.113.1"
    resolved_ua = (user_agent or "").strip() or EXAMPLE_USER_AGENTS[1]["value"]
    ctx = build_render_context(
        child_id,
        {},
        ip=resolved_ip,
        domain_id=domain_id,
        domain_host=domain,
        user_id=user_id,
        user_uuid=user_uuid,
        user_agent=resolved_ua,
        server_side=server_side,
        skip_network_lookup=True,
        core=core if server_side else None,
    )
    if ignore_skip:
        ctx["ignore_skip"] = True
    _scope_example_context(
        ctx,
        proxy_id=None,
        domain_id=domain_id,
        domain_host=domain,
        server_side=server_side,
    )

    if core == "sublink":
        try:
            rendered = render_template_text(content, child_id, ctx)
            return {"ok": True, "rendered": rendered, "parsed": None, "skipped": False, "error": None, "warnings": []}
        except TemplateSkip:
            return {"ok": True, "rendered": "SKIP", "parsed": None, "skipped": True, "error": None, "warnings": []}
        except (TemplateError, TemplateSyntaxError, UndefinedError) as e:
            return {"ok": False, "rendered": "", "parsed": None, "skipped": False, "error": str(e), "warnings": []}

    base = _extract_block_body(content, "base_config") or content
    as_json = core not in ("haproxy", "nginx", "rust-rpxy-l4")
    section = _render_section(base, child_id, ctx, as_json_object=as_json)
    parsed = section.get("parsed")
    if isinstance(parsed, dict):
        sanitized = _sanitize_parsed_config(copy.deepcopy(parsed))
        section = {
            **section,
            "parsed": sanitized,
            "rendered": json.dumps(sanitized, indent=2, ensure_ascii=False),
        }
    return {**_preview_result_from_section(section), "warnings": []}


def _server_block_name(core: str) -> str:
    return "inbounds" if core == "hiddify-core" else "inbound"


def _client_block_name(core: str) -> str:
    return "outbounds"


_BUILTIN_OUTBOUND_TAGS = frozenset({"direct", "block", "dns-out", "bypass", "freedom", "blackhole"})
_SELECTOR_TAGS = frozenset({"Select", "Auto", "proxy_select", "proxy_auto"})


def _ua_version_gte(ua_parsed: dict, version_key: str, major: int, minor: int = 0, patch: int = 0) -> bool:
    raw_v = ua_parsed.get(version_key)
    if not raw_v:
        return False
    u_major = raw_v[0] if len(raw_v) > 0 else 0
    u_minor = raw_v[1] if len(raw_v) > 1 else 0
    u_patch = raw_v[2] if len(raw_v) > 2 else 0
    user_agent_v = f"{u_major}.{u_minor}.{u_patch}"
    needed_version = f"{major}.{minor}.{patch}"
    res = hutils.utils.compare_versions(user_agent_v, needed_version)
    return res == 0 or res == 1


def _wireguard_to_endpoints(ua_parsed: dict) -> bool:
    return _ua_version_gte(ua_parsed, "hiddify_version", 4, 0, 0)


def _split_outbounds(outbounds: list) -> tuple[list, list, list]:
    selectors: list[dict] = []
    proxies: list[dict] = []
    builtins: list[dict] = []
    for item in outbounds:
        if not isinstance(item, dict):
            continue
        tag = item.get("tag", "")
        if tag in _SELECTOR_TAGS or item.get("type") in ("selector", "urltest"):
            selectors.append(item)
        elif tag in _BUILTIN_OUTBOUND_TAGS:
            builtins.append(item)
        else:
            proxies.append(item)
    return selectors, proxies, builtins


def _selectable_outbound_tag(outbound: dict) -> str | None:
    tag = outbound.get("tag")
    if not tag or not isinstance(tag, str):
        return None
    if "shadowtls-out" in tag or "§hide§" in tag:
        return None
    return tag


def _partition_client_fragments(items: list[dict], ua_parsed: dict) -> tuple[list[dict], list[dict]]:
    outbounds: list[dict] = []
    endpoints: list[dict] = []
    use_endpoints = _wireguard_to_endpoints(ua_parsed)
    for item in items:
        if use_endpoints and item.get("type") == "wireguard":
            endpoints.append(item)
        else:
            outbounds.append(item)
    return outbounds, endpoints


def _parsed_to_items(parsed: Any) -> list[dict]:
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        if "proxies" in parsed and isinstance(parsed["proxies"], list):
            return [item for item in parsed["proxies"] if isinstance(item, dict)]
        return [parsed]
    return []


def _inject_singbox_selectors(outbounds: list, tags: list[str]) -> list:
    filtered = [tag for tag in tags if tag and "shadowtls-out" not in tag and "§hide§" not in tag]
    select = {
        "type": "selector",
        "tag": "Select",
        "outbounds": ["Auto", *filtered],
        "default": "Auto",
    }
    auto = {
        "type": "urltest",
        "tag": "Auto",
        "outbounds": filtered,
        "url": "https://www.gstatic.com/generate_204",
        "interval": "10m",
        "tolerance": 200,
    }
    return [select, auto, *outbounds]


def _update_singbox_selectors(selectors: list[dict], tags: list[str]) -> list[dict]:
    filtered = [tag for tag in tags if tag and "shadowtls-out" not in tag and "§hide§" not in tag]
    updated: list[dict] = []
    for item in selectors:
        if item.get("tag") == "Select":
            updated.append({**item, "outbounds": ["Auto", *filtered], "default": "Auto"})
        elif item.get("tag") == "Auto":
            updated.append({**item, "outbounds": filtered})
        else:
            updated.append(item)
    return updated


def _finalize_singbox_client_section(section: dict[str, Any], core: str, ua_parsed: dict) -> dict[str, Any]:
    if core not in ("hiddify-core", "singbox"):
        return section
    parsed = section.get("parsed")
    if not isinstance(parsed, dict):
        if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
            section = {**section, "parsed": parsed[0]}
            parsed = parsed[0]
        else:
            return section

    merged = copy.deepcopy(parsed)
    outbounds = list(merged.get("outbounds") or [])
    endpoints = list(merged.get("endpoints") or [])

    selectors, proxy_items, builtins = _split_outbounds(outbounds)
    proxy_out, wg_endpoints = _partition_client_fragments(proxy_items, ua_parsed)
    proxy_out = deduplicate_client_tags(proxy_out)
    endpoints.extend(wg_endpoints)

    tags = [_selectable_outbound_tag(item) for item in proxy_out]
    tags = [tag for tag in tags if tag]
    if selectors:
        merged["outbounds"] = _update_singbox_selectors(selectors, tags) + proxy_out + builtins
    else:
        merged["outbounds"] = _inject_singbox_selectors(proxy_out + builtins, tags)
    if endpoints:
        merged["endpoints"] = endpoints

    route = merged.get("route")
    if isinstance(route, dict):
        route["final"] = "Select"
    else:
        merged["route"] = {"final": "Select", "rules": []}

    rendered = json.dumps(merged, indent=2, ensure_ascii=False)
    return {
        **section,
        "rendered": rendered,
        "parsed": merged,
    }


def _is_full_config_dict(value: dict[str, Any]) -> bool:
    return bool(set(value.keys()) & {"outbounds", "inbounds", "route", "endpoints", "log"})


def _parsed_fragment_items(section: dict[str, Any]) -> list[dict[str, Any]]:
    parsed = section.get("parsed")
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict) and not _is_full_config_dict(parsed):
        return [parsed]
    rendered = (section.get("rendered") or "").strip().rstrip(",")
    if not rendered:
        return []
    if rendered.startswith("["):
        rebound, err = parse_json5(rendered)
        if not err and isinstance(rebound, list):
            return [item for item in rebound if isinstance(item, dict)]
    if re.search(r"\}\s*,\s*\{", rendered):
        rebound, err = parse_json5(_wrap_as_json_object(rendered))
        if not err and isinstance(rebound, list):
            return [item for item in rebound if isinstance(item, dict)]
    return []


def _ua_parsed_from_context(context: dict[str, Any]) -> dict[str, Any]:
    platform = context.get("platform")
    if platform is not None:
        data = getattr(platform, "_data", None)
        if isinstance(data, dict) and data:
            return dict(data)
    return {}


def _coerce_singbox_style_config_section(
    section: dict[str, Any],
    *,
    child_id: int,
    context: dict[str, Any],
    core: str,
    version: str = "",
    side: str | Any = BaseConfigSide.client.value,
    fragment_template: str = "",
    ua_parsed: dict[str, Any] | None = None,
    _depth: int = 0,
) -> dict[str, Any]:
    """Ensure hiddify-core / sing-box example output is one JSON object, not a top-level array."""
    if core not in ("hiddify-core", "singbox"):
        return section
    if _depth > 2:
        return section

    parsed = section.get("parsed")
    if isinstance(parsed, dict) and _is_full_config_dict(parsed):
        sanitized = _sanitize_parsed_config(copy.deepcopy(parsed))
        rendered = json.dumps(sanitized, indent=2, ensure_ascii=False)
        return {
            **section,
            "parsed": sanitized,
            "rendered": rendered,
            "error": section.get("error"),
        }

    items = _parsed_fragment_items(section)
    if not items:
        return section

    side_val = side.value if hasattr(side, "value") else str(side)
    ua = ua_parsed if ua_parsed is not None else _ua_parsed_from_context(context)

    if side_val == BaseConfigSide.client.value:
        outbound_items, endpoint_items = _partition_client_fragments(items, ua)
        return _compose_singbox_client_config(
            child_id,
            context,
            core=core,
            version=version,
            outbound_template=fragment_template,
            outbound_items=outbound_items or None,
            endpoint_items=endpoint_items or None,
            _coerce_depth=_depth + 1,
        )
    if core == "hiddify-core":
        inbound_body = _rendered_client_block_body(items)
        return _compose_server_config(
            child_id,
            context,
            core=core,
            version=version,
            inbound_template=inbound_body or fragment_template,
            _coerce_depth=_depth + 1,
        )
    return section


def _proxy_mode_value(data: dict[str, Any]) -> str:
    mode = data.get("mode")
    if hasattr(mode, "value"):
        return mode.value
    return str(mode or "")


def _infer_proxy_l3(data: dict[str, Any]) -> str:
    explicit = data.get("tls_layer")
    if explicit not in (None, ""):
        if str(explicit).lower() == "http":
            return "http"
    for token in data.get("categories") or []:
        key = str(token).lower()
        if key == "reality":
            return "reality"
        if key == "http":
            return "http"
        if key == "quic":
            return "h3_quic"
    return "tls"


_TRANSPORT_CATEGORIES = frozenset({"ws", "grpc", "tcp", "httpupgrade", "xhttp", "shadowtls", "faketls", "udp", "custom"})
_PROTO_CATEGORIES = frozenset({"vless", "vmess", "trojan", "shadowsocks", "ss", "v2ray", "tuic", "hysteria", "hysteria2", "wireguard", "ssh", "socks", "naive", "mieru", "anytls", "dnstt", "snell"})


def _infer_proxy_transport(data: dict[str, Any]) -> str:
    from hiddifypanel.models.custom_proxy import _parse_transport

    explicit = data.get("transport")
    if explicit not in (None, ""):
        return _parse_transport(explicit).value.lower()
    for token in data.get("categories") or []:
        key = str(token).lower()
        if key in _TRANSPORT_CATEGORIES:
            return key
    return "tcp"


def _infer_proxy_proto(data: dict[str, Any]) -> str:
    from hiddifypanel.models.custom_proxy import _normalize_proto_key

    explicit = _normalize_proto_key(str(data.get("proto") or "").strip().lower())
    if explicit:
        return explicit
    for token in data.get("categories") or []:
        key = _normalize_proto_key(str(token).lower())
        if key in _PROTO_CATEGORIES:
            return key
    return "vless"


def _client_uses_template_alpn_loop(core_name: str) -> bool:
    return core_name in ("hiddify-core", "singbox")


def _client_render_variants(data: dict[str, Any]) -> list[_ClientRenderVariant]:
    from hiddifypanel.models import get_hconfigs

    from hiddifypanel.proxy_v3.alpn_helpers import resolve_proxy_alpn_pairs
    from hiddifypanel.proxy_v3.context_vars.hconfig import HConfigVar

    hconfigs = HConfigVar(get_hconfigs(0), server_side=False)
    pairs = resolve_proxy_alpn_pairs(
        tls_layer=str(data.get("tls_layer") or "").lower() or None,
        transport=_infer_proxy_transport(data),
        proto=_infer_proxy_proto(data),
        hconfigs=hconfigs,
        categories=list(data.get("categories") or []),
    )
    if pairs:
        return [
            _ClientRenderVariant(
                alpn_tag=upload.to_tag(),
                download_alpn_tag=download.to_tag() if download else None,
            )
            for upload, download in pairs
            if upload.to_tag()
        ]
    default = normalize_alpn_tag(str((data.get("server_config") or {}).get("tag") or data.get("slug") or "tls_h2"))
    return [_ClientRenderVariant(alpn_tag=default)]


def _variant_context_kwargs(variant: _ClientRenderVariant) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "domain_mode": variant.domain_mode,
    }
    if variant.alpn_tag:
        kwargs["alpn_tag"] = variant.alpn_tag
    if variant.download_alpn_tag:
        kwargs["download_alpn_tag"] = variant.download_alpn_tag
    return kwargs


def _variant_label(variant: _ClientRenderVariant) -> str:
    label = variant.alpn_tag or "template"
    if variant.download_alpn_tag:
        label = f"{label}/{variant.download_alpn_tag}"
    if variant.domain_mode:
        label = f"{label}/{variant.domain_mode}"
    return label


def _build_proxy_context(
    child_id: int,
    data: dict[str, Any],
    *,
    domain_id: int | None,
    domain_host: str | None,
    ip: str | None,
    user_id: int | None,
    user_uuid: str | None,
    user_agent: str | None,
    server_side: bool,
    proxy_id: int | None = None,
    alpn_tag: str | None = None,
    download_alpn_tag: str | None = None,
    domain_mode: str | None = None,
    core: str | None = None,
    core_version: str | None = None,
) -> dict[str, Any]:
    if server_side:
        from hiddifypanel.proxy_v3.context_vars.builder.server_builder import (
            build_proxy_jinja_context,
            resolve_custom_proxy,
        )

        pid = proxy_id if proxy_id is not None else data.get("id")
        proxy = resolve_custom_proxy(child_id, int(pid) if pid is not None else None)
        if proxy is None:
            return build_render_context(
                child_id,
                data,
                user_id=user_id,
                user_uuid=user_uuid,
                user_agent=user_agent,
                server_side=True,
                skip_network_lookup=True,
                ip=(ip or "").strip() or "203.0.113.1",
                proxy_id=proxy_id,
                domain_id=domain_id,
                domain_host=domain_host,
                core=core,
                core_version=core_version,
            )
        return build_proxy_jinja_context(
            child_id,
            proxy,
            core=core or "xray",
            domain_id=domain_id,
            domain_host=domain_host,
            user_id=user_id,
            user_uuid=user_uuid,
        )

    protocol = _proxy_mode_value(data)
    binding = "ip" if protocol == CustomProxyMode.ip.value else "domain"
    resolved_ip = (ip or "").strip() or "203.0.113.1"
    kwargs: dict[str, Any] = {
        "child_id": child_id,
        "data": data,
        "user_id": user_id,
        "user_uuid": user_uuid,
        "user_agent": user_agent,
        "server_side": server_side,
        "skip_network_lookup": True,
        "ip": resolved_ip,
        "proxy_id": proxy_id if proxy_id is not None else data.get("id"),
        "alpn_tag": alpn_tag,
        "download_alpn_tag": download_alpn_tag,
        "domain_mode": domain_mode,
        "core": core,
        "core_version": core_version,
    }
    if binding != "ip":
        kwargs["domain_id"] = domain_id
        kwargs["domain_host"] = domain_host
    ctx = build_render_context(**kwargs)
    pid = proxy_id if proxy_id is not None else data.get("id")
    if binding != "ip":
        _scope_example_context(
            ctx,
            proxy_id=int(pid) if pid is not None else None,
            domain_id=domain_id,
            domain_host=domain_host,
            server_side=server_side,
        )
    return ctx


def _build_bundle_context(
    child_id: int,
    *,
    domain_id: int | None,
    domain_host: str | None,
    ip: str | None,
    user_id: int | None,
    user_uuid: str | None,
    user_agent: str | None,
    server_side: bool = False,
) -> dict[str, Any]:
    if server_side:
        from hiddifypanel.proxy_v3.context_vars.builder.server_builder import build_bundle_jinja_context

        return build_bundle_jinja_context(
            child_id,
            domain_id=domain_id,
            domain_host=domain_host,
            user_id=user_id,
            user_uuid=user_uuid,
        )

    ctx = build_render_context(
        child_id,
        {},
        ip=(ip or "").strip() or "203.0.113.1",
        domain_id=domain_id,
        domain_host=domain_host,
        user_id=user_id,
        user_uuid=user_uuid,
        user_agent=user_agent,
        server_side=server_side,
        skip_network_lookup=True,
    )
    _scope_example_context(
        ctx,
        proxy_id=None,
        domain_id=domain_id,
        domain_host=domain_host,
        server_side=server_side,
    )
    return ctx


def _render_base_section(
    child_id: int,
    context: dict[str, Any],
    side: str,
    core: str,
    version: str = "",
) -> dict[str, Any]:
    base = resolve_base_config_content(child_id, side, core, version)
    base = _extract_block_body(base, "base_config") or base
    as_json = core not in ("haproxy", "nginx", "rust-rpxy-l4")
    section = _render_section(base, child_id, context, as_json_object=as_json)
    parsed = section.get("parsed")
    if isinstance(parsed, dict):
        section = {
            **section,
            "parsed": _sanitize_parsed_config(copy.deepcopy(parsed)),
            "rendered": json.dumps(_sanitize_parsed_config(copy.deepcopy(parsed)), indent=2, ensure_ascii=False),
        }
    return section


def _yaml_from_parsed(parsed: Any) -> str | None:
    if parsed is None:
        return None
    try:
        return yaml.dump(parsed, sort_keys=False, allow_unicode=True)
    except (TypeError, ValueError, yaml.YAMLError):
        return None


def _clash_yaml_from_parsed(parsed: Any) -> str | None:
    return _yaml_from_parsed(parsed)


def _attach_config_yaml(section: dict[str, Any]) -> dict[str, Any]:
    parsed = section.get("parsed")
    yaml_text = _yaml_from_parsed(parsed)
    if yaml_text:
        section = {**section, "config_yaml": yaml_text}
    if isinstance(section.get("configs"), list):
        section = {
            **section,
            "configs": [_attach_config_yaml(dict(item)) for item in section["configs"]],
        }
    return section


def _inject_client_fragment_blocks(base: str, fragment: str) -> tuple[str, bool]:
    return _inject_named_fragment_blocks(base, fragment, ("outbounds", "endpoints"))


def _rendered_client_block_body(items: list[dict]) -> str:
    if not items:
        return ""
    return ",\n".join(json.dumps(item, ensure_ascii=False) for item in items)


def _normalize_fragment_body(rendered: str) -> str:
    return (rendered or "").strip().rstrip(",")


def _template_has_client_blocks(template: str) -> bool:
    return "{% block outbounds %}" in template or "{% block endpoints %}" in template


def _build_client_block_fragment(
    outbound_template: str,
    *,
    outbound_items: list[dict] | None = None,
    endpoint_items: list[dict] | None = None,
    outbound_body: str | None = None,
    endpoint_body: str | None = None,
) -> str:
    if outbound_body is None and outbound_items is None and endpoint_body is None and endpoint_items is None and _template_has_client_blocks(outbound_template):
        return outbound_template

    parts: list[str] = []
    if outbound_body is not None:
        parts.append(f"{{% block outbounds %}}\n{outbound_body}\n{{% endblock %}}")
    elif outbound_items is not None:
        body = _rendered_client_block_body(outbound_items)
        parts.append(f"{{% block outbounds %}}\n{body}\n{{% endblock %}}")
    else:
        extracted_outbound = _extract_block_body(outbound_template, "outbounds")
        if extracted_outbound is not None:
            parts.append(f"{{% block outbounds %}}\n{extracted_outbound}\n{{% endblock %}}")
        elif outbound_template.strip() and "{% block outbounds %}" not in outbound_template:
            body = _fragment_block_body(outbound_template, "outbounds")
            if body.strip():
                parts.append(f"{{% block outbounds %}}\n{body}\n{{% endblock %}}")

    if endpoint_body is not None:
        parts.append(f"{{% block endpoints %}}\n{endpoint_body}\n{{% endblock %}}")
    elif endpoint_items is not None:
        body = _rendered_client_block_body(endpoint_items)
        parts.append(f"{{% block endpoints %}}\n{body}\n{{% endblock %}}")
    else:
        extracted_endpoint = _extract_block_body(outbound_template, "endpoints")
        if extracted_endpoint is not None:
            parts.append(f"{{% block endpoints %}}\n{extracted_endpoint}\n{{% endblock %}}")

    if parts:
        return "\n".join(parts)
    return outbound_template


def _compose_singbox_client_config(
    child_id: int,
    context: dict[str, Any],
    *,
    core: str,
    version: str,
    outbound_template: str,
    outbound_items: list[dict] | None = None,
    endpoint_items: list[dict] | None = None,
    outbound_body: str | None = None,
    endpoint_body: str | None = None,
    _coerce_depth: int = 0,
) -> dict[str, Any]:
    fragment = _build_client_block_fragment(
        outbound_template,
        outbound_items=outbound_items,
        endpoint_items=endpoint_items,
        outbound_body=outbound_body,
        endpoint_body=endpoint_body,
    )
    candidates: list[str] = []
    base = resolve_base_config_content(child_id, BaseConfigSide.client.value, core, version)
    base = _extract_block_body(base, "base_config") or base
    if _base_usable_for_compose(base):
        candidates.append(base)
    shell = _catalog_shell_base(BaseConfigSide.client.value, core)
    shell = _extract_block_body(shell, "base_config") or shell
    if _base_usable_for_compose(shell) and shell not in candidates:
        candidates.append(shell)
    section: dict[str, Any] | None = None
    for candidate in candidates:
        injected, ok = _inject_client_fragment_blocks(candidate, fragment)
        if ok:
            section = _render_section(injected, child_id, context, as_json_object=True)
            break
    if section is None:
        section = _compose_full_config(
            child_id,
            context,
            side=BaseConfigSide.client.value,
            core=core,
            version=version,
            fragment=fragment,
            block_name="outbounds",
        )
    if _coerce_depth > 0:
        return section
    return _coerce_singbox_style_config_section(
        section,
        child_id=child_id,
        context=context,
        core=core,
        version=version,
        side=BaseConfigSide.client.value,
        fragment_template=outbound_template,
    )


def _compose_server_config(
    child_id: int,
    context: dict[str, Any],
    *,
    core: str,
    version: str,
    inbound_template: str,
    _coerce_depth: int = 0,
) -> dict[str, Any]:
    block_name = _server_block_name(core)
    if not (inbound_template or "").strip():
        return _render_section("", child_id, context, as_json_object=True)

    candidates: list[str] = []
    base = resolve_base_config_content(child_id, BaseConfigSide.server.value, core, version)
    base = _extract_block_body(base, "base_config") or base
    if _base_usable_for_compose(base):
        candidates.append(base)
    shell = _catalog_shell_base(BaseConfigSide.server.value, core)
    shell = _extract_block_body(shell, "base_config") or shell
    if _base_usable_for_compose(shell) and shell not in candidates:
        candidates.append(shell)

    section: dict[str, Any] | None = None
    for candidate in candidates:
        injected, ok = _inject_named_fragment_blocks(candidate, inbound_template, (block_name,))
        if ok:
            section = _render_section(injected, child_id, context, as_json_object=True)
            break

    if section is None:
        section = _compose_full_config(
            child_id,
            context,
            side=BaseConfigSide.server.value,
            core=core,
            version=version,
            fragment=inbound_template,
            block_name=block_name,
        )
    if _coerce_depth > 0 or core != "hiddify-core":
        return section
    return _coerce_singbox_style_config_section(
        section,
        child_id=child_id,
        context=context,
        core=core,
        version=version,
        side=BaseConfigSide.server.value,
        fragment_template=inbound_template,
    )


def _domain_var_id(domain: Any) -> int | None:
    data = getattr(domain, "_data", None)
    if isinstance(data, dict):
        for key in ("id", "domain_id"):
            val = data.get(key)
            if val is not None:
                return int(val)
    raw = getattr(domain, "id", None)
    return int(raw) if raw is not None else None


def _domain_var_host(domain: Any) -> str:
    data = getattr(domain, "_data", None)
    if isinstance(data, dict):
        return str(data.get("name") or data.get("domain") or data.get("host") or "").strip().lower()
    return str(getattr(domain, "domain", None) or getattr(domain, "name", None) or "").strip().lower()


def _scope_example_context(
    ctx: dict[str, Any],
    *,
    proxy_id: int | None,
    domain_id: int | None,
    domain_host: str | None,
    server_side: bool,
) -> None:
    del proxy_id, server_side
    target = ctx.get("ctx") if isinstance(ctx.get("ctx"), object) and hasattr(ctx.get("ctx"), "get") else ctx
    if not hasattr(target, "get") and not isinstance(target, dict):
        return
    domains = target.get("domains") or []
    if not domains:
        return
    if domain_id is not None:
        scoped_domains = [item for item in domains if _domain_var_id(item) == int(domain_id)]
    elif (domain_host or "").strip():
        host = domain_host.strip().lower()
        scoped_domains = [item for item in domains if _domain_var_host(item) == host]
    else:
        return
    if scoped_domains:
        target["domains"] = scoped_domains
    else:
        fallback = target.get("domain")
        if fallback is not None:
            target["domains"] = [fallback]
    proxy = target.get("proxy")
    if proxy is not None and hasattr(proxy, "domains"):
        proxy.domains = list(target.get("domains") or [])


def _collect_client_fragment_bodies(
    child_id: int,
    data: dict[str, Any],
    tpl: str,
    *,
    core_name: str,
    proxy_id: int | None,
    domain_id: int | None,
    domain_host: str | None,
    ip: str | None,
    user_id: int | None,
    user_uuid: str | None,
    user_agent: str | None,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, str]],
    label: str,
) -> tuple[str, str, dict[str, Any] | None]:
    block_name = _client_block_name(core_name)
    outbound_parts: list[str] = []
    endpoint_parts: list[str] = []
    last_error_section: dict[str, Any] | None = None
    proxy_label = data.get("name") or data.get("slug") or str(proxy_id or "")
    variants = [_ClientRenderVariant(alpn_tag="", download_alpn_tag=None)] if _client_uses_template_alpn_loop(core_name) else _client_render_variants(data)
    for variant in variants:
        alpn_ctx = _build_proxy_context(
            child_id,
            data,
            domain_id=domain_id,
            domain_host=domain_host,
            ip=ip,
            user_id=user_id,
            user_uuid=user_uuid,
            user_agent=user_agent,
            server_side=False,
            proxy_id=proxy_id,
            **_variant_context_kwargs(variant),
        )
        alpn_ctx["client_core"] = core_name
        frag = _render_fragment_section(child_id, alpn_ctx, tpl, block_name, parse_json=False)
        alpn_label = _variant_label(variant)
        full_label = f"{proxy_label}/{alpn_label}" if proxy_label else alpn_label
        if frag.get("skipped"):
            warnings.append(
                {
                    "code": "client_skip",
                    "message": f"{full_label} ({label}): skipped (SKIP)",
                }
            )
            continue
        if frag.get("error"):
            _append_render_issue(
                errors,
                code="client_render",
                message=f"{full_label} ({label}): {frag['error']}",
                section=frag,
                label=full_label,
            )
            last_error_section = frag
            continue
        body = _normalize_fragment_body(frag.get("rendered") or "")
        if not body:
            continue
        from hiddifypanel.proxy_v3.config_builder.render import _resolve_fragment_block_name

        resolved_block = _resolve_fragment_block_name(tpl, block_name)
        if resolved_block == "endpoints":
            endpoint_parts.append(body)
        else:
            outbound_parts.append(body)
    outbound_body = ",\n".join(outbound_parts)
    endpoint_body = ",\n".join(endpoint_parts)
    return outbound_body, endpoint_body, last_error_section


def _collect_client_fragment_items(
    child_id: int,
    data: dict[str, Any],
    tpl: str,
    *,
    core_name: str,
    proxy_id: int | None,
    domain_id: int | None,
    domain_host: str | None,
    ip: str | None,
    user_id: int | None,
    user_uuid: str | None,
    user_agent: str | None,
    ua_parsed: dict,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, str]],
    label: str,
) -> tuple[list[dict], list[dict], dict[str, Any] | None]:
    block_name = _client_block_name(core_name)
    outbound_items: list[dict] = []
    endpoint_items: list[dict] = []
    last_error_section: dict[str, Any] | None = None
    proxy_label = data.get("name") or data.get("slug") or str(proxy_id or "")
    for variant in _client_render_variants(data):
        alpn_ctx = _build_proxy_context(
            child_id,
            data,
            domain_id=domain_id,
            domain_host=domain_host,
            ip=ip,
            user_id=user_id,
            user_uuid=user_uuid,
            user_agent=user_agent,
            server_side=False,
            proxy_id=proxy_id,
            **_variant_context_kwargs(variant),
        )
        alpn_ctx["client_core"] = core_name
        frag = _render_fragment_section(child_id, alpn_ctx, tpl, block_name)
        alpn_label = _variant_label(variant)
        full_label = f"{proxy_label}/{alpn_label}" if proxy_label else alpn_label
        if frag.get("skipped"):
            warnings.append(
                {
                    "code": "client_skip",
                    "message": f"{full_label} ({label}): skipped (SKIP)",
                }
            )
            continue
        if frag.get("error"):
            _append_render_issue(
                errors,
                code="client_render",
                message=f"{full_label} ({label}): {frag['error']}",
                section=frag,
                label=full_label,
            )
            last_error_section = frag
            continue
        items_list = _parsed_to_items(frag.get("parsed"))
        ob, ep = _partition_client_fragments(items_list, ua_parsed)
        outbound_items.extend(ob)
        endpoint_items.extend(ep)
    return outbound_items, endpoint_items, last_error_section


def _render_singbox_style_client_for_proxy(
    child_id: int,
    client_ctx: dict[str, Any],
    data: dict[str, Any],
    tpl: str,
    *,
    core_name: str,
    version: str,
    proxy_id: int | None,
    domain_id: int | None,
    domain_host: str | None,
    ip: str | None,
    user_id: int | None,
    user_uuid: str | None,
    user_agent: str | None,
    ua_parsed: dict,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, str]],
    label: str,
) -> dict[str, Any]:
    outbound_body, endpoint_body, last_error = _collect_client_fragment_bodies(
        child_id,
        data,
        tpl,
        core_name=core_name,
        proxy_id=proxy_id,
        domain_id=domain_id,
        domain_host=domain_host,
        ip=ip,
        user_id=user_id,
        user_uuid=user_uuid,
        user_agent=user_agent,
        errors=errors,
        warnings=warnings,
        label=label,
    )
    if last_error and not outbound_body and not endpoint_body and not tpl.strip():
        return last_error
    section = _compose_singbox_client_config(
        child_id,
        client_ctx,
        core=core_name,
        version=version,
        outbound_template=tpl,
        outbound_body=outbound_body if outbound_body else None,
        endpoint_body=endpoint_body if endpoint_body else None,
    )
    if section.get("error") and last_error and not section.get("parsed"):
        return last_error
    return section


def _catalog_shell_base(side: str, core: str) -> str:
    from hiddifypanel.proxy_v3.template_catalog.base_configs import load_base_config_file

    file_core = "hiddify-core" if core in ("hiddify-core", "singbox") else core
    try:
        return load_base_config_file(file_core, side)
    except FileNotFoundError:
        return default_base_content(side, core)


def _merge_rendered_sections(base_section: dict[str, Any], frag_section: dict[str, Any], block_name: str | None) -> dict[str, Any]:
    if frag_section.get("skipped"):
        return base_section
    if frag_section.get("error"):
        return _ensure_section_error_detail(
            {
                **base_section,
                "error": frag_section.get("error"),
                "error_detail": frag_section.get("error_detail"),
                "rendered": frag_section.get("rendered") or base_section.get("rendered"),
            }
        )
    base_parsed = base_section.get("parsed")
    frag_parsed = frag_section.get("parsed")
    if not isinstance(base_parsed, dict):
        return frag_section if frag_parsed is not None else base_section

    merged = copy.deepcopy(base_parsed)
    if block_name == "inbound" or block_name == "inbounds":
        key = "inbounds"
        if isinstance(frag_parsed, list):
            items = frag_parsed
        elif isinstance(frag_parsed, dict):
            items = [frag_parsed]
        else:
            items = []
        merged[key] = items + list(merged.get(key) or [])
    elif block_name in ("outbound", "outbounds", None):
        key = "outbounds"
        if isinstance(frag_parsed, list):
            items = frag_parsed
        elif isinstance(frag_parsed, dict):
            if "proxies" in frag_parsed:
                return {
                    "rendered": json.dumps(frag_parsed, indent=2, ensure_ascii=False),
                    "parsed": frag_parsed,
                    "skipped": False,
                    "error": None,
                }
            items = [frag_parsed]
        else:
            items = []
        merged[key] = items + list(merged.get(key) or [])
    elif block_name == "endpoints":
        key = "endpoints"
        if isinstance(frag_parsed, list):
            items = frag_parsed
        elif isinstance(frag_parsed, dict):
            items = [frag_parsed]
        else:
            items = []
        merged[key] = items + list(merged.get(key) or [])
    else:
        return frag_section

    rendered = json.dumps(merged, indent=2, ensure_ascii=False)
    return {
        "rendered": rendered,
        "parsed": merged,
        "skipped": False,
        "error": None,
    }


def _base_usable_for_compose(base: str) -> bool:
    stripped = (base or "").strip()
    return bool(stripped) and stripped != "{}"


def _resolve_client_base_shell(
    child_id: int,
    side: str,
    core: str,
    version: str,
    cc: dict[str, Any],
) -> str:
    base = resolve_base_config_content(child_id, side, core, version)
    return _extract_block_body(base, "base_config") or base


def _compose_full_config(
    child_id: int,
    context: dict[str, Any],
    *,
    side: str,
    core: str,
    version: str,
    fragment: str,
    block_name: str | None,
    as_json_object: bool = True,
    base_template: str | None = None,
) -> dict[str, Any]:
    if not (fragment or "").strip():
        return _render_section("", child_id, context, as_json_object=as_json_object)

    if not block_name:
        return _render_section(fragment, child_id, context, as_json_object=as_json_object)

    if base_template is not None:
        base = base_template
    else:
        base = resolve_base_config_content(child_id, side, core, version)
        base = _extract_block_body(base, "base_config") or base
    if block_name and _base_usable_for_compose(base):
        side_val = side.value if hasattr(side, "value") else side
        if side_val == BaseConfigSide.client.value and core in ("hiddify-core", "singbox"):
            injected, ok = _inject_client_fragment_blocks(base, fragment)
        else:
            injected, ok = _inject_named_fragment_blocks(base, fragment, (block_name,))
        if ok:
            return _render_section(injected, child_id, context, as_json_object=as_json_object)

    shell = _catalog_shell_base(side, core)
    shell = _extract_block_body(shell, "base_config") or shell
    if block_name and _base_usable_for_compose(shell):
        side_val = side.value if hasattr(side, "value") else side
        if side_val == BaseConfigSide.client.value and core in ("hiddify-core", "singbox"):
            injected, ok = _inject_client_fragment_blocks(shell, fragment)
        else:
            injected, ok = _inject_named_fragment_blocks(shell, fragment, (block_name,))
        if ok:
            return _render_section(injected, child_id, context, as_json_object=as_json_object)

    if not _base_usable_for_compose(base):
        return _render_section(fragment, child_id, context, as_json_object=as_json_object)

    base_section = _render_section(base, child_id, context, as_json_object=True)
    if base_section.get("skipped"):
        return base_section

    frag_section = _render_fragment_section(child_id, context, fragment, block_name)
    return _merge_rendered_sections(base_section, frag_section, block_name)


def _xray_config_remarks(parsed: Any) -> str | None:
    if not isinstance(parsed, dict):
        return None
    outbounds = parsed.get("outbounds") or []
    for item in outbounds:
        if isinstance(item, dict):
            tag = item.get("tag")
            if tag and tag not in _BUILTIN_OUTBOUND_TAGS:
                return str(tag)
    return None


def _apply_xray_config_remarks(section: dict[str, Any]) -> dict[str, Any]:
    parsed = section.get("parsed")
    if not isinstance(parsed, dict):
        return section
    remarks = _xray_config_remarks(parsed)
    if remarks:
        parsed = copy.deepcopy(parsed)
        parsed["remarks"] = remarks
        section = {
            **section,
            "parsed": parsed,
            "rendered": json.dumps(parsed, indent=2, ensure_ascii=False),
        }
    return section


def _compose_xray_client_configs_for_proxy(
    child_id: int,
    data: dict[str, Any],
    cc: dict[str, Any],
    *,
    proxy_id: int,
    domain_id: int | None,
    domain_host: str | None,
    ip: str | None,
    user_id: int | None,
    user_uuid: str | None,
    user_agent: str | None,
) -> list[dict[str, Any]]:
    tpl = (cc.get("outbounds_template") or "").strip()
    if not tpl:
        return []
    version = cc.get("version") or ""
    base_shell = _resolve_client_base_shell(
        child_id,
        BaseConfigSide.client.value,
        "xray",
        version,
        cc,
    )
    block_name = _client_block_name("xray")
    proxy_label = data.get("name") or data.get("slug") or str(proxy_id)
    sections: list[dict[str, Any]] = []
    for variant in _client_render_variants(data):
        ctx = _build_proxy_context(
            child_id,
            data,
            domain_id=domain_id,
            domain_host=domain_host,
            ip=ip,
            user_id=user_id,
            user_uuid=user_uuid,
            user_agent=user_agent,
            server_side=False,
            proxy_id=proxy_id,
            **_variant_context_kwargs(variant),
        )
        section = _compose_full_config(
            child_id,
            ctx,
            side=BaseConfigSide.client.value,
            core="xray",
            version=version,
            fragment=tpl,
            block_name=block_name,
            base_template=base_shell,
        )
        section = _apply_xray_config_remarks(section)
        var_label = _variant_label(variant)
        section["variant_label"] = f"{proxy_label}/{var_label}"
        sections.append(section)
    return sections


def _xray_client_entry_from_sections(
    sections: list[dict[str, Any]],
    *,
    core: str,
    version: str | None,
    label: str,
    index: int | None,
    auto: bool = False,
) -> dict[str, Any]:
    if not sections:
        return {
            "core": core,
            "version": version,
            "label": label,
            "index": index,
            "auto": auto,
            "configs": [],
            "rendered": "",
            "parsed": None,
            "skipped": False,
            "error": None,
        }
    first = sections[0]
    return {
        "core": core,
        "version": version,
        "label": label,
        "index": index,
        "auto": auto,
        "configs": sections,
        "rendered": first.get("rendered") or "",
        "parsed": first.get("parsed") if len(sections) == 1 else None,
        "skipped": all(bool(s.get("skipped")) for s in sections),
        "error": next((s.get("error") for s in sections if s.get("error")), None),
        "error_detail": next((s.get("error_detail") for s in sections if s.get("error_detail")), None),
    }


def _normalize_sublink_base(base: str) -> str:
    text = base or ""
    if "{{ links }}" in text or "{{links}}" in text:
        return text
    return re.sub(
        r"\{%\s*block\s+links\s*%\}.*?\{%\s*endblock\s*%\}",
        "{{ links }}",
        text,
        flags=re.DOTALL,
    )


def _sublink_base_uses_links_var(base: str) -> bool:
    text = _normalize_sublink_base(base)
    return "{{ links }}" in text or "{{links}}" in text


def _compose_sublink_full_config(
    child_id: int,
    context: dict[str, Any],
    *,
    version: str,
    outbounds_template: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    link_section = _render_section(outbounds_template, child_id, context, as_json_object=False)
    if link_section.get("rendered"):
        link_section = {
            **link_section,
            "rendered": _strip_empty_link_lines(link_section["rendered"]),
        }
    formats = build_sublink_formats(link_section.get("rendered") or "")
    if link_section.get("skipped") or link_section.get("error"):
        return link_section, formats

    link_value = link_section.get("rendered") or ""
    base = _normalize_sublink_base(
        resolve_base_config_content(child_id, BaseConfigSide.client.value, "sublink", version)
    )
    if _base_usable_for_compose(base) and link_value:
        if _sublink_base_uses_links_var(base):
            compose_ctx = {**context, "links": link_value}
            full_section = _render_section(base, child_id, compose_ctx, as_json_object=False)
            if full_section.get("rendered"):
                full_section = {
                    **full_section,
                    "rendered": _strip_empty_link_lines(full_section["rendered"]),
                }
        elif '"links": []' in base:
            link_json = json.dumps(link_value, ensure_ascii=False)
            template = base.replace('"links": []', f'"links": [{link_json}]', 1)
            full_section = _render_section(template, child_id, context, as_json_object=True)
        else:
            full_section = {
                "rendered": link_value,
                "parsed": {"links": [link_value]} if link_value else None,
                "skipped": False,
                "error": None,
            }
    else:
        full_section = {
            "rendered": link_value,
            "parsed": {"links": [link_value]} if link_value else None,
            "skipped": False,
            "error": None,
        }
        if link_value:
            parsed, parse_err = parse_json5(json.dumps(full_section["parsed"]))
            if parse_err:
                full_section["error"] = parse_err
                full_section["error_detail"] = _render_error_detail(
                    parse_err,
                    source=full_section.get("rendered") or link_value,
                    phase="json5",
                )
            else:
                full_section["parsed"] = parsed
                full_section["rendered"] = json.dumps(parsed, indent=2, ensure_ascii=False)

    return full_section, formats


def _render_section(template_text: str, child_id: int, context: dict[str, Any], *, as_json_object: bool = True, parse_json: bool = True) -> dict[str, Any]:
    return _ensure_section_error_detail(
        _render_section_impl(
            template_text,
            child_id,
            context,
            as_json_object=as_json_object,
            parse_json=parse_json,
        ).model_dump()
    )


def _render_fragment_section(child_id: int, context: dict[str, Any], fragment: str, block_name: str | None, *, parse_json: bool = True) -> dict[str, Any]:
    return _ensure_section_error_detail(
        _render_fragment_section_impl(
            child_id,
            context,
            fragment,
            block_name,
            parse_json=parse_json,
        ).model_dump()
    )


def generate_proxy_example(
    proxy_id: int,
    child_id: int = 0,
    *,
    domain: str | None = None,
    domain_id: int | None = None,
    user_id: int | None = None,
    user_uuid: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    ignore_skip: bool = True,
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    proxy = CustomProxy.query.filter(CustomProxy.id == proxy_id, CustomProxy.child_id == child_id).first()
    if not proxy:
        return {
            "ok": False,
            "errors": [{"code": "not_found", "message": "Custom proxy not found"}],
            "warnings": [],
            "context": {},
            "server": None,
            "clients": [],
        }

    data = proxy.to_dict()
    server_config = data.get("server_config") or {}
    client_config = data.get("client_config") or {}
    tag = server_config.get("tag") or data.get("slug") or "example-tag"
    protocol = _proxy_mode_value(data)
    stored_tcp = normalize_port_list(server_config.get("inbound_tcp_ports") or server_config.get("inbound_port"))
    stored_udp = normalize_port_list(server_config.get("inbound_udp_ports"))
    client_ports = resolve_inbound_ports(
        protocol,
        proxy_id,
        domain_id=domain_id,
        db_tcp_ports=stored_tcp,
        db_udp_ports=stored_udp,
        server_side=False,
        tls_layer=data.get("tls_layer"),
    )
    server_ports = resolve_inbound_ports(
        protocol,
        proxy_id,
        domain_id=domain_id,
        db_tcp_ports=stored_tcp,
        db_udp_ports=stored_udp,
        server_side=True,
        tls_layer=data.get("tls_layer"),
    )
    client_port = primary_resolved_port(client_ports)
    server_port = primary_resolved_port(server_ports)
    core = server_config.get("core") or "xray"
    binding = "ip" if protocol == CustomProxyMode.ip.value else "domain"
    resolved_ip = (ip or "").strip() or "203.0.113.1"
    resolved_ua = (user_agent or "").strip() or EXAMPLE_USER_AGENTS[1]["value"]
    ua_parsed = parse_user_agent(resolved_ua)
    user, _users = build_user_context(user_id=user_id, user_uuid=user_uuid)
    domain_data = build_domain_context(
        child_id,
        domain_id=domain_id,
        domain_host=domain,
        server_ip=resolved_ip,
        skip_network_lookup=True,
    )

    server_domain_id = domain_id
    server_domain_host = domain
    if protocol == CustomProxyMode.domains_l7_gateway.value:
        server_domain_id = None
        server_domain_host = None

    ctx_server = build_render_context(
        child_id,
        data,
        ip=resolved_ip,
        domain_id=server_domain_id,
        domain_host=server_domain_host,
        user_id=user_id,
        user_uuid=user_uuid,
        user_agent=resolved_ua,
        server_side=True,
        skip_network_lookup=True,
        proxy_id=proxy_id,
        core=core,
    )
    ctx_client = build_render_context(
        child_id,
        data,
        ip=resolved_ip,
        domain_id=domain_id,
        domain_host=domain,
        user_id=user_id,
        user_uuid=user_uuid,
        user_agent=resolved_ua,
        server_side=False,
        skip_network_lookup=True,
        proxy_id=proxy_id,
    )
    if ignore_skip:
        ctx_server["ignore_skip"] = True
        ctx_client["ignore_skip"] = True

    _scope_example_context(
        ctx_server,
        proxy_id=proxy_id,
        domain_id=server_domain_id,
        domain_host=server_domain_host,
        server_side=True,
    )
    _scope_example_context(
        ctx_client,
        proxy_id=proxy_id,
        domain_id=domain_id,
        domain_host=domain,
        server_side=False,
    )

    auto_client_cores = resolve_auto_client_cores(resolved_ua, ua_parsed, child_id)
    core_configs = [
        cc
        for cc in (client_config.get("core_configs") or [])
        if _keep_common_proxy_client_core(data, str(cc.get("core") or ""), child_id)
    ]
    configured_cores = [str(cc.get("core") or "").strip() for cc in core_configs if str(cc.get("core") or "").strip()]
    primary_auto = resolve_primary_auto_client_core(resolved_ua, ua_parsed, child_id, configured_cores)
    default_client_core = resolve_default_client_core(configured_cores, child_id)

    def _client_is_auto(core_name: str) -> bool:
        return bool(primary_auto and core_name == primary_auto)

    server_result: dict[str, Any] | None = None
    inbound_template = server_config.get("inbound_template") or ""
    if inbound_template.strip():
        section = _compose_server_config(
            child_id,
            ctx_server,
            core=core,
            version="",
            inbound_template=inbound_template,
        )
        server_result = _attach_config_yaml(
            {
                "core": core,
                "version": None,
                "label": core,
                "index": None,
                **section,
            }
        )
        if section.get("error"):
            _append_render_issue(
                errors,
                code="server_render",
                message=section["error"],
                section=section,
                label=core,
            )
        elif section.get("skipped"):
            warnings.append({"code": "server_skip", "message": "Server template skipped (SKIP)"})

    clients: list[dict[str, Any]] = []
    for idx, cc in enumerate(core_configs):
        core_name = cc.get("core") or ""
        version = cc.get("version") or ""
        label = _client_core_label(core_name, version)
        client_ctx = dict(ctx_client)
        client_ctx["client_core"] = core_name
        if core_name == "sublink":
            tpl = _client_outbounds_template(cc)
            section, formats = _compose_sublink_full_config(
                child_id,
                client_ctx,
                version=version,
                outbounds_template=tpl,
            )
            entry = {
                "core": core_name,
                "version": version or None,
                "label": label,
                "index": idx,
                "auto": _client_is_auto(core_name),
                **section,
                "sublink_formats": formats,
                "rendered": section.get("rendered") or formats.get("raw") or "",
            }
            clients.append(entry)
            if section.get("error"):
                _append_render_issue(
                    errors,
                    code="client_render",
                    message=f"{label}: {section['error']}",
                    section=section,
                    label=label,
                )
            elif formats.get("parse_error"):
                warnings.append({"code": "sublink_parse", "message": f"{label}: {formats['parse_error']}"})
            continue
        if core_name == "clash":
            tpl = cc.get("outbounds_template") or ""
            if not tpl.strip():
                clients.append(
                    {
                        "core": core_name,
                        "version": version or None,
                        "label": label,
                        "index": idx,
                        "auto": _client_is_auto(core_name),
                        "rendered": "",
                        "parsed": None,
                        "skipped": False,
                        "error": None,
                    }
                )
                continue
            section = _compose_full_config(
                child_id,
                client_ctx,
                side=BaseConfigSide.client.value,
                core=core_name,
                version=version,
                fragment=tpl,
                block_name=None,
            )
            entry = {
                "core": core_name,
                "version": version or None,
                "label": label,
                "index": idx,
                "auto": _client_is_auto(core_name),
                **section,
            }
            entry["clash_yaml"] = _clash_yaml_from_parsed(section.get("parsed"))
            clients.append(entry)
            if section.get("error"):
                _append_render_issue(
                    errors,
                    code="client_render",
                    message=f"{label}: {section['error']}",
                    section=section,
                    label=label,
                )
            elif section.get("skipped"):
                warnings.append({"code": "client_skip", "message": f"{label}: skipped (SKIP)"})
            continue
        tpl = cc.get("outbounds_template") or ""
        if not tpl.strip():
            clients.append(
                {
                    "core": core_name,
                    "version": version or None,
                    "label": label,
                    "index": idx,
                    "rendered": "",
                    "parsed": None,
                    "skipped": False,
                    "error": None,
                }
            )
            continue
        if core_name == "xray":
            xray_sections = _compose_xray_client_configs_for_proxy(
                child_id,
                data,
                cc,
                proxy_id=proxy_id,
                domain_id=domain_id,
                domain_host=domain,
                ip=resolved_ip,
                user_id=user_id,
                user_uuid=user_uuid,
                user_agent=resolved_ua,
            )
            entry = _xray_client_entry_from_sections(
                xray_sections,
                core=core_name,
                version=version or None,
                label=label,
                index=idx,
                auto=_client_is_auto(core_name),
            )
            clients.append(entry)
            for section in xray_sections:
                var_label = section.get("variant_label") or label
                if section.get("error"):
                    _append_render_issue(
                        errors,
                        code="client_render",
                        message=f"{var_label} ({label}): {section['error']}",
                        section=section,
                        label=var_label,
                    )
                elif section.get("skipped"):
                    warnings.append({"code": "client_skip", "message": f"{var_label} ({label}): skipped (SKIP)"})
            continue
        block_name = _client_block_name(core_name)
        if core_name in ("hiddify-core", "singbox"):
            section = _render_singbox_style_client_for_proxy(
                child_id,
                client_ctx,
                data,
                tpl,
                core_name=core_name,
                version=version,
                proxy_id=proxy_id,
                domain_id=domain_id,
                domain_host=domain,
                ip=resolved_ip,
                user_id=user_id,
                user_uuid=user_uuid,
                user_agent=resolved_ua,
                ua_parsed=ua_parsed,
                errors=errors,
                warnings=warnings,
                label=label,
            )
        else:
            merged_section = _render_base_section(
                child_id,
                client_ctx,
                BaseConfigSide.client.value,
                core_name,
                version,
            )
            parsed = merged_section.get("parsed")
            if isinstance(parsed, dict):
                merged = copy.deepcopy(parsed)
                proxy_label = data.get("name") or data.get("slug") or str(proxy_id)
                for variant in _client_render_variants(data):
                    alpn_ctx = _build_proxy_context(
                        child_id,
                        data,
                        domain_id=domain_id,
                        domain_host=domain,
                        ip=resolved_ip,
                        user_id=user_id,
                        user_uuid=user_uuid,
                        user_agent=resolved_ua,
                        server_side=False,
                        proxy_id=proxy_id,
                        **_variant_context_kwargs(variant),
                    )
                    alpn_ctx["client_core"] = core_name
                    frag = _render_fragment_section(child_id, alpn_ctx, tpl, block_name)
                    alpn_label = _variant_label(variant)
                    if frag.get("skipped"):
                        warnings.append(
                            {
                                "code": "client_skip",
                                "message": f"{proxy_label}/{alpn_label} ({label}): skipped (SKIP)",
                            }
                        )
                        continue
                    if frag.get("error"):
                        _append_render_issue(
                            errors,
                            code="client_render",
                            message=f"{proxy_label}/{alpn_label} ({label}): {frag['error']}",
                            section=frag,
                            label=f"{proxy_label}/{alpn_label}",
                        )
                        continue
                    items_list = _parsed_to_items(frag.get("parsed"))
                    outbound_items, endpoint_items = _partition_client_fragments(items_list, ua_parsed)
                    _append_client_outbound_items(merged, outbound_items, endpoint_items)
                merged = _sanitize_parsed_config(merged)
                section = _section_from_parsed(merged, error=merged_section.get("error"))
            else:
                section = _compose_full_config(
                    child_id,
                    client_ctx,
                    side=BaseConfigSide.client.value,
                    core=core_name,
                    version=version,
                    fragment=tpl,
                    block_name=block_name,
                )
        section = _finalize_singbox_client_section(section, core_name, ua_parsed)
        entry = {
            "core": core_name,
            "version": version or None,
            "label": label,
            "index": idx,
            "auto": _client_is_auto(core_name),
            **section,
        }
        clients.append(entry)
        if section.get("error"):
            _append_render_issue(
                errors,
                code="client_render",
                message=f"{label}: {section['error']}",
                section=section,
                label=label,
            )
        elif section.get("skipped"):
            warnings.append({"code": "client_skip", "message": f"{label}: skipped (SKIP)"})

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "context": {
            "custom_proxy_id": proxy_id,
            "domain": domain_data.get("name") or domain,
            "user": user.get("name") or user.get("uuid"),
            "ip": resolved_ip,
            "user_agent": resolved_ua,
            "user_agent_parsed": ua_parsed,
            "tag": tag,
            "port": client_port,
            "server_port": server_port,
            "domain_binding": binding,
        },
        "server": server_result,
        "clients": [_attach_config_yaml(c) for c in clients],
        "auto_client_cores": [primary_auto] if primary_auto else [],
        "auto_client_core": primary_auto,
        "default_client_core": default_client_core,
    }


def _append_client_outbound_items(
    merged: dict[str, Any],
    outbound_items: list[dict],
    endpoint_items: list[dict],
) -> None:
    outbounds = list(merged.get("outbounds") or [])
    _, proxy_items, builtins = _split_outbounds(outbounds)
    proxy_items.extend(outbound_items)
    merged["outbounds"] = proxy_items + builtins
    if endpoint_items:
        merged["endpoints"] = list(merged.get("endpoints") or []) + endpoint_items


def _section_from_parsed(parsed: dict[str, Any] | None, *, error: str | None = None) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        return {
            "rendered": "",
            "parsed": None,
            "skipped": False,
            "error": error,
        }
    return _ensure_section_error_detail(
        {
            "rendered": json.dumps(parsed, indent=2, ensure_ascii=False),
            "parsed": parsed,
            "skipped": False,
            "error": error,
        }
    )


def _merge_server_bundle(
    child_id: int,
    core: str,
    proxies: list[CustomProxy],
    *,
    domain_id: int | None,
    domain_host: str | None,
    ip: str | None,
    user_id: int | None,
    user_uuid: str | None,
    user_agent: str | None,
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> dict[str, Any]:
    from hiddifypanel.models.proxy_base_config import BaseConfigSide
    from hiddifypanel.proxy_v3.config_builder.registry import get_config_builder_driver

    driver = get_config_builder_driver(core, BaseConfigSide.server)
    if driver is not None and hasattr(driver, "merge_bundle"):
        return driver.merge_bundle(
            child_id,
            proxies,
            domain_id=domain_id,
            domain_host=domain_host,
            ip=ip,
            user_id=user_id,
            user_uuid=user_uuid,
            user_agent=user_agent,
            errors=errors,
            warnings=warnings,
        )

    bundle_ctx = _build_bundle_context(
        child_id,
        domain_id=domain_id,
        domain_host=domain_host,
        ip=ip,
        user_id=user_id,
        user_uuid=user_uuid,
        user_agent=user_agent,
        server_side=True,
    )
    block_name = _server_block_name(core)
    merged_section = _render_base_section(
        child_id,
        bundle_ctx,
        BaseConfigSide.server.value,
        core,
    )
    if merged_section.get("error"):
        return {
            "core": core,
            "version": None,
            "label": core,
            "index": None,
            **merged_section,
        }

    for proxy in proxies:
        if not proxy.enable:
            continue
        if (proxy.server_core.value if proxy.server_core else "xray") != core:
            continue
        inbound_tpl = proxy.effective_server_config_text()
        if not inbound_tpl.strip():
            continue
        from hiddifypanel.proxy_v3.context_vars.builder.server_builder import build_proxy_jinja_context

        ctx = build_proxy_jinja_context(
            child_id,
            proxy,
            core=core,
            domain_id=domain_id if proxy.mode not in (CustomProxyMode.domains_l7_gateway, CustomProxyMode.domains_auto_public_ports) else None,
            domain_host=domain_host if proxy.mode not in (CustomProxyMode.domains_l7_gateway, CustomProxyMode.domains_auto_public_ports) else None,
            user_id=user_id,
            user_uuid=user_uuid,
        )
        frag = _render_fragment_section(child_id, ctx, inbound_tpl, block_name)
        proxy_label = proxy.name or proxy.slug or str(proxy.id)
        if frag.get("skipped"):
            warnings.append({"code": "server_skip", "message": f"{proxy_label}: server skipped (SKIP)"})
            continue
        if frag.get("error"):
            _append_render_issue(
                errors,
                code="server_render",
                message=f"{proxy_label}: {frag['error']}",
                section=frag,
                label=proxy_label,
            )
            continue
        merged_section = _merge_rendered_sections(merged_section, frag, block_name)

    return {
        "core": core,
        "version": None,
        "label": core,
        "index": None,
        **merged_section,
    }


def _merge_client_outbound_bundle(
    child_id: int,
    core: str,
    version: str,
    items: list[tuple[CustomProxy, dict[str, Any]]],
    *,
    domain_id: int | None,
    domain_host: str | None,
    ip: str | None,
    user_id: int | None,
    user_uuid: str | None,
    user_agent: str | None,
    ua_parsed: dict,
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> dict[str, Any]:
    label = f"{core}{f' ≥ {version}' if version else ''}"
    if core == "xray":
        sections: list[dict[str, Any]] = []
        for proxy, cc in items:
            data = proxy.to_dict()
            proxy_sections = _compose_xray_client_configs_for_proxy(
                child_id,
                data,
                cc,
                proxy_id=proxy.id,
                domain_id=domain_id,
                domain_host=domain_host,
                ip=ip,
                user_id=user_id,
                user_uuid=user_uuid,
                user_agent=user_agent,
            )
            for section in proxy_sections:
                var_label = section.get("variant_label") or label
                if section.get("error"):
                    _append_render_issue(
                        errors,
                        code="client_render",
                        message=f"{var_label} ({label}): {section['error']}",
                        section=section,
                        label=var_label,
                    )
                elif section.get("skipped"):
                    warnings.append({"code": "client_skip", "message": f"{var_label} ({label}): skipped (SKIP)"})
            sections.extend(proxy_sections)
        return _xray_client_entry_from_sections(
            sections,
            core=core,
            version=version or None,
            label=label,
            index=None,
        )

    bundle_ctx = _build_bundle_context(
        child_id,
        domain_id=domain_id,
        domain_host=domain_host,
        ip=ip,
        user_id=user_id,
        user_uuid=user_uuid,
        user_agent=user_agent,
    )
    if core in ("singbox", "hiddify-core"):
        all_outbound_parts: list[str] = []
        all_endpoint_parts: list[str] = []
        last_error: dict[str, Any] | None = None
        for proxy, cc in items:
            data = proxy.to_dict()
            tpl = cc.get("outbounds_template") or ""
            if not tpl.strip():
                continue
            outbound_body, endpoint_body, err_section = _collect_client_fragment_bodies(
                child_id,
                data,
                tpl,
                core_name=core,
                proxy_id=proxy.id,
                domain_id=domain_id,
                domain_host=domain_host,
                ip=ip,
                user_id=user_id,
                user_uuid=user_uuid,
                user_agent=user_agent,
                errors=errors,
                warnings=warnings,
                label=label,
            )
            if outbound_body:
                all_outbound_parts.append(outbound_body)
            if endpoint_body:
                all_endpoint_parts.append(endpoint_body)
            if err_section is not None:
                last_error = err_section
        outbound_body = ",\n".join(all_outbound_parts)
        endpoint_body = ",\n".join(all_endpoint_parts)
        if last_error and not outbound_body and not endpoint_body:
            return {
                "core": core,
                "version": version or None,
                "label": label,
                "index": None,
                **last_error,
            }
        section = _compose_singbox_client_config(
            child_id,
            bundle_ctx,
            core=core,
            version=version,
            outbound_template="",
            outbound_body=outbound_body if outbound_body else None,
            endpoint_body=endpoint_body if endpoint_body else None,
        )
        if section.get("error") and last_error and not section.get("parsed"):
            section = last_error
        section = _finalize_singbox_client_section(section, core, ua_parsed)
        return {
            "core": core,
            "version": version or None,
            "label": label,
            "index": None,
            **section,
        }

    block_name = _client_block_name(core)
    merged_section = _render_base_section(
        child_id,
        bundle_ctx,
        BaseConfigSide.client.value,
        core,
        version,
    )
    if merged_section.get("error"):
        return {
            "core": core,
            "version": version or None,
            "label": label,
            "index": None,
            **merged_section,
        }

    parsed = merged_section.get("parsed")
    if not isinstance(parsed, dict):
        return {
            "core": core,
            "version": version or None,
            "label": label,
            "index": None,
            **merged_section,
        }

    merged = copy.deepcopy(parsed)
    for proxy, cc in items:
        data = proxy.to_dict()
        tpl = cc.get("outbounds_template") or ""
        if not tpl.strip():
            continue
        proxy_label = data.get("name") or data.get("slug") or str(proxy.id)
        for variant in _client_render_variants(data):
            ctx = _build_proxy_context(
                child_id,
                data,
                domain_id=domain_id,
                domain_host=domain_host,
                ip=ip,
                user_id=user_id,
                user_uuid=user_uuid,
                user_agent=user_agent,
                server_side=False,
                proxy_id=proxy.id,
                **_variant_context_kwargs(variant),
            )
            frag = _render_fragment_section(child_id, ctx, tpl, block_name)
            alpn_label = f"{proxy_label}/{_variant_label(variant)}"
            if frag.get("skipped"):
                warnings.append({"code": "client_skip", "message": f"{alpn_label} ({label}): skipped (SKIP)"})
                continue
            if frag.get("error"):
                _append_render_issue(
                    errors,
                    code="client_render",
                    message=f"{alpn_label} ({label}): {frag['error']}",
                    section=frag,
                    label=alpn_label,
                )
                continue
            items_list = _parsed_to_items(frag.get("parsed"))
            outbound_items, endpoint_items = _partition_client_fragments(items_list, ua_parsed)
            _append_client_outbound_items(merged, outbound_items, endpoint_items)

    section = _section_from_parsed(_sanitize_parsed_config(merged), error=merged_section.get("error"))
    section = _finalize_singbox_client_section(section, core, ua_parsed)
    return {
        "core": core,
        "version": version or None,
        "label": label,
        "index": None,
        **section,
    }


def _merge_clash_bundle(
    child_id: int,
    version: str,
    items: list[tuple[CustomProxy, dict[str, Any]]],
    *,
    domain_id: int | None,
    domain_host: str | None,
    ip: str | None,
    user_id: int | None,
    user_uuid: str | None,
    user_agent: str | None,
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> dict[str, Any]:
    label = f"clash{f' ≥ {version}' if version else ''}"
    bundle_ctx = _build_bundle_context(
        child_id,
        domain_id=domain_id,
        domain_host=domain_host,
        ip=ip,
        user_id=user_id,
        user_uuid=user_uuid,
        user_agent=user_agent,
    )
    merged_section = _render_base_section(
        child_id,
        bundle_ctx,
        BaseConfigSide.client.value,
        "clash",
        version,
    )
    parsed = merged_section.get("parsed")
    if not isinstance(parsed, dict):
        return {
            "core": "clash",
            "version": version or None,
            "label": label,
            "index": None,
            **merged_section,
        }

    merged = copy.deepcopy(parsed)
    all_proxies = list(merged.get("proxies") or [])
    for proxy, cc in items:
        data = proxy.to_dict()
        tpl = cc.get("outbounds_template") or ""
        if not tpl.strip():
            continue
        for variant in _client_render_variants(data):
            ctx = _build_proxy_context(
                child_id,
                data,
                domain_id=domain_id,
                domain_host=domain_host,
                ip=ip,
                user_id=user_id,
                user_uuid=user_uuid,
                user_agent=user_agent,
                server_side=False,
                proxy_id=proxy.id,
                **_variant_context_kwargs(variant),
            )
            frag = _render_fragment_section(child_id, ctx, tpl, None)
            proxy_label = data.get("name") or data.get("slug") or str(proxy.id)
            if frag.get("skipped"):
                warnings.append(
                    {
                        "code": "client_skip",
                        "message": f"{proxy_label}/{_variant_label(variant)} ({label}): skipped (SKIP)",
                    }
                )
                continue
            if frag.get("error"):
                _append_render_issue(
                    errors,
                    code="client_render",
                    message=f"{proxy_label}/{_variant_label(variant)} ({label}): {frag['error']}",
                    section=frag,
                    label=f"{proxy_label}/{_variant_label(variant)}",
                )
                continue
            for item in _parsed_to_items(frag.get("parsed")):
                if isinstance(item, dict) and item.get("name") and not item.get("tag"):
                    item["tag"] = item["name"]
                all_proxies.append(item)

    all_proxies = deduplicate_client_tags(all_proxies, tag_key="name")
    for item in all_proxies:
        if isinstance(item, dict) and item.get("tag") and not item.get("name"):
            item["name"] = item["tag"]

    merged["proxies"] = all_proxies
    section = _section_from_parsed(merged)
    return {
        "core": "clash",
        "version": version or None,
        "label": label,
        "index": None,
        **section,
        "clash_yaml": _clash_yaml_from_parsed(merged),
    }


def _merge_sublink_bundle(
    child_id: int,
    version: str,
    items: list[tuple[CustomProxy, dict[str, Any]]],
    *,
    domain_id: int | None,
    domain_host: str | None,
    ip: str | None,
    user_id: int | None,
    user_uuid: str | None,
    user_agent: str | None,
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> dict[str, Any]:
    label = f"sublink{f' ≥ {version}' if version else ''}"
    links: list[str] = []
    for proxy, cc in items:
        data = proxy.to_dict()
        tpl = _client_outbounds_template(cc)
        if not tpl.strip():
            continue
        ctx = _build_proxy_context(
            child_id,
            data,
            domain_id=domain_id,
            domain_host=domain_host,
            ip=ip,
            user_id=user_id,
            user_uuid=user_uuid,
            user_agent=user_agent,
            server_side=False,
        )
        link_section = _render_section(tpl, child_id, ctx, as_json_object=False)
        proxy_label = data.get("name") or data.get("slug") or str(proxy.id)
        if link_section.get("skipped"):
            warnings.append({"code": "client_skip", "message": f"{proxy_label} ({label}): skipped (SKIP)"})
            continue
        if link_section.get("error"):
            _append_render_issue(
                errors,
                code="client_render",
                message=f"{proxy_label} ({label}): {link_section['error']}",
                section=link_section,
                label=f"{proxy_label} ({label})",
            )
            continue
        link_val = (link_section.get("rendered") or "").strip()
        if link_val:
            links.append(link_val.strip('"'))

    if not links:
        return {
            "core": "sublink",
            "version": version or None,
            "label": label,
            "index": None,
            "rendered": "",
            "parsed": None,
            "skipped": False,
            "error": None,
            "sublink_formats": build_sublink_formats(""),
        }

    bundle_ctx = _build_bundle_context(
        child_id,
        domain_id=domain_id,
        domain_host=domain_host,
        ip=ip,
        user_id=user_id,
        user_uuid=user_uuid,
        user_agent=user_agent,
    )
    base = _normalize_sublink_base(
        resolve_base_config_content(child_id, BaseConfigSide.client.value, "sublink", version)
    )
    links_text = "\n".join(links)
    if _base_usable_for_compose(base) and _sublink_base_uses_links_var(base):
        compose_ctx = {**bundle_ctx, "links": links_text}
        section = _render_section(base, child_id, compose_ctx, as_json_object=False)
        if section.get("rendered"):
            section = {
                **section,
                "rendered": _strip_empty_link_lines(section["rendered"]),
            }
    elif _base_usable_for_compose(base) and '"links": []' in base:
        links_json = ", ".join(json.dumps(link, ensure_ascii=False) for link in links)
        template = base.replace('"links": []', f'"links": [{links_json}]', 1)
        section = _render_section(template, child_id, bundle_ctx, as_json_object=True)
    else:
        template = '{\n  "links": [' + ", ".join(json.dumps(link, ensure_ascii=False) for link in links) + "]\n}"
        section = _render_section(template, child_id, bundle_ctx, as_json_object=True)
    formats = build_sublink_formats(links[0])
    return {
        "core": "sublink",
        "version": version or None,
        "label": label,
        "index": None,
        **section,
        "sublink_formats": formats,
        "rendered": section.get("rendered") or formats.get("raw") or "",
    }


def _resolve_bundle_domain_targets(
    child_id: int,
    *,
    domain: str | None = None,
    domain_id: int | None = None,
    domains: list[str] | None = None,
    domain_ids: list[int] | None = None,
) -> list[tuple[int | None, str | None]]:
    from hiddifypanel.models import Domain

    targets: list[tuple[int | None, str | None]] = []
    seen: set[tuple[int | None, str | None]] = set()

    def _add(did: int | None, dhost: str | None) -> None:
        host = (dhost or "").strip() or None
        host_key = host.lower() if host else None
        key = (did, host_key)
        if key in seen:
            return
        seen.add(key)
        targets.append((did, host))

    if domain_ids:
        for raw_id in domain_ids:
            if raw_id is None:
                continue
            did = int(raw_id)
            row = Domain.query.filter(Domain.id == did, Domain.child_id == child_id).first()
            _add(did, row.domain if row else None)
        if targets:
            return targets

    if domains:
        for raw_host in domains:
            host = (raw_host or "").strip()
            if not host:
                continue
            row = Domain.query.filter(Domain.child_id == child_id, Domain.domain == host).first()
            _add(row.id if row else None, host)
        if targets:
            return targets

    if domain_id is not None or (domain or "").strip():
        if domain_id is not None:
            row = Domain.query.filter(Domain.id == domain_id, Domain.child_id == child_id).first()
            _add(domain_id, row.domain if row else domain)
        else:
            host = (domain or "").strip()
            row = Domain.query.filter(Domain.child_id == child_id, Domain.domain == host).first()
            _add(row.id if row else None, host)
        return targets

    return [(None, None)]


def _merge_parsed_array_configs(
    base: dict[str, Any],
    extra: dict[str, Any],
    array_keys: tuple[str, ...],
) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    base_parsed = merged.get("parsed")
    extra_parsed = extra.get("parsed")
    if not isinstance(base_parsed, dict) or not isinstance(extra_parsed, dict):
        if extra.get("error") and not merged.get("error"):
            merged["error"] = extra.get("error")
        return merged
    for key in array_keys:
        if key in base_parsed or key in extra_parsed:
            base_parsed[key] = list(base_parsed.get(key) or []) + list(extra_parsed.get(key) or [])
    merged["parsed"] = base_parsed
    merged["rendered"] = json.dumps(base_parsed, indent=2, ensure_ascii=False)
    merged["skipped"] = bool(merged.get("skipped")) and bool(extra.get("skipped"))
    if extra.get("error") and not merged.get("error"):
        merged["error"] = extra.get("error")
        merged["error_detail"] = extra.get("error_detail")
    return merged


def _collect_sublink_links(entry: dict[str, Any]) -> list[str]:
    links: list[str] = []
    parsed = entry.get("parsed")
    if isinstance(parsed, dict) and isinstance(parsed.get("links"), list):
        for item in parsed["links"]:
            text = str(item).strip().strip('"')
            if text:
                links.append(text)
    if links:
        return links
    rendered = (entry.get("rendered") or "").strip()
    if not rendered:
        return links
    if rendered.startswith("{"):
        try:
            payload = json.loads(rendered)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict) and isinstance(payload.get("links"), list):
            return [str(item).strip().strip('"') for item in payload["links"] if str(item).strip()]
    return [line.strip() for line in rendered.splitlines() if line.strip() and "://" in line]


def _merge_sublink_client_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    base = copy.deepcopy(entries[0])
    links: list[str] = []
    for entry in entries:
        links.extend(_collect_sublink_links(entry))
    if not links:
        return base
    parsed = base.get("parsed")
    if isinstance(parsed, dict):
        merged_parsed = copy.deepcopy(parsed)
        merged_parsed["links"] = links
        base["parsed"] = merged_parsed
        base["rendered"] = json.dumps(merged_parsed, indent=2, ensure_ascii=False)
    else:
        base["rendered"] = "\n".join(links)
    formats = build_sublink_formats(links[0])
    base["sublink_formats"] = formats
    return base


def _merge_clash_client_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    base = copy.deepcopy(entries[0])
    parsed = copy.deepcopy(base.get("parsed") or {})
    if not isinstance(parsed, dict):
        return base
    all_proxies = list(parsed.get("proxies") or [])
    for entry in entries[1:]:
        ep = entry.get("parsed")
        if isinstance(ep, dict):
            all_proxies.extend(ep.get("proxies") or [])
    all_proxies = deduplicate_client_tags(all_proxies, tag_key="name")
    parsed["proxies"] = all_proxies
    section = _section_from_parsed(parsed)
    return {
        **base,
        **section,
        "clash_yaml": _clash_yaml_from_parsed(parsed),
    }


def _merge_singbox_client_entries(entries: list[dict[str, Any]], ua_parsed: dict[str, Any]) -> dict[str, Any]:
    base = copy.deepcopy(entries[0])
    parsed = copy.deepcopy(base.get("parsed") or {})
    if not isinstance(parsed, dict):
        return base
    for entry in entries[1:]:
        ep = entry.get("parsed")
        if not isinstance(ep, dict):
            continue
        for key in ("outbounds", "endpoints"):
            parsed[key] = list(parsed.get(key) or []) + list(ep.get(key) or [])
    section = {**base, "parsed": parsed}
    core = str(base.get("core") or "hiddify-core")
    return _finalize_singbox_client_section(section, core, ua_parsed)


def _merge_xray_client_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    base = entries[0]
    sections: list[dict[str, Any]] = []
    for entry in entries:
        sections.extend(entry.get("configs") or [])
    return _xray_client_entry_from_sections(
        sections,
        core=base.get("core") or "xray",
        version=base.get("version"),
        label=base.get("label") or "xray",
        index=base.get("index"),
        auto=bool(base.get("auto")),
    )


def _merge_bundle_client_entries(
    entries: list[dict[str, Any]],
    *,
    ua_parsed: dict[str, Any],
) -> dict[str, Any]:
    if not entries:
        return {}
    if len(entries) == 1:
        return entries[0]
    core = entries[0].get("core")
    if core == "xray":
        return _merge_xray_client_entries(entries)
    if core == "sublink":
        return _merge_sublink_client_entries(entries)
    if core == "clash":
        return _merge_clash_client_entries(entries)
    if core in ("hiddify-core", "singbox"):
        return _merge_singbox_client_entries(entries, ua_parsed)
    merged = entries[0]
    for extra in entries[1:]:
        merged = _merge_parsed_array_configs(merged, extra, ("outbounds", "inbounds", "endpoints", "proxies"))
    return merged


def _merge_bundle_server_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    if not entries:
        return {}
    if len(entries) == 1:
        return entries[0]
    merged = entries[0]
    for extra in entries[1:]:
        merged = _merge_parsed_array_configs(merged, extra, ("inbounds", "outbounds", "endpoints"))
    return merged


def _merge_bundle_results(bundles: list[dict[str, Any]], ua_parsed: dict[str, Any]) -> dict[str, Any]:
    if not bundles:
        return {
            "ok": True,
            "errors": [],
            "warnings": [],
            "context": {},
            "servers": [],
            "clients": [],
        }
    if len(bundles) == 1:
        return bundles[0]

    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    contexts: list[dict[str, Any]] = []
    for bundle in bundles:
        errors.extend(bundle.get("errors") or [])
        warnings.extend(bundle.get("warnings") or [])
        ctx = bundle.get("context") or {}
        if ctx:
            contexts.append(ctx)

    servers_by_core: dict[str, list[dict[str, Any]]] = {}
    for bundle in bundles:
        for entry in bundle.get("servers") or []:
            servers_by_core.setdefault(str(entry.get("core") or ""), []).append(entry)
    servers: list[dict[str, Any]] = []
    for core in SERVER_BUNDLE_CORES:
        group = servers_by_core.pop(core, [])
        if group:
            servers.append(_merge_bundle_server_entries(group))
    for group in servers_by_core.values():
        if group:
            servers.append(_merge_bundle_server_entries(group))

    clients_map: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for bundle in bundles:
        for entry in bundle.get("clients") or []:
            key = (str(entry.get("core") or ""), str(entry.get("version") or ""))
            clients_map.setdefault(key, []).append(entry)
    clients: list[dict[str, Any]] = []
    for key in sorted(clients_map):
        clients.append(_merge_bundle_client_entries(clients_map[key], ua_parsed=ua_parsed))

    domain_names = [str(ctx.get("domain") or "") for ctx in contexts if ctx.get("domain")]
    base_context = dict(contexts[0]) if contexts else {}
    if domain_names:
        base_context["domains"] = domain_names
        base_context["domain_count"] = len(domain_names)

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "context": base_context,
        "servers": servers,
        "clients": clients,
    }


def _generate_enabled_proxies_bundle_for_domain(
    child_id: int = 0,
    *,
    domain: str | None = None,
    domain_id: int | None = None,
    user_id: int | None = None,
    user_uuid: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    include_servers: bool = True,
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    proxies = (
        CustomProxy.query.filter(
            CustomProxy.child_id == child_id,
            CustomProxy.enable.is_(True),
        )
        .order_by(CustomProxy.sort_order, CustomProxy.id)
        .all()
    )

    resolved_ip = (ip or "").strip() or "203.0.113.1"
    resolved_ua = (user_agent or "").strip() or EXAMPLE_USER_AGENTS[0]["value"]
    ua_parsed = parse_user_agent(resolved_ua)
    user, _users = build_user_context(user_id=user_id, user_uuid=user_uuid)
    domain_data = build_domain_context(
        child_id,
        domain_id=domain_id,
        domain_host=domain,
        server_ip=resolved_ip,
        skip_network_lookup=True,
    )

    server_groups: dict[str, list[CustomProxy]] = {}
    client_groups: dict[tuple[str, str], list[tuple[CustomProxy, dict[str, Any]]]] = {}

    for proxy in proxies:
        if not proxy.enable:
            continue
        data = proxy.to_dict()
        if common_proxy_core_blocks(bool(data.get("is_common_proxy")), data.get("server_core"), hconfig(ConfigEnum.common_proxy_core, child_id)):
            continue
        server_core = (data.get("server_config") or {}).get("core") or "xray"
        server_groups.setdefault(server_core, []).append(proxy)

        client_config = data.get("client_config") or {}
        for cc in client_config.get("core_configs") or []:
            core_name = cc.get("core") or ""
            if not core_name:
                continue
            if not _keep_common_proxy_client_core(data, core_name, child_id):
                continue
            version = cc.get("version") or ""
            client_groups.setdefault((core_name, version), []).append((proxy, cc))

    servers: list[dict[str, Any]] = []
    if include_servers:
        for server_index, core in enumerate(SERVER_BUNDLE_CORES):
            core_proxies = server_groups.get(core, [])
            entry = _merge_server_bundle(
                child_id,
                core,
                core_proxies,
                domain_id=domain_id,
                domain_host=domain,
                ip=resolved_ip,
                user_id=user_id,
                user_uuid=user_uuid,
                user_agent=resolved_ua,
                errors=errors,
                warnings=warnings,
            )
            entry["index"] = server_index
            servers.append(entry)

    clients: list[dict[str, Any]] = []
    client_index = 0
    for (core_name, version), items in sorted(client_groups.items()):
        if core_name == "sublink":
            entry = _merge_sublink_bundle(
                child_id,
                version,
                items,
                domain_id=domain_id,
                domain_host=domain,
                ip=resolved_ip,
                user_id=user_id,
                user_uuid=user_uuid,
                user_agent=resolved_ua,
                errors=errors,
                warnings=warnings,
            )
        elif core_name == "clash":
            entry = _merge_clash_bundle(
                child_id,
                version,
                items,
                domain_id=domain_id,
                domain_host=domain,
                ip=resolved_ip,
                user_id=user_id,
                user_uuid=user_uuid,
                user_agent=resolved_ua,
                errors=errors,
                warnings=warnings,
            )
        else:
            entry = _merge_client_outbound_bundle(
                child_id,
                core_name,
                version,
                items,
                domain_id=domain_id,
                domain_host=domain,
                ip=resolved_ip,
                user_id=user_id,
                user_uuid=user_uuid,
                user_agent=resolved_ua,
                ua_parsed=ua_parsed,
                errors=errors,
                warnings=warnings,
            )
        entry["index"] = client_index
        client_index += 1
        clients.append(entry)

    if not proxies:
        warnings.append({"code": "no_proxies", "message": "No enabled custom proxies found"})

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "context": {
            "proxy_count": len(proxies),
            "domain": domain_data.get("name") or domain,
            "user": user.get("name") or user.get("uuid"),
            "user_uuid": user.get("uuid"),
            "ip": resolved_ip,
            "user_agent": resolved_ua,
            "user_agent_parsed": ua_parsed,
        },
        "servers": servers,
        "clients": clients,
    }


def generate_enabled_proxies_bundle(
    child_id: int = 0,
    *,
    domain: str | None = None,
    domain_id: int | None = None,
    domains: list[str] | None = None,
    domain_ids: list[int] | None = None,
    user_id: int | None = None,
    user_uuid: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    include_servers: bool = True,
) -> dict[str, Any]:
    resolved_ip = (ip or "").strip() or "203.0.113.1"
    resolved_ua = (user_agent or "").strip() or EXAMPLE_USER_AGENTS[0]["value"]
    ua_parsed = parse_user_agent(resolved_ua)
    targets = _resolve_bundle_domain_targets(
        child_id,
        domain=domain,
        domain_id=domain_id,
        domains=domains,
        domain_ids=domain_ids,
    )
    if len(targets) <= 1:
        target_domain_id, target_domain_host = targets[0]
        return _generate_enabled_proxies_bundle_for_domain(
            child_id,
            domain=target_domain_host,
            domain_id=target_domain_id,
            user_id=user_id,
            user_uuid=user_uuid,
            ip=resolved_ip,
            user_agent=resolved_ua,
            include_servers=include_servers,
        )

    bundles = [
        _generate_enabled_proxies_bundle_for_domain(
            child_id,
            domain=target_domain_host,
            domain_id=target_domain_id,
            user_id=user_id,
            user_uuid=user_uuid,
            ip=resolved_ip,
            user_agent=resolved_ua,
            include_servers=include_servers,
        )
        for target_domain_id, target_domain_host in targets
    ]
    return _merge_bundle_results(bundles, ua_parsed)
