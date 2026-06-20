from __future__ import annotations

import base64
import json
import re
from typing import Any
from urllib.parse import parse_qs, quote, urlencode, urlparse


def _decode_base64_loose(value: str) -> bytes:
    padding = '=' * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except Exception:
        return base64.b64decode(value + padding)


def _vmess_legacy_to_link_json(data: dict[str, Any]) -> dict[str, Any]:
    """Map classic vmess JSON keys into unified link JSON."""
    add = data.get('add') or data.get('server') or data.get('host') or ''
    port = data.get('port') or 443
    params: dict[str, Any] = {}
    for key in ('aid', 'scy', 'net', 'type', 'host', 'path', 'tls', 'sni', 'alpn', 'fp', 'pbk', 'sid'):
        if data.get(key) not in (None, ''):
            params[key] = data[key]
    return {
        'protocol': 'vmess',
        'username': str(data.get('id') or data.get('uuid') or ''),
        'password': '',
        'server': str(add),
        'port': int(port) if str(port).isdigit() else port,
        'uripath': str(data.get('path') or ''),
        'params': params,
        'fragment': data.get('ps') or data.get('remark') or None,
    }


def uri_to_link_json(raw: str) -> dict[str, Any] | None:
    """Parse a proxy share link into structured JSON."""
    text = (raw or '').strip()
    if not text:
        return None

    if text.lower().startswith('vmess://'):
        payload = text[8:].strip()
        try:
            decoded = _decode_base64_loose(payload).decode('utf-8')
            data = json.loads(decoded)
            if isinstance(data, dict):
                return _vmess_legacy_to_link_json(data)
        except Exception:
            return None
        return None

    if text.startswith('{'):
        try:
            data = json.loads(text)
            if isinstance(data, dict) and data.get('protocol'):
                return data
        except json.JSONDecodeError:
            return None

    parsed = urlparse(text)
    if not parsed.scheme:
        return None

    username = parsed.username or ''
    password = parsed.password or ''
    host = parsed.hostname or ''
    port = parsed.port if parsed.port is not None else 443
    path = (parsed.path or '').strip('/')
    if path == '?':
        path = ''

    params: dict[str, Any] = {}
    if parsed.query:
        for key, values in parse_qs(parsed.query, keep_blank_values=True).items():
            params[key] = values[0] if len(values) == 1 else values

    return {
        'protocol': parsed.scheme,
        'username': username,
        'password': password or '',
        'server': host,
        'port': port,
        'uripath': path,
        'params': params,
        'fragment': parsed.fragment or None,
    }


def link_json_to_uri(data: dict[str, Any]) -> str:
    """Build vless/vmess/trojan-style URI from structured JSON."""
    protocol = str(data.get('protocol') or 'vless')
    username = str(data.get('username') or '')
    password = str(data.get('password') or '')
    server = str(data.get('server') or '')
    port = data.get('port') or 443
    uripath = str(data.get('uripath') or '').strip('/')
    params = dict(data.get('params') or {})

    if password:
        userinfo = f'{quote(username, safe="")}:{quote(password, safe="")}'
    else:
        userinfo = quote(username, safe="")

    netloc = f'{userinfo}@{server}:{port}'
    path_part = f'/{uripath}' if uripath else ''
    query = urlencode(params, quote_via=quote) if params else ''
    uri = f'{protocol}://{netloc}{path_part}'
    if query:
        uri += f'?{query}'
    fragment = data.get('fragment')
    if fragment:
        uri += f'#{fragment}'
    return uri


def link_json_to_vmess_uri(data: dict[str, Any]) -> str:
    """vmess:// + base64(json) using the unified link JSON payload."""
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    encoded = base64.urlsafe_b64encode(payload.encode('utf-8')).decode('ascii').rstrip('=')
    return f'vmess://{encoded}'


def build_sublink_formats(raw: str) -> dict[str, Any]:
    """Produce raw, vless, and vmess representations for a rendered sublink."""
    raw_text = (raw or '').strip()
    result: dict[str, Any] = {
        'raw': raw_text,
        'vless_json': None,
        'vless_uri': None,
        'vmess_json': None,
        'vmess_uri': None,
        'parse_error': None,
    }
    if not raw_text:
        return result

    link_json = uri_to_link_json(raw_text)
    if not link_json:
        result['parse_error'] = 'Could not parse rendered link into structured JSON'
        return result

    result['vless_json'] = link_json
    result['vless_uri'] = link_json_to_uri(link_json)
    result['vmess_json'] = link_json
    result['vmess_uri'] = link_json_to_vmess_uri(link_json)
    return result
