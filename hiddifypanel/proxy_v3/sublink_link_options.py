from __future__ import annotations

import json
import re
from types import SimpleNamespace
from typing import Any


URI_LINK_TEMPLATE = (
    '{{uri.protocol}}://{{ uri.user }}:{{ uri.password }}@{{ uri.host }}:{{ uri.port }}/{{ uri.path }}'
    '?{{ uri.query_params|urlencoded }}#{{ uri.fragment |urlencoded }}'
)

BASE64_LINK_TEMPLATE = '{{ uri.protocol }}://{{ uri.content|trim|b64encode }}'

URI_FRAGMENT_INCLUDE = "{%- include 'hiddify-core/client/tag' -%}"

DEFAULT_BASE64_CONTENT = (
    '{\n'
    '  "v": "2",\n'
    f'  "ps": "{URI_FRAGMENT_INCLUDE}",\n'
    '  "add": "{{ proxy.server }}",\n'
    '  "port": "{{ proxy.port }}",\n'
    '  "id": "{{ user.uuid }}",\n'
    '  "aid": "0",\n'
    '  "net": "tcp",\n'
    '  "type": "none",\n'
    '  "host": "",\n'
    '  "path": "{{ proxy.path }}",\n'
    '  "tls": "tls"\n'
    '}'
)

DEFAULT_URI_FORMAT: dict[str, Any] = {
    'protocol': 'vless',
    'user': '{{ user.uuid }}',
    'password': '',
    'host': '{{ proxy.server }}',
    'port': '{{ proxy.port }}',
    'path': '/',
    'fragment': URI_FRAGMENT_INCLUDE,
    'query_params': {
        'encryption': 'none',
        'type': 'tcp',
        'security': 'tls',
    },
}

DEFAULT_BASE64_FORMAT: dict[str, Any] = {
    'protocol': 'vmess',
    'content': DEFAULT_BASE64_CONTENT,
}

DEFAULT_LINK_FORMAT_OPTIONS: dict[str, Any] = {
    'format': 'raw',
}


def jinja_trim_no_line(value: Any) -> str:
    return re.sub(r'\s+', '', str(value or ''))


def _migrate_legacy_options(raw: dict[str, Any]) -> dict[str, Any]:
    data = dict(raw)
    fmt = str(data.get('format') or '')
    if fmt in ('vless', 'vmess'):
        data['format'] = 'raw'
    if not data.get('uri_format') and data.get('vless_format'):
        legacy = dict(data.get('vless_format') or {})
        legacy.pop('pass', None)
        password = legacy.pop('password', None) or ''
        fragment = legacy.pop('fragment', None) or legacy.pop('tag', None) or URI_FRAGMENT_INCLUDE
        data['uri_format'] = {
            **DEFAULT_URI_FORMAT,
            **legacy,
            'password': password,
            'fragment': fragment,
        }
    if not data.get('base64_format') and data.get('vmess_format'):
        data['base64_format'] = dict(data.get('vmess_format') or {})
    uri = dict(data.get('uri_format') or {})
    if uri.get('tag') and not uri.get('fragment'):
        uri['fragment'] = uri.pop('tag')
    if uri.get('pass') and not uri.get('password'):
        uri['password'] = uri.pop('pass')
    if uri:
        data['uri_format'] = uri
    data.pop('raw_format', None)
    data.pop('vless_format', None)
    data.pop('vmess_format', None)
    return data


def normalize_link_format_options(raw: dict[str, Any] | None) -> dict[str, Any]:
    base = dict(DEFAULT_LINK_FORMAT_OPTIONS)
    if not raw:
        return base
    data = _migrate_legacy_options(raw)
    fmt = str(data.get('format') or 'uri')
    base['format'] = fmt if fmt in ('uri', 'raw', 'base64') else 'raw'
    uri = dict(DEFAULT_URI_FORMAT)
    uri.update(data.get('uri_format') or {})
    base['uri_format'] = uri
    b64 = dict(DEFAULT_BASE64_FORMAT)
    b64.update(data.get('base64_format') or {})
    base['base64_format'] = b64
    return base


def compose_link_template(options: dict[str, Any] | None) -> str | None:
    opts = normalize_link_format_options(options)
    if opts['format'] == 'raw':
        return None
    if opts['format'] == 'base64':
        return BASE64_LINK_TEMPLATE
    return URI_LINK_TEMPLATE


def _render_field_template(template_text: str, child_id: int, context: dict[str, Any]) -> str:
    text = (template_text or '').strip()
    if not text:
        return ''
    if '{%' in text or '{{' in text:
        from .custom_proxy_validate import render_template_text

        return (render_template_text(text, child_id, context) or '').strip()
    return text


def _render_fragment(template_text: str, child_id: int, context: dict[str, Any]) -> str:
    rendered = _render_field_template(template_text, child_id, context)
    return jinja_trim_no_line(rendered)


def build_uri_context(
    link_format_options: dict[str, Any] | None,
    child_id: int,
    context: dict[str, Any],
) -> SimpleNamespace:
    opts = normalize_link_format_options(link_format_options)
    fmt = opts['format']
    if fmt == 'base64':
        b64 = opts['base64_format']
        content = _render_field_template(str(b64.get('content') or ''), child_id, context)
        return SimpleNamespace(
            protocol=_render_field_template(str(b64.get('protocol') or 'vmess'), child_id, context),
            content=content,
        )

    uri_fmt = opts['uri_format']
    query_params: dict[str, str] = {}
    for key, value in (uri_fmt.get('query_params') or {}).items():
        query_params[str(key)] = _render_field_template(str(value), child_id, context)

    return SimpleNamespace(
        protocol=_render_field_template(str(uri_fmt.get('protocol') or ''), child_id, context),
        user=_render_field_template(str(uri_fmt.get('user') or ''), child_id, context),
        password=_render_field_template(str(uri_fmt.get('password') or ''), child_id, context),
        host=_render_field_template(str(uri_fmt.get('host') or ''), child_id, context),
        port=_render_field_template(str(uri_fmt.get('port') or ''), child_id, context),
        path=_render_field_template(str(uri_fmt.get('path') or ''), child_id, context),
        fragment=_render_fragment(str(uri_fmt.get('fragment') or URI_FRAGMENT_INCLUDE), child_id, context),
        query_params=query_params,
    )


def enrich_sublink_render_context(
    context: dict[str, Any],
    link_format_options: dict[str, Any] | None,
    child_id: int,
) -> dict[str, Any]:
    if not link_format_options:
        return context
    opts = normalize_link_format_options(link_format_options)
    if opts.get('format') == 'raw':
        return context
    merged = dict(context)
    merged['uri'] = build_uri_context(link_format_options, child_id, context)
    return merged
