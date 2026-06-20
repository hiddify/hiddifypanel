from __future__ import annotations

import copy
import json
import random
import re
import time
from typing import Any

import json5
import yaml
from jinja2 import DictLoader, Environment, TemplateSyntaxError, UndefinedError
from jinja2.exceptions import TemplateError

from hiddifypanel.models import ConfigEnum, CustomProxy, CustomProxyMode, Domain, ProxyTemplate, User
from hiddifypanel.models.proxy_base_config import BaseConfigSide, ProxyBaseConfig, default_base_content
from hiddifypanel import hutils
from hiddifypanel.hutils.flask import parse_user_agent

from .sublink_format import build_sublink_formats

from dataclasses import dataclass

from .alpn_helpers import alpn_list_for_tag, is_tls_alpn_tag, is_xhttp_proxy_data, stable_proxy_port


def _client_outbounds_template(cc: dict[str, Any]) -> str:
    return str(cc.get('outbounds_template') or cc.get('link_template') or '')
from .outbound_tags import deduplicate_client_tags
from .custom_proxy_ports import (
    mode_requires_static_ports,
    mode_uses_auto_ports,
    mode_uses_gateway_port,
    normalize_port_list,
    resolve_inbound_ports,
)
from .jinja_context import SkipExtension, TemplateSkip, build_template_context, skip_proxy
from .template_context_vars import (
    _PlatformPart,
    TemplateVersion,
)
from .template_variables import (
    _STATIC_DOMAIN_SAMPLE,
    build_domain_context,
    build_domain_sample,
    build_user_context,
)

SAMPLE_UUID = '00000000-0000-0000-0000-000000000001'

SERVER_BUNDLE_CORES: tuple[str, ...] = ('hiddify-core', 'xray', 'haproxy', 'nginx')


@dataclass(frozen=True)
class _ClientRenderVariant:
    alpn_tag: str
    download_alpn_tag: str | None = None
    domain_mode: str | None = None


def _proxy_server_tag(data: dict[str, Any], proxy_id: int | None = None) -> str:
    pid = int(proxy_id if proxy_id is not None else data.get('id') or 0)
    name = str(data.get('name') or data.get('slug') or 'proxy')
    safe_name = re.sub(r'[^\w.-]+', '_', name.strip()).strip('_') or 'proxy'
    return f'{pid}_{safe_name}'


def _client_outbound_tag(
    data: dict[str, Any],
    proxy_id: int | None,
    alpn_tag: str,
    domain_mode: str | None = None,
) -> str:
    base = _proxy_server_tag(data, proxy_id)
    if domain_mode:
        return f'{base}_{alpn_tag}_{domain_mode}'
    return f'{base}_{alpn_tag}'


def _sanitize_parsed_config(parsed: Any) -> Any:
    if not isinstance(parsed, dict):
        return parsed
    for key in ('outbounds', 'endpoints', 'inbounds'):
        items = parsed.get(key)
        if isinstance(items, list):
            parsed[key] = [item for item in items if isinstance(item, dict) and item]
    return parsed


EXAMPLE_USER_AGENTS: list[dict[str, str]] = [
    {
        'id': 'hiddify',
        'label': 'HiddifyNext 4.2 (Android)',
        'value': 'HiddifyNext/4.2.0 (android) like ClashMeta v2ray sing-box',
    },
    {
        'id': 'sfa',
        'label': 'SFA / sing-box 1.7',
        'value': 'SFA/1.7.0 (sing-box 1.7.0)',
    },
    {
        'id': 'foxray',
        'label': 'FoXray (iOS)',
        'value': 'FoXray',
    },
    {
        'id': 'xray',
        'label': 'xray 26.3.27',
        'value': 'xray/26.3.27',
    },
    {
        'id': 'clash',
        'label': 'Clash Meta',
        'value': 'ClashMeta/1.18.0',
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
    server_config = data.get('server_config') or {}
    base_tag = tag or server_config.get('tag') or data.get('slug') or 'example-tag'
    effective_proxy_id = proxy_id if proxy_id is not None else data.get('id')
    download_alpn = ''
    download_alpn_list: list[str] = []
    if server_side and effective_proxy_id:
        resolved_tag = _proxy_server_tag(data, int(effective_proxy_id))
        resolved_alpn = str(server_config.get('tag') or base_tag).strip()
        alpns: list[str] = []
        use_tls = False
        proxy_l3 = _infer_proxy_l3(data)
    else:
        server_tag = str(server_config.get('tag') or base_tag).strip()
        default_alpn = str((data.get('alpns') or [server_tag])[0])
        resolved_alpn = (alpn_tag or default_alpn).strip()
        use_tls = is_tls_alpn_tag(resolved_alpn)
        proxy_l3 = _infer_proxy_l3(data)
        resolved_tag = server_tag
        download_alpn = (download_alpn_tag or '').strip()
        alpns = alpn_list_for_tag(resolved_alpn) if use_tls else []
        download_alpn_list = alpn_list_for_tag(download_alpn) if download_alpn else []
    resolved_path = custom_path if custom_path is not None else (data.get('custom_path') or 'test-path')
    protocol = _proxy_mode_value(data)
    binding = domain_binding
    if binding is None:
        binding = 'ip' if protocol == CustomProxyMode.ip.value else 'domain'
    resolved_ip = (ip or '').strip()
    if not resolved_ip:
        if skip_network_lookup:
            resolved_ip = '203.0.113.1'
        else:
            resolved_ip = hutils.network.get_ip_str(4) or '203.0.113.1'
    effective_domain_id = domain_id
    stored_tcp = normalize_port_list(server_config.get('inbound_tcp_ports') or server_config.get('inbound_port'))
    stored_udp = normalize_port_list(server_config.get('inbound_udp_ports'))
    if effective_proxy_id:
        resolved_ports = resolve_inbound_ports(
            protocol,
            int(effective_proxy_id),
            domain_id=effective_domain_id,
            stored_tcp_ports=stored_tcp,
            stored_udp_ports=stored_udp,
        )
    else:
        resolved_ports = resolve_inbound_ports(
            protocol,
            0,
            domain_id=effective_domain_id,
            stored_tcp_ports=stored_tcp,
            stored_udp_ports=stored_udp,
        )
    if port is not None:
        resolved_port = port
    else:
        resolved_port = resolved_ports.tcp_port or resolved_ports.udp_port or 2080
    domain_data = build_domain_context(
        child_id,
        domain_id=domain_id,
        domain_host=domain_host,
        server_ip=resolved_ip if binding == 'ip' else None,
        skip_network_lookup=skip_network_lookup,
    )
    if domain_mode:
        domain_data = dict(domain_data)
        domain_data['mode'] = domain_mode
    if binding == 'ip':
        domain_data = dict(domain_data)
        domain_data['server'] = resolved_ip
        domain_data['ip'] = resolved_ip
    user, users = build_user_context(user_id=user_id, user_uuid=user_uuid)
    ua = user_agent or EXAMPLE_USER_AGENTS[1]['value']
    ua_parsed = parse_user_agent(ua)
    direct_port_access = bool(server_config.get('direct_port_access'))
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
            'id': effective_proxy_id,
            'mode': protocol,
            'tag': resolved_tag,
            'port': resolved_port,
            'tcp_ports': resolved_ports.tcp_ports,
            'udp_ports': resolved_ports.udp_ports,
            'tcp_port': resolved_ports.tcp_port,
            'udp_port': resolved_ports.udp_port,
            'direct_port_access': direct_port_access,
            'domain_binding': binding,
            'alpn': resolved_alpn if not server_side else '',
            'alpns': alpns,
            'download_alpn': download_alpn if not server_side else '',
            'download_alpn_list': download_alpn_list if not server_side else [],
            'tls': use_tls if not server_side else False,
            'l3': proxy_l3,
            'domain_modes': list(data.get('domain_modes') or []),
            'server_inbound_tcp_ports': stored_tcp,
            'server_inbound_udp_ports': stored_udp,
        },
    )
    ctx['alpns'] = alpns
    if server_side and core:
        version = (core_version or '').strip() or '1.0.0'
        platform = ctx.get('platform')
        if platform is not None and hasattr(platform, '_data'):
            platform._data['app'] = _PlatformPart(core, version)
            platform._data['app_version'] = TemplateVersion(version)
    return ctx


def build_sample_context(
    child_id: int = 0,
    tag: str = 'validate-tag',
    port: int = 2080,
    *,
    ip: str = '203.0.113.1',
    custom_path: str = 'test-path',
    domain_binding: str = 'domain',
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
        user_agent='HiddifyNext/3.0.0 (android) like ClashMeta v2ray sing-box',
    )
    if proxy_data:
        merged = dict(ctx.get('proxy') or {})
        merged.update(proxy_data)
        ctx['proxy'] = merged
    return ctx


def _template_map(child_id: int = 0) -> dict[str, str]:
    templates = ProxyTemplate.query.filter(
        (ProxyTemplate.child_id == child_id) | (ProxyTemplate.child_id == 0)
    ).all()
    return {t.slug: t.effective_content() for t in templates}


_template_map_cache: dict[int, tuple[float, dict[str, str]]] = {}
_jinja_env_cache: dict[int, tuple[float, Environment]] = {}
_JINJA_CACHE_TTL = 60.0


def _cached_template_map(child_id: int = 0) -> dict[str, str]:
    now = time.monotonic()
    cached = _template_map_cache.get(child_id)
    if cached and now - cached[0] < _JINJA_CACHE_TTL:
        return cached[1]
    mapping = _template_map(child_id)
    _template_map_cache[child_id] = (now, mapping)
    return mapping


def _jinja_env(child_id: int = 0) -> Environment:
    now = time.monotonic()
    cached = _jinja_env_cache.get(child_id)
    if cached and now - cached[0] < _JINJA_CACHE_TTL:
        return cached[1]
    env = Environment(
        loader=DictLoader(_cached_template_map(child_id)),
        keep_trailing_newline=True,
        extensions=[SkipExtension],
    )
    env.globals['enumerate'] = enumerate
    env.filters['tojson'] = lambda value: json.dumps(value, ensure_ascii=False)
    env.filters['b64encode'] = hutils.encode.do_base_64
    env.filters['choose_random'] = _jinja_choose_random
    _jinja_env_cache[child_id] = (now, env)
    return env


def _jinja_choose_random(value: Any) -> str:
    parts = [part.strip() for part in str(value or '').split(',') if part.strip()]
    if not parts:
        return ''
    return random.choice(parts)


def render_template_text(template_text: str, child_id: int = 0, context: dict[str, Any] | None = None) -> str:
    ctx = context or build_sample_context(child_id=child_id)
    env = _jinja_env(child_id)
    return env.from_string(template_text).render(**ctx)


def fix_duplicate_json_commas(text: str) -> str:
    """Collapse `, ,` / `,,` artifacts from adjacent Jinja includes into one comma."""
    text = re.sub(r'\[\s*,', '[', text)
    pattern = re.compile(r',(\s*),')
    prev = None
    while prev != text:
        prev = text
        text = pattern.sub(',', text)
    return text


def parse_json5(text: str) -> tuple[Any | None, str | None]:
    stripped = fix_duplicate_json_commas(text.strip())
    if not stripped:
        return None, None
    try:
        return json5.loads(stripped), None
    except Exception as e:
        return None, str(e)


def _wrap_as_json_object(fragment: str) -> str:
    fragment = fragment.strip()
    if not fragment:
        return '{}'
    if fragment.startswith('{') or fragment.startswith('['):
        return fragment
    return '{\n' + fragment + '\n}'


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
    if direct_port_access and listen in ('0.0.0.0', '::'):
        warnings.append({
            'code': 'direct_port_access',
            'message': 'Direct port access is enabled; binding to all interfaces may make the server discoverable',
        })
    if protocol == CustomProxyMode.domains_auto_public_ports.value:
        if listen not in ('0.0.0.0', '::1'):
            warnings.append({
                'code': 'listen_custom',
                'message': 'For multi-domain auto ports, listen should be 0.0.0.0 or ::1',
            })
    elif protocol and protocol != CustomProxyMode.domains_auto_public_ports.value:
        if direct_port_access:
            if listen not in ('127.0.0.1', '0.0.0.0', '::1'):
                warnings.append({
                    'code': 'listen_direct_port',
                    'message': 'With direct port access, listen should be 127.0.0.1 or 0.0.0.0',
                })
        elif listen != '127.0.0.1':
            warnings.append({
                'code': 'listen_non_custom',
                'message': 'For non-custom protocols, listen should be 127.0.0.1',
            })
    return warnings


def validate_port_rules(compiled_text: str, port: int | None = None) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for p in re.findall(r'"port"\s*:\s*(\d+)', compiled_text):
        if int(p) in (80, 443):
            errors.append({'code': 'port_reserved', 'message': f'Port {p} is not allowed (80/443)'})
    if port in (80, 443):
        errors.append({'code': 'port_reserved', 'message': f'Port {port} is not allowed (80/443)'})
    return errors


def validate_core_placeholders(template_text: str, core: str | None) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    has_tag = (
        'proxy.tag' in template_text
        or '{{TAG}}' in template_text
        or '{{ TAG }}' in template_text
    )
    has_port = (
        'proxy.port' in template_text
        or '{{PORT}}' in template_text
        or '{{ PORT }}' in template_text
    )
    if core == 'xray':
        if not has_tag:
            errors.append({'code': 'missing_tag', 'message': 'Xray template must include proxy.tag (or {{TAG}})'})
        if not has_port:
            errors.append({'code': 'missing_port', 'message': 'Xray template must include proxy.port (or {{PORT}})'})
        if re.search(r'"port"\s*:\s*\d+', template_text) and 'proxy.port' not in template_text and '{{PORT}}' not in template_text:
            errors.append({'code': 'hardcoded_port', 'message': 'Use proxy.port instead of a numeric port for xray'})
    elif core == 'hiddify-core':
        if not has_tag:
            errors.append({'code': 'missing_tag', 'message': 'Hiddify-core template must include proxy.tag (or {{TAG}})'})
        if not has_port:
            errors.append({'code': 'missing_listen_port', 'message': 'Hiddify-core template must include proxy.port (or {{PORT}}) for listen_port'})
        if re.search(r'"listen_port"\s*:\s*\d+', template_text) and 'proxy.port' not in template_text and '{{PORT}}' not in template_text:
            errors.append({'code': 'hardcoded_port', 'message': 'Use proxy.port instead of a numeric listen_port'})
    return errors



def validate_proxy_payload(
    data: dict[str, Any],
    child_id: int = 0,
    proxy_id: int | None = None,
    sections: list[str] | None = None,
) -> dict[str, Any]:
    sections = sections or ['server', 'client', 'general']
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    compiled_preview = ''
    compiled_json: Any = None

    if proxy_id:
        proxy = CustomProxy.query.filter(CustomProxy.id == proxy_id, CustomProxy.child_id == child_id).first()
        if proxy:
            merged = proxy.to_dict()
            merged.update(data)
            data = merged

    protocol = _proxy_mode_value(data)
    binding = 'ip' if protocol == CustomProxyMode.ip.value else 'domain'
    is_builtin = bool(data.get('is_builtin'))
    server_override = bool(data.get('server_override'))
    client_override = bool(data.get('client_override'))
    validate_server = (not is_builtin) or server_override
    validate_client = (not is_builtin) or client_override
    server_config = data.get('server_config') or {}
    client_config = data.get('client_config') or {}
    tag = server_config.get('tag') or data.get('slug') or 'validate-tag'
    stored_tcp = normalize_port_list(server_config.get('inbound_tcp_ports') or server_config.get('inbound_port'))
    stored_udp = normalize_port_list(server_config.get('inbound_udp_ports'))
    resolved_ports = resolve_inbound_ports(
        protocol or '',
        int(proxy_id or data.get('id') or 0),
        stored_tcp_ports=stored_tcp,
        stored_udp_ports=stored_udp,
    )
    port = resolved_ports.tcp_port or resolved_ports.udp_port or 2080
    core = server_config.get('core') or 'xray'
    direct_port_access = bool(server_config.get('direct_port_access'))
    ctx_client = build_sample_context(
        child_id=child_id,
        tag=tag,
        port=port,
        ip='203.0.113.1',
        custom_path=data.get('custom_path') or 'test-path',
        domain_binding=binding,
        server_side=False,
        proxy_data={
            'tag': tag,
            'port': port,
            'direct_port_access': direct_port_access,
            'domain_binding': binding,
        },
    )
    ctx_server = build_sample_context(
        child_id=child_id,
        tag=tag,
        port=port,
        ip='203.0.113.1',
        custom_path=data.get('custom_path') or 'test-path',
        domain_binding=binding,
        server_side=True,
        proxy_data={
            'tag': tag,
            'port': port,
            'direct_port_access': direct_port_access,
            'domain_binding': binding,
        },
    )

    if 'server' in sections and validate_server:
        inbound_template = server_config.get('inbound_template') or ''
        errors.extend(validate_core_placeholders(inbound_template, core))
        if inbound_template.strip():
            try:
                rendered = fix_duplicate_json_commas(render_template_text(inbound_template, child_id, ctx_server))
                compiled_preview = _wrap_as_json_object(rendered)
                compiled_json, parse_err = parse_json5(compiled_preview)
                if parse_err:
                    errors.append({'code': 'json5_parse', 'message': parse_err})
                else:
                    warnings.extend(validate_listen_rules(protocol, compiled_preview, direct_port_access))
                    errors.extend(validate_port_rules(compiled_preview, port))
            except TemplateSkip:
                warnings.append({
                    'code': 'template_skip',
                    'message': 'Server template skipped for current settings (SKIP)',
                })
            except (TemplateError, TemplateSyntaxError, UndefinedError) as e:
                errors.append({'code': 'jinja_error', 'message': str(e)})

    if 'client' in sections and validate_client:
        for idx, cc in enumerate(client_config.get('core_configs') or []):
            core_name = cc.get('core') or ''
            if core_name == 'sublink':
                tpl = _client_outbounds_template(cc)
                if tpl.strip():
                    try:
                        render_template_text(tpl, child_id, ctx_client)
                    except TemplateSkip:
                        pass
                    except (TemplateError, TemplateSyntaxError, UndefinedError) as e:
                        errors.append({'code': 'sublink_jinja_error', 'message': f'core_configs[{idx}]: {e}'})
                continue
            tpl = cc.get('outbounds_template') or ''
            if not tpl.strip():
                continue
            try:
                rendered = fix_duplicate_json_commas(render_template_text(tpl, child_id, ctx_client))
                wrapped = _wrap_as_json_object(rendered) if not rendered.strip().startswith('[') else rendered
                _, parse_err = parse_json5(wrapped)
                if parse_err:
                    errors.append({'code': 'client_json5_parse', 'message': f'core_configs[{idx}]: {parse_err}'})
            except TemplateSkip:
                pass
            except (TemplateError, TemplateSyntaxError, UndefinedError) as e:
                errors.append({'code': 'client_jinja_error', 'message': f'core_configs[{idx}]: {e}'})

    if 'general' in sections:
        domain_ids = [int(v) for v in (data.get('domain_ids') or []) if v is not None]
        if protocol == CustomProxyMode.domains_single_public_port.value:
            if len(domain_ids) > 1:
                errors.append({
                    'code': 'single_domain_multiple_domains',
                    'message': 'Single-domain static port mode supports only one selected domain',
                })
            elif not domain_ids:
                from hiddifypanel.models import Domain
                modes = [str(m).strip() for m in (data.get('domain_modes') or []) if str(m).strip()]
                if modes:
                    count = Domain.query.filter(
                        Domain.child_id == child_id,
                        Domain.mode.in_(modes),
                    ).count()
                    if count > 1:
                        warnings.append({
                            'code': 'single_domain_multiple_domains',
                            'message': 'Multiple domains match this proxy; single-domain static port allows only one domain',
                        })
        if mode_requires_static_ports(protocol):
            if not stored_tcp:
                errors.append({
                    'code': 'missing_inbound_tcp_ports',
                    'message': 'At least one inbound TCP port is required for this mode',
                })
        elif mode_uses_auto_ports(protocol) or mode_uses_gateway_port(protocol):
            if stored_tcp or stored_udp:
                warnings.append({
                    'code': 'ignored_inbound_ports',
                    'message': 'Inbound ports are calculated automatically for this mode and will be ignored',
                })
        if protocol == CustomProxyMode.domains_l7_gateway.value:
            allowed = {'direct', 'cdn', 'relay', 'fake'}
            invalid = [m for m in (data.get('domain_modes') or []) if m not in allowed]
            if invalid:
                errors.append({
                    'code': 'invalid_domain_modes',
                    'message': 'L7 gateway domain modes must be direct, cdn, relay, or fake',
                })
        elif protocol == CustomProxyMode.domains_sni_gateway.value:
            modes = list(data.get('domain_modes') or [])
            if modes != ['special']:
                warnings.append({
                    'code': 'domain_modes_forced_special',
                    'message': 'Domain mode is forced to special for SNI gateway mode',
                })
        elif protocol == CustomProxyMode.ip.value:
            allowed = {'direct', 'relay'}
            invalid = [m for m in (data.get('domain_modes') or []) if m not in allowed]
            if invalid:
                errors.append({
                    'code': 'invalid_domain_modes',
                    'message': 'IP mode domain modes must be direct or relay',
                })

    return {
        'ok': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'compiled_preview': compiled_preview,
        'compiled_json': compiled_json,
    }


def validate_base_config_content(data: dict[str, Any], child_id: int = 0) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    core = data.get('core') or ''
    content = data.get('content') or ''
    if not content.strip():
        return {'ok': True, 'errors': errors, 'warnings': warnings}
    ctx = build_sample_context(child_id=child_id)
    if core == 'sublink':
        try:
            render_template_text(content, child_id, ctx)
        except TemplateSkip:
            pass
        except (TemplateError, TemplateSyntaxError, UndefinedError) as e:
            errors.append({'code': 'jinja_error', 'message': str(e)})
        return {'ok': len(errors) == 0, 'errors': errors, 'warnings': warnings}
    try:
        rendered = fix_duplicate_json_commas(render_template_text(content, child_id, ctx))
        wrapped = _wrap_as_json_object(rendered)
        _, parse_err = parse_json5(wrapped)
        if parse_err:
            errors.append({'code': 'json5_parse', 'message': parse_err})
    except TemplateSkip:
        pass
    except (TemplateError, TemplateSyntaxError, UndefinedError) as e:
        errors.append({'code': 'jinja_error', 'message': str(e)})
    return {'ok': len(errors) == 0, 'errors': errors, 'warnings': warnings}


def _server_block_name(core: str) -> str:
    return 'inbounds' if core == 'hiddify-core' else 'inbound'


def _client_block_name(core: str) -> str:
    return 'outbounds'


_BUILTIN_OUTBOUND_TAGS = frozenset({'direct', 'block', 'dns-out', 'bypass', 'freedom', 'blackhole'})
_SELECTOR_TAGS = frozenset({'Select', 'Auto', 'proxy_select', 'proxy_auto'})


def _ua_version_gte(ua_parsed: dict, version_key: str, major: int, minor: int = 0, patch: int = 0) -> bool:
    raw_v = ua_parsed.get(version_key)
    if not raw_v:
        return False
    u_major = raw_v[0] if len(raw_v) > 0 else 0
    u_minor = raw_v[1] if len(raw_v) > 1 else 0
    u_patch = raw_v[2] if len(raw_v) > 2 else 0
    user_agent_v = f'{u_major}.{u_minor}.{u_patch}'
    needed_version = f'{major}.{minor}.{patch}'
    res = hutils.utils.compare_versions(user_agent_v, needed_version)
    return res == 0 or res == 1


def _wireguard_to_endpoints(ua_parsed: dict) -> bool:
    return _ua_version_gte(ua_parsed, 'hiddify_version', 4, 0, 0)


def _split_outbounds(outbounds: list) -> tuple[list, list, list]:
    selectors: list[dict] = []
    proxies: list[dict] = []
    builtins: list[dict] = []
    for item in outbounds:
        if not isinstance(item, dict):
            continue
        tag = item.get('tag', '')
        if tag in _SELECTOR_TAGS or item.get('type') in ('selector', 'urltest'):
            selectors.append(item)
        elif tag in _BUILTIN_OUTBOUND_TAGS:
            builtins.append(item)
        else:
            proxies.append(item)
    return selectors, proxies, builtins


def _selectable_outbound_tag(outbound: dict) -> str | None:
    tag = outbound.get('tag')
    if not tag or not isinstance(tag, str):
        return None
    if 'shadowtls-out' in tag or '§hide§' in tag:
        return None
    return tag


def _partition_client_fragments(items: list[dict], ua_parsed: dict) -> tuple[list[dict], list[dict]]:
    outbounds: list[dict] = []
    endpoints: list[dict] = []
    use_endpoints = _wireguard_to_endpoints(ua_parsed)
    for item in items:
        if use_endpoints and item.get('type') == 'wireguard':
            endpoints.append(item)
        else:
            outbounds.append(item)
    return outbounds, endpoints


def _parsed_to_items(parsed: Any) -> list[dict]:
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        if 'proxies' in parsed and isinstance(parsed['proxies'], list):
            return [item for item in parsed['proxies'] if isinstance(item, dict)]
        return [parsed]
    return []


def _inject_singbox_selectors(outbounds: list, tags: list[str]) -> list:
    filtered = [tag for tag in tags if tag and 'shadowtls-out' not in tag and '§hide§' not in tag]
    select = {
        'type': 'selector',
        'tag': 'Select',
        'outbounds': ['Auto', *filtered],
        'default': 'Auto',
    }
    auto = {
        'type': 'urltest',
        'tag': 'Auto',
        'outbounds': filtered,
        'url': 'https://www.gstatic.com/generate_204',
        'interval': '10m',
        'tolerance': 200,
    }
    return [select, auto, *outbounds]


def _finalize_singbox_client_section(section: dict[str, Any], core: str, ua_parsed: dict) -> dict[str, Any]:
    if core not in ('hiddify-core', 'singbox'):
        return section
    parsed = section.get('parsed')
    if not isinstance(parsed, dict):
        return section

    merged = copy.deepcopy(parsed)
    outbounds = list(merged.get('outbounds') or [])
    endpoints = list(merged.get('endpoints') or [])

    _, proxy_items, builtins = _split_outbounds(outbounds)
    proxy_out, wg_endpoints = _partition_client_fragments(proxy_items, ua_parsed)
    proxy_out = deduplicate_client_tags(proxy_out)
    endpoints.extend(wg_endpoints)

    tags = [_selectable_outbound_tag(item) for item in proxy_out]
    tags = [tag for tag in tags if tag]
    merged['outbounds'] = _inject_singbox_selectors(proxy_out + builtins, tags)
    if endpoints:
        merged['endpoints'] = endpoints

    route = merged.get('route')
    if isinstance(route, dict):
        route['final'] = 'Select'
    else:
        merged['route'] = {'final': 'Select', 'rules': []}

    rendered = json.dumps(merged, indent=2, ensure_ascii=False)
    return {
        **section,
        'rendered': rendered,
        'parsed': merged,
    }


def _proxy_mode_value(data: dict[str, Any]) -> str:
    mode = data.get('mode')
    if hasattr(mode, 'value'):
        return mode.value
    return str(mode or '')


def _infer_proxy_l3(data: dict[str, Any]) -> str:
    for token in data.get('tags') or []:
        key = str(token).lower()
        if key in ('reality', 'h3_quic', 'tls_h2', 'tls', 'http', 'ssh', 'udp', 'custom'):
            return key
    return 'tls'


def _client_render_variants(data: dict[str, Any]) -> list[_ClientRenderVariant]:
    allowed = [str(tag).strip() for tag in (data.get('alpns') or []) if str(tag).strip()]
    default = str((data.get('server_config') or {}).get('tag') or data.get('slug') or 'tls_h2')
    main_alpns = allowed or [default]
    download_allowed = [
        str(tag).strip() for tag in (data.get('download_alpns') or []) if str(tag).strip()
    ]
    if is_xhttp_proxy_data(data):
        if download_allowed:
            variants: list[_ClientRenderVariant] = []
            for alpn in main_alpns:
                for dl in download_allowed:
                    variants.append(_ClientRenderVariant(alpn_tag=alpn, download_alpn_tag=dl))
            return variants
        return [_ClientRenderVariant(alpn_tag=tag, download_alpn_tag=tag) for tag in main_alpns]
    return [_ClientRenderVariant(alpn_tag=tag) for tag in main_alpns]


def _variant_context_kwargs(variant: _ClientRenderVariant) -> dict[str, Any]:
    return {
        'alpn_tag': variant.alpn_tag,
        'download_alpn_tag': variant.download_alpn_tag,
        'domain_mode': variant.domain_mode,
    }


def _variant_label(variant: _ClientRenderVariant) -> str:
    label = variant.alpn_tag
    if variant.download_alpn_tag:
        label = f'{label}/{variant.download_alpn_tag}'
    if variant.domain_mode:
        label = f'{label}/{variant.domain_mode}'
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
    protocol = _proxy_mode_value(data)
    binding = 'ip' if protocol == CustomProxyMode.ip.value else 'domain'
    resolved_ip = (ip or '').strip() or '203.0.113.1'
    kwargs: dict[str, Any] = {
        'child_id': child_id,
        'data': data,
        'user_id': user_id,
        'user_uuid': user_uuid,
        'user_agent': user_agent,
        'server_side': server_side,
        'skip_network_lookup': True,
        'ip': resolved_ip,
        'proxy_id': proxy_id if proxy_id is not None else data.get('id'),
        'alpn_tag': alpn_tag,
        'download_alpn_tag': download_alpn_tag,
        'domain_mode': domain_mode,
        'core': core,
        'core_version': core_version,
    }
    if binding != 'ip':
        kwargs['domain_id'] = domain_id
        kwargs['domain_host'] = domain_host
    return build_render_context(**kwargs)


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
    return build_render_context(
        child_id,
        {},
        ip=(ip or '').strip() or '203.0.113.1',
        domain_id=domain_id,
        domain_host=domain_host,
        user_id=user_id,
        user_uuid=user_uuid,
        user_agent=user_agent,
        server_side=server_side,
        skip_network_lookup=True,
    )


def _render_base_section(
    child_id: int,
    context: dict[str, Any],
    side: str,
    core: str,
    version: str = '',
) -> dict[str, Any]:
    base = resolve_base_config_content(child_id, side, core, version)
    base = _extract_block_body(base, 'base_config') or base
    as_json = core not in ('haproxy', 'nginx')
    section = _render_section(base, child_id, context, as_json_object=as_json)
    parsed = section.get('parsed')
    if isinstance(parsed, dict):
        section = {
            **section,
            'parsed': _sanitize_parsed_config(copy.deepcopy(parsed)),
            'rendered': json.dumps(_sanitize_parsed_config(copy.deepcopy(parsed)), indent=2, ensure_ascii=False),
        }
    return section


def _clash_yaml_from_parsed(parsed: Any) -> str | None:
    if parsed is None:
        return None
    try:
        return yaml.dump(parsed, sort_keys=False, allow_unicode=True)
    except (TypeError, ValueError, yaml.YAMLError):
        return None


_BLOCK_BODY_RE = re.compile(
    r'\{%-?\s*block\s+(\w+)\s*-?%\}(.*?)\{%-?\s*endblock\s*-?%\}',
    re.DOTALL,
)
_EMPTY_BLOCK_RE = re.compile(
    r'\{%-?\s*block\s+(\w+)\s*-?%\}\s*\{%-?\s*endblock\s*-?%\}',
)


def _extract_block_body(fragment: str, block_name: str) -> str | None:
    match = _BLOCK_BODY_RE.search((fragment or '').strip())
    if match and match.group(1) == block_name:
        return match.group(2).strip()
    return None


def _fragment_block_body(fragment: str, block_name: str) -> str:
    body = _extract_block_body(fragment, block_name)
    if body is not None:
        return body
    stripped = (fragment or '').strip()
    if stripped.startswith('[') and stripped.endswith(']'):
        inner = stripped[1:-1].strip().rstrip(',')
        return f'{inner},\n' if inner else ''
    return stripped


def _inject_template_block(base: str, block_name: str, fragment: str) -> tuple[str, bool]:
    body = _fragment_block_body(fragment, block_name)
    replacement = f'{{% block {block_name} %}}\n{body}\n{{% endblock %}}'
    pattern = re.compile(
        rf'\{{%\-?\s*block\s+{re.escape(block_name)}\s*\-?%\}}\s*\{{%\-?\s*endblock\s*\-?%\}}',
    )
    merged, count = pattern.subn(replacement, base, count=1)
    return merged, count > 0


def _catalog_shell_base(side: str, core: str) -> str:
    from hiddifypanel.panel.template_catalog.base_configs import load_base_config_file

    file_core = 'hiddify-core' if core in ('hiddify-core', 'singbox') else core
    try:
        return load_base_config_file(file_core, side)
    except FileNotFoundError:
        return default_base_content(side, core)


def _render_fragment_section(
    child_id: int,
    context: dict[str, Any],
    fragment: str,
    block_name: str | None,
) -> dict[str, Any]:
    raw = (fragment or '').strip()
    extracted = _extract_block_body(raw, block_name or 'outbounds') if block_name else None
    if extracted is not None:
        body = extracted
    elif raw.startswith('[') and raw.endswith(']'):
        body = raw
    elif block_name:
        body = _fragment_block_body(fragment, block_name)
    else:
        body = raw
    if body.strip().startswith('['):
        return _render_section(body, child_id, context, as_json_object=False)
    if body.strip().startswith('{'):
        return _render_section(body, child_id, context, as_json_object=True)
    return _render_section(_wrap_as_json_object(body), child_id, context, as_json_object=True)


def _merge_rendered_sections(
    base_section: dict[str, Any],
    frag_section: dict[str, Any],
    block_name: str | None,
) -> dict[str, Any]:
    if frag_section.get('skipped'):
        return base_section
    if frag_section.get('error'):
        return {
            **base_section,
            'error': frag_section.get('error'),
        }
    base_parsed = base_section.get('parsed')
    frag_parsed = frag_section.get('parsed')
    if not isinstance(base_parsed, dict):
        return frag_section if frag_parsed is not None else base_section

    merged = copy.deepcopy(base_parsed)
    if block_name == 'inbound' or block_name == 'inbounds':
        key = 'inbounds'
        if isinstance(frag_parsed, list):
            items = frag_parsed
        elif isinstance(frag_parsed, dict):
            items = [frag_parsed]
        else:
            items = []
        merged[key] = items + list(merged.get(key) or [])
    elif block_name in ('outbound', 'outbounds', None):
        key = 'outbounds'
        if isinstance(frag_parsed, list):
            items = frag_parsed
        elif isinstance(frag_parsed, dict):
            if 'proxies' in frag_parsed:
                return {
                    'rendered': json.dumps(frag_parsed, indent=2, ensure_ascii=False),
                    'parsed': frag_parsed,
                    'skipped': False,
                    'error': None,
                }
            items = [frag_parsed]
        else:
            items = []
        merged[key] = items + list(merged.get(key) or [])
    elif block_name == 'endpoints':
        key = 'endpoints'
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
        'rendered': rendered,
        'parsed': merged,
        'skipped': False,
        'error': None,
    }


def resolve_base_config_content(
    child_id: int,
    side: str,
    core: str,
    version: str = '',
) -> str:
    side_val = side.value if hasattr(side, 'value') else side
    version = (version or '').strip()

    def _query(ver: str):
        return (
            ProxyBaseConfig.query.filter(
                ProxyBaseConfig.enable.is_(True),
                ProxyBaseConfig.side == side_val,
                ProxyBaseConfig.core == core,
                ProxyBaseConfig.version == ver,
                (ProxyBaseConfig.child_id == child_id) | (ProxyBaseConfig.child_id == 0),
            )
            .order_by(ProxyBaseConfig.child_id.desc())
            .first()
        )

    row = _query(version) if version else None
    if not row:
        row = _query('1.0.0')
    if not row:
        row = _query('')
    if row:
        return row.effective_content()
    return default_base_content(side_val, core)


def _base_usable_for_compose(base: str) -> bool:
    stripped = (base or '').strip()
    return bool(stripped) and stripped != '{}'


def _resolve_client_base_shell(
    child_id: int,
    side: str,
    core: str,
    version: str,
    cc: dict[str, Any],
) -> str:
    base = resolve_base_config_content(child_id, side, core, version)
    return _extract_block_body(base, 'base_config') or base


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
    if not (fragment or '').strip():
        return _render_section('', child_id, context, as_json_object=as_json_object)

    if not block_name:
        return _render_section(fragment, child_id, context, as_json_object=as_json_object)

    if base_template is not None:
        base = base_template
    else:
        base = resolve_base_config_content(child_id, side, core, version)
        base = _extract_block_body(base, 'base_config') or base
    if block_name and _base_usable_for_compose(base):
        injected, ok = _inject_template_block(base, block_name, fragment)
        if ok:
            return _render_section(injected, child_id, context, as_json_object=as_json_object)

    shell = _catalog_shell_base(side, core)
    shell = _extract_block_body(shell, 'base_config') or shell
    if block_name and _base_usable_for_compose(shell):
        injected, ok = _inject_template_block(shell, block_name, fragment)
        if ok:
            return _render_section(injected, child_id, context, as_json_object=as_json_object)

    if not _base_usable_for_compose(base):
        return _render_section(fragment, child_id, context, as_json_object=as_json_object)

    base_section = _render_section(base, child_id, context, as_json_object=True)
    if base_section.get('skipped'):
        return base_section

    frag_section = _render_fragment_section(child_id, context, fragment, block_name)
    return _merge_rendered_sections(base_section, frag_section, block_name)


def _xray_config_remarks(parsed: Any) -> str | None:
    if not isinstance(parsed, dict):
        return None
    outbounds = parsed.get('outbounds') or []
    for item in outbounds:
        if isinstance(item, dict):
            tag = item.get('tag')
            if tag and tag not in _BUILTIN_OUTBOUND_TAGS:
                return str(tag)
    return None


def _apply_xray_config_remarks(section: dict[str, Any]) -> dict[str, Any]:
    parsed = section.get('parsed')
    if not isinstance(parsed, dict):
        return section
    remarks = _xray_config_remarks(parsed)
    if remarks:
        parsed = copy.deepcopy(parsed)
        parsed['remarks'] = remarks
        section = {
            **section,
            'parsed': parsed,
            'rendered': json.dumps(parsed, indent=2, ensure_ascii=False),
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
    tpl = (cc.get('outbounds_template') or '').strip()
    if not tpl:
        return []
    version = cc.get('version') or ''
    base_shell = _resolve_client_base_shell(
        child_id,
        BaseConfigSide.client.value,
        'xray',
        version,
        cc,
    )
    block_name = _client_block_name('xray')
    proxy_label = data.get('name') or data.get('slug') or str(proxy_id)
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
            core='xray',
            version=version,
            fragment=tpl,
            block_name=block_name,
            base_template=base_shell,
        )
        section = _apply_xray_config_remarks(section)
        var_label = _variant_label(variant)
        section['variant_label'] = f'{proxy_label}/{var_label}'
        sections.append(section)
    return sections


def _xray_client_entry_from_sections(
    sections: list[dict[str, Any]],
    *,
    core: str,
    version: str | None,
    label: str,
    index: int | None,
) -> dict[str, Any]:
    if not sections:
        return {
            'core': core,
            'version': version,
            'label': label,
            'index': index,
            'configs': [],
            'rendered': '',
            'parsed': None,
            'skipped': False,
            'error': None,
        }
    first = sections[0]
    return {
        'core': core,
        'version': version,
        'label': label,
        'index': index,
        'configs': sections,
        'rendered': first.get('rendered') or '',
        'parsed': first.get('parsed') if len(sections) == 1 else None,
        'skipped': all(bool(s.get('skipped')) for s in sections),
        'error': next((s.get('error') for s in sections if s.get('error')), None),
    }


def _compose_sublink_full_config(
    child_id: int,
    context: dict[str, Any],
    *,
    version: str,
    outbounds_template: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    link_section = _render_section(outbounds_template, child_id, context, as_json_object=False)
    formats = build_sublink_formats(link_section.get('rendered') or '')
    if link_section.get('skipped') or link_section.get('error'):
        return link_section, formats

    link_value = link_section.get('rendered') or ''
    base = resolve_base_config_content(child_id, BaseConfigSide.client.value, 'sublink', version)
    if _base_usable_for_compose(base) and link_value:
        link_json = json.dumps(link_value, ensure_ascii=False)
        if '"links": []' in base:
            template = base.replace('"links": []', f'"links": [{link_json}]', 1)
        else:
            template = '{\n  "links": [' + link_json + ']\n}'
        full_section = _render_section(template, child_id, context, as_json_object=True)
    else:
        full_section = {
            'rendered': link_value,
            'parsed': {'links': [link_value]} if link_value else None,
            'skipped': False,
            'error': None,
        }
        if link_value:
            parsed, parse_err = parse_json5(json.dumps(full_section['parsed']))
            if parse_err:
                full_section['error'] = parse_err
            else:
                full_section['parsed'] = parsed
                full_section['rendered'] = json.dumps(parsed, indent=2, ensure_ascii=False)

    return full_section, formats


def _render_section(
    template_text: str,
    child_id: int,
    context: dict[str, Any],
    *,
    as_json_object: bool = True,
) -> dict[str, Any]:
    if not (template_text or '').strip():
        return {
            'rendered': '',
            'parsed': None,
            'skipped': False,
            'error': None,
        }
    try:
        rendered = render_template_text(template_text, child_id, context)
        if as_json_object and rendered.strip() and not rendered.strip().startswith(('[', '{')):
            wrapped = _wrap_as_json_object(rendered)
        else:
            wrapped = rendered
        if wrapped.strip().startswith(('{', '[')):
            wrapped = fix_duplicate_json_commas(wrapped)
        parsed = None
        parse_err = None
        if wrapped.strip().startswith(('{', '[')):
            to_parse = wrapped if wrapped.strip().startswith('{') else _wrap_as_json_object(wrapped)
            parsed, parse_err = parse_json5(to_parse)
        return {
            'rendered': wrapped,
            'parsed': parsed,
            'skipped': False,
            'error': parse_err,
        }
    except TemplateSkip:
        return {
            'rendered': 'SKIP',
            'parsed': None,
            'skipped': True,
            'error': None,
        }
    except (TemplateError, TemplateSyntaxError, UndefinedError) as e:
        return {
            'rendered': '',
            'parsed': None,
            'skipped': False,
            'error': str(e),
        }


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
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    proxy = CustomProxy.query.filter(CustomProxy.id == proxy_id, CustomProxy.child_id == child_id).first()
    if not proxy:
        return {
            'ok': False,
            'errors': [{'code': 'not_found', 'message': 'Custom proxy not found'}],
            'warnings': [],
            'context': {},
            'server': None,
            'clients': [],
        }

    data = proxy.to_dict()
    server_config = data.get('server_config') or {}
    client_config = data.get('client_config') or {}
    tag = server_config.get('tag') or data.get('slug') or 'example-tag'
    protocol = _proxy_mode_value(data)
    resolved_ports = resolve_inbound_ports(
        protocol,
        proxy_id,
        domain_id=domain_id,
        stored_tcp_ports=normalize_port_list(server_config.get('inbound_tcp_ports') or server_config.get('inbound_port')),
        stored_udp_ports=normalize_port_list(server_config.get('inbound_udp_ports')),
    )
    port = resolved_ports.tcp_port or resolved_ports.udp_port or 2080
    core = server_config.get('core') or 'xray'
    binding = 'ip' if protocol == CustomProxyMode.ip.value else 'domain'
    resolved_ip = (ip or '').strip() or '203.0.113.1'
    resolved_ua = (user_agent or '').strip() or EXAMPLE_USER_AGENTS[1]['value']
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

    server_result: dict[str, Any] | None = None
    inbound_template = server_config.get('inbound_template') or ''
    if inbound_template.strip():
        section = _compose_full_config(
            child_id,
            ctx_server,
            side=BaseConfigSide.server.value,
            core=core,
            version='',
            fragment=inbound_template,
            block_name=_server_block_name(core),
        )
        server_result = {
            'core': core,
            'version': None,
            'label': core,
            'index': None,
            **section,
        }
        if section.get('error'):
            errors.append({'code': 'server_render', 'message': section['error']})
        elif section.get('skipped'):
            warnings.append({'code': 'server_skip', 'message': 'Server template skipped (SKIP)'})

    clients: list[dict[str, Any]] = []
    for idx, cc in enumerate(client_config.get('core_configs') or []):
        core_name = cc.get('core') or ''
        version = cc.get('version') or ''
        label = f'{core_name}{f" ≥ {version}" if version else ""}'
        if core_name == 'sublink':
            tpl = _client_outbounds_template(cc)
            section, formats = _compose_sublink_full_config(
                child_id,
                ctx_client,
                version=version,
                outbounds_template=tpl,
            )
            entry = {
                'core': core_name,
                'version': version or None,
                'label': label,
                'index': idx,
                **section,
                'sublink_formats': formats,
                'rendered': section.get('rendered') or formats.get('raw') or '',
            }
            clients.append(entry)
            if section.get('error'):
                errors.append({'code': 'client_render', 'message': f'{label}: {section["error"]}'})
            elif formats.get('parse_error'):
                warnings.append({'code': 'sublink_parse', 'message': f'{label}: {formats["parse_error"]}'})
            continue
        if core_name == 'clash':
            tpl = cc.get('outbounds_template') or ''
            if not tpl.strip():
                clients.append({
                    'core': core_name,
                    'version': version or None,
                    'label': label,
                    'index': idx,
                    'rendered': '',
                    'parsed': None,
                    'skipped': False,
                    'error': None,
                })
                continue
            section = _compose_full_config(
                child_id,
                ctx_client,
                side=BaseConfigSide.client.value,
                core=core_name,
                version=version,
                fragment=tpl,
                block_name=None,
            )
            entry = {'core': core_name, 'version': version or None, 'label': label, 'index': idx, **section}
            entry['clash_yaml'] = _clash_yaml_from_parsed(section.get('parsed'))
            clients.append(entry)
            if section.get('error'):
                errors.append({'code': 'client_render', 'message': f'{label}: {section["error"]}'})
            elif section.get('skipped'):
                warnings.append({'code': 'client_skip', 'message': f'{label}: skipped (SKIP)'})
            continue
        tpl = cc.get('outbounds_template') or ''
        if not tpl.strip():
            clients.append({
                'core': core_name,
                'version': version or None,
                'label': label,
                'index': idx,
                'rendered': '',
                'parsed': None,
                'skipped': False,
                'error': None,
            })
            continue
        if core_name == 'xray':
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
            )
            clients.append(entry)
            for section in xray_sections:
                var_label = section.get('variant_label') or label
                if section.get('error'):
                    errors.append({'code': 'client_render', 'message': f'{var_label} ({label}): {section["error"]}'})
                elif section.get('skipped'):
                    warnings.append({'code': 'client_skip', 'message': f'{var_label} ({label}): skipped (SKIP)'})
            continue
        block_name = _client_block_name(core_name)
        merged_section = _render_base_section(
            child_id,
            ctx_client,
            BaseConfigSide.client.value,
            core_name,
            version,
        )
        parsed = merged_section.get('parsed')
        if isinstance(parsed, dict):
            merged = copy.deepcopy(parsed)
            proxy_label = data.get('name') or data.get('slug') or str(proxy_id)
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
                frag = _render_fragment_section(child_id, alpn_ctx, tpl, block_name)
                alpn_label = _variant_label(variant)
                if frag.get('skipped'):
                    warnings.append({
                        'code': 'client_skip',
                        'message': f'{proxy_label}/{alpn_label} ({label}): skipped (SKIP)',
                    })
                    continue
                if frag.get('error'):
                    errors.append({
                        'code': 'client_render',
                        'message': f'{proxy_label}/{alpn_label} ({label}): {frag["error"]}',
                    })
                    continue
                items_list = _parsed_to_items(frag.get('parsed'))
                outbound_items, endpoint_items = _partition_client_fragments(items_list, ua_parsed)
                _append_client_outbound_items(merged, outbound_items, endpoint_items)
            merged = _sanitize_parsed_config(merged)
            section = _section_from_parsed(merged, error=merged_section.get('error'))
        else:
            section = _compose_full_config(
                child_id,
                ctx_client,
                side=BaseConfigSide.client.value,
                core=core_name,
                version=version,
                fragment=tpl,
                block_name=block_name,
            )
        section = _finalize_singbox_client_section(section, core_name, ua_parsed)
        entry = {'core': core_name, 'version': version or None, 'label': label, 'index': idx, **section}
        clients.append(entry)
        if section.get('error'):
            errors.append({'code': 'client_render', 'message': f'{label}: {section["error"]}'})
        elif section.get('skipped'):
            warnings.append({'code': 'client_skip', 'message': f'{label}: skipped (SKIP)'})

    return {
        'ok': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'context': {
            'custom_proxy_id': proxy_id,
            'domain': domain_data.get('name') or domain,
            'user': user.get('name') or user.get('uuid'),
            'ip': resolved_ip,
            'user_agent': resolved_ua,
            'user_agent_parsed': ua_parsed,
            'tag': tag,
            'port': port,
            'domain_binding': binding,
        },
        'server': server_result,
        'clients': clients,
    }


def _append_client_outbound_items(
    merged: dict[str, Any],
    outbound_items: list[dict],
    endpoint_items: list[dict],
) -> None:
    outbounds = list(merged.get('outbounds') or [])
    _, proxy_items, builtins = _split_outbounds(outbounds)
    proxy_items.extend(outbound_items)
    merged['outbounds'] = proxy_items + builtins
    if endpoint_items:
        merged['endpoints'] = list(merged.get('endpoints') or []) + endpoint_items


def _section_from_parsed(parsed: dict[str, Any] | None, *, error: str | None = None) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        return {
            'rendered': '',
            'parsed': None,
            'skipped': False,
            'error': error,
        }
    return {
        'rendered': json.dumps(parsed, indent=2, ensure_ascii=False),
        'parsed': parsed,
        'skipped': False,
        'error': error,
    }


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
    if merged_section.get('error'):
        return {
            'core': core,
            'version': None,
            'label': core,
            'index': None,
            **merged_section,
        }

    for proxy in proxies:
        data = proxy.to_dict()
        if (data.get('server_config') or {}).get('core') != core:
            continue
        inbound_tpl = (data.get('server_config') or {}).get('inbound_template') or ''
        if not inbound_tpl.strip():
            continue
        protocol = _proxy_mode_value(data)
        server_domain_id = domain_id
        server_domain_host = domain_host
        if protocol == CustomProxyMode.domains_l7_gateway.value:
            server_domain_id = None
            server_domain_host = None
        ctx = _build_proxy_context(
            child_id,
            data,
            domain_id=server_domain_id,
            domain_host=server_domain_host,
            ip=ip,
            user_id=user_id,
            user_uuid=user_uuid,
            user_agent=user_agent,
            server_side=True,
            proxy_id=proxy.id,
            core=core,
            core_version='',
        )
        frag = _render_fragment_section(child_id, ctx, inbound_tpl, block_name)
        proxy_label = data.get('name') or data.get('slug') or str(proxy.id)
        if frag.get('skipped'):
            warnings.append({'code': 'server_skip', 'message': f'{proxy_label}: server skipped (SKIP)'})
            continue
        if frag.get('error'):
            errors.append({'code': 'server_render', 'message': f'{proxy_label}: {frag["error"]}'})
            continue
        merged_section = _merge_rendered_sections(merged_section, frag, block_name)

    return {
        'core': core,
        'version': None,
        'label': core,
        'index': None,
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
    label = f'{core}{f" ≥ {version}" if version else ""}'
    if core == 'xray':
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
                var_label = section.get('variant_label') or label
                if section.get('error'):
                    errors.append({'code': 'client_render', 'message': f'{var_label} ({label}): {section["error"]}'})
                elif section.get('skipped'):
                    warnings.append({'code': 'client_skip', 'message': f'{var_label} ({label}): skipped (SKIP)'})
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
    block_name = _client_block_name(core)
    merged_section = _render_base_section(
        child_id,
        bundle_ctx,
        BaseConfigSide.client.value,
        core,
        version,
    )
    if merged_section.get('error'):
        return {
            'core': core,
            'version': version or None,
            'label': label,
            'index': None,
            **merged_section,
        }

    parsed = merged_section.get('parsed')
    if not isinstance(parsed, dict):
        return {
            'core': core,
            'version': version or None,
            'label': label,
            'index': None,
            **merged_section,
        }

    merged = copy.deepcopy(parsed)
    for proxy, cc in items:
        data = proxy.to_dict()
        tpl = cc.get('outbounds_template') or ''
        if not tpl.strip():
            continue
        proxy_label = data.get('name') or data.get('slug') or str(proxy.id)
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
            alpn_label = f'{proxy_label}/{_variant_label(variant)}'
            if frag.get('skipped'):
                warnings.append({'code': 'client_skip', 'message': f'{alpn_label} ({label}): skipped (SKIP)'})
                continue
            if frag.get('error'):
                errors.append({'code': 'client_render', 'message': f'{alpn_label} ({label}): {frag["error"]}'})
                continue
            items_list = _parsed_to_items(frag.get('parsed'))
            outbound_items, endpoint_items = _partition_client_fragments(items_list, ua_parsed)
            _append_client_outbound_items(merged, outbound_items, endpoint_items)

    section = _section_from_parsed(_sanitize_parsed_config(merged), error=merged_section.get('error'))
    section = _finalize_singbox_client_section(section, core, ua_parsed)
    return {
        'core': core,
        'version': version or None,
        'label': label,
        'index': None,
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
    label = f'clash{f" ≥ {version}" if version else ""}'
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
        'clash',
        version,
    )
    parsed = merged_section.get('parsed')
    if not isinstance(parsed, dict):
        return {
            'core': 'clash',
            'version': version or None,
            'label': label,
            'index': None,
            **merged_section,
        }

    merged = copy.deepcopy(parsed)
    all_proxies = list(merged.get('proxies') or [])
    for proxy, cc in items:
        data = proxy.to_dict()
        tpl = cc.get('outbounds_template') or ''
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
            proxy_label = data.get('name') or data.get('slug') or str(proxy.id)
            if frag.get('skipped'):
                warnings.append({
                    'code': 'client_skip',
                    'message': f'{proxy_label}/{_variant_label(variant)} ({label}): skipped (SKIP)',
                })
                continue
            if frag.get('error'):
                errors.append({
                    'code': 'client_render',
                    'message': f'{proxy_label}/{_variant_label(variant)} ({label}): {frag["error"]}',
                })
                continue
            for item in _parsed_to_items(frag.get('parsed')):
                if isinstance(item, dict) and item.get('name') and not item.get('tag'):
                    item['tag'] = item['name']
                all_proxies.append(item)

    all_proxies = deduplicate_client_tags(all_proxies, tag_key='name')
    for item in all_proxies:
        if isinstance(item, dict) and item.get('tag') and not item.get('name'):
            item['name'] = item['tag']

    merged['proxies'] = all_proxies
    section = _section_from_parsed(merged)
    return {
        'core': 'clash',
        'version': version or None,
        'label': label,
        'index': None,
        **section,
        'clash_yaml': _clash_yaml_from_parsed(merged),
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
    label = f'sublink{f" ≥ {version}" if version else ""}'
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
        proxy_label = data.get('name') or data.get('slug') or str(proxy.id)
        if link_section.get('skipped'):
            warnings.append({'code': 'client_skip', 'message': f'{proxy_label} ({label}): skipped (SKIP)'})
            continue
        if link_section.get('error'):
            errors.append({'code': 'client_render', 'message': f'{proxy_label} ({label}): {link_section["error"]}'})
            continue
        link_val = (link_section.get('rendered') or '').strip()
        if link_val:
            links.append(link_val.strip('"'))

    if not links:
        return {
            'core': 'sublink',
            'version': version or None,
            'label': label,
            'index': None,
            'rendered': '',
            'parsed': None,
            'skipped': False,
            'error': None,
            'sublink_formats': build_sublink_formats(''),
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
    base = resolve_base_config_content(child_id, BaseConfigSide.client.value, 'sublink', version)
    links_json = ', '.join(json.dumps(link, ensure_ascii=False) for link in links)
    if _base_usable_for_compose(base) and '"links": []' in base:
        template = base.replace('"links": []', f'"links": [{links_json}]', 1)
    else:
        template = '{\n  "links": [' + links_json + ']\n}'
    section = _render_section(template, child_id, bundle_ctx, as_json_object=True)
    formats = build_sublink_formats(links[0])
    return {
        'core': 'sublink',
        'version': version or None,
        'label': label,
        'index': None,
        **section,
        'sublink_formats': formats,
        'rendered': section.get('rendered') or formats.get('raw') or '',
    }


def generate_enabled_proxies_bundle(
    child_id: int = 0,
    *,
    domain: str | None = None,
    domain_id: int | None = None,
    user_id: int | None = None,
    user_uuid: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
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

    resolved_ip = (ip or '').strip() or '203.0.113.1'
    resolved_ua = (user_agent or '').strip() or EXAMPLE_USER_AGENTS[0]['value']
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
        data = proxy.to_dict()
        server_core = (data.get('server_config') or {}).get('core') or 'xray'
        server_groups.setdefault(server_core, []).append(proxy)

        client_config = data.get('client_config') or {}
        for cc in client_config.get('core_configs') or []:
            core_name = cc.get('core') or ''
            if not core_name:
                continue
            version = cc.get('version') or ''
            client_groups.setdefault((core_name, version), []).append((proxy, cc))

    servers: list[dict[str, Any]] = []
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
        entry['index'] = server_index
        servers.append(entry)

    clients: list[dict[str, Any]] = []
    client_index = 0
    for (core_name, version), items in sorted(client_groups.items()):
        if core_name == 'sublink':
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
        elif core_name == 'clash':
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
        entry['index'] = client_index
        client_index += 1
        clients.append(entry)

    if not proxies:
        warnings.append({'code': 'no_proxies', 'message': 'No enabled custom proxies found'})

    return {
        'ok': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'context': {
            'proxy_count': len(proxies),
            'domain': domain_data.get('name') or domain,
            'user': user.get('name') or user.get('uuid'),
            'ip': resolved_ip,
            'user_agent': resolved_ua,
            'user_agent_parsed': ua_parsed,
        },
        'servers': servers,
        'clients': clients,
    }
