from __future__ import annotations

import copy
from typing import Any

from hiddifypanel.database import db
from hiddifypanel.hutils.proxy.custom_proxy_ports import normalize_port_list
from hiddifypanel.models.custom_proxy import (
    CustomProxy,
    CustomProxyClientCore,
    normalize_custom_path,
)


def _client_template(item: dict[str, Any]) -> str:
    return str(item.get('outbounds_template') or item.get('link_template') or '')


def custom_proxy_catalog_body(preset: dict[str, Any]) -> dict[str, Any]:
    server = copy.deepcopy(preset.get('server_config') or {})
    return {
        'alpns': list(preset.get('alpns') or []),
        'download_alpns': list(preset.get('download_alpns') or []),
        'custom_path': normalize_custom_path(preset.get('custom_path')),
        'domain_modes': list(preset.get('domain_modes') or []),
        'server_core': server.get('core') or 'xray',
        'server_tag': server.get('tag') or '',
        'server_inbound_tcp_ports': list(server.get('inbound_tcp_ports') or server.get('inbound_port') or []),
        'server_inbound_udp_ports': list(server.get('inbound_udp_ports') or []),
        'server_template_slugs': list(server.get('template_slugs') or []),
        'server_config': server.get('inbound_template') or '',
        'client_cores': copy.deepcopy((preset.get('client_config') or {}).get('core_configs') or []),
    }


def custom_proxy_body_from_dict(data: dict[str, Any]) -> dict[str, Any]:
    server = copy.deepcopy(data.get('server_config') or {})
    if isinstance(server, str):
        inbound_template = server
        server = {}
    else:
        inbound_template = server.get('inbound_template') or ''
    return {
        'alpns': list(data.get('alpns') or []),
        'download_alpns': list(data.get('download_alpns') or []),
        'custom_path': normalize_custom_path(data.get('custom_path')),
        'domain_modes': list(data.get('domain_modes') or []),
        'server_core': server.get('core') or data.get('server_core') or 'xray',
        'server_tag': server.get('tag') or data.get('server_tag') or '',
        'server_inbound_tcp_ports': normalize_port_list(
            server.get('inbound_tcp_ports', data.get('server_inbound_tcp_ports'))
        ),
        'server_inbound_udp_ports': normalize_port_list(
            server.get('inbound_udp_ports', data.get('server_inbound_udp_ports'))
        ),
        'server_template_slugs': list(server.get('template_slugs') or data.get('server_template_slugs') or []),
        'server_config': inbound_template,
        'client_cores': copy.deepcopy((data.get('client_config') or {}).get('core_configs') or []),
    }


def _builtin_catalog(row: CustomProxy) -> dict[str, Any]:
    return {
        'alpns': list(row.alpns or []),
        'download_alpns': list(row.download_alpns or []),
        'custom_path': row.custom_path or '',
        'domain_modes': list(row.domain_modes or []),
        'server_core': row.server_core.value if row.server_core else 'xray',
        'server_tag': row.server_tag or '',
        'server_inbound_tcp_ports': list(row.server_inbound_tcp_ports or []),
        'server_inbound_udp_ports': list(row.server_inbound_udp_ports or []),
        'server_template_slugs': list(row.server_template_slugs or []),
        'server_config': row.builtin_server_config or '',
        'client_cores': [cc.to_dict() for cc in row.client_cores],
    }


def effective_custom_proxy_body(row: CustomProxy) -> dict[str, Any]:
    if not row.is_builtin:
        return custom_proxy_body_from_dict(row.to_dict())
    data = row.to_dict()
    catalog = _builtin_catalog(row)
    return {
        'alpns': list(catalog.get('alpns') or row.alpns or []),
        'download_alpns': list(catalog.get('download_alpns') or row.download_alpns or []),
        'custom_path': normalize_custom_path(catalog.get('custom_path') or row.custom_path),
        'domain_modes': list(catalog.get('domain_modes') or row.domain_modes or []),
        'server_config': data['server_config'],
        'client_config': data['client_config'],
    }


def apply_custom_proxy_general(row: CustomProxy, body: dict[str, Any]) -> None:
    if 'alpns' in body:
        row.alpns = [str(v).strip() for v in (body.get('alpns') or []) if str(v).strip()]
    if 'download_alpns' in body:
        row.download_alpns = [
            str(v).strip() for v in (body.get('download_alpns') or []) if str(v).strip()
        ]
    if 'custom_path' in body:
        row.custom_path = normalize_custom_path(body.get('custom_path'))
    if 'domain_modes' in body:
        row.domain_modes = list(body.get('domain_modes') or [])


def apply_server_override(row: CustomProxy, *, override: bool) -> None:
    row.server_override = bool(override)
    if override:
        if not (row.server_config or '').strip():
            row.server_config = row.builtin_server_config or ''
    else:
        row.server_config = row.builtin_server_config or ''


def _replace_client_core_rows(row: CustomProxy, core_configs: list[dict[str, Any]], *, builtin: bool) -> None:
    from hiddifypanel.models.custom_proxy import _parse_client_core

    for existing in list(row.client_cores):
        db.session.delete(existing)
    row.client_cores.clear()
    db.session.flush()
    for item in core_configs:
        core = _parse_client_core(item.get('core'))
        outbound = _client_template(item)
        row.client_cores.append(CustomProxyClientCore(
            core=core,
            version=str(item.get('version') or ''),
            outbounds_template=outbound,
            do_base64_after=bool(item.get('do_base64_after')),
            template_slugs=list(item.get('template_slugs') or []),
            builtin_outbounds_template=outbound if builtin else '',
            override=not builtin and bool(outbound),
        ))


def sync_builtin_custom_proxy(row: CustomProxy, catalog: dict[str, Any]) -> bool:
    if not row.is_builtin:
        return False
    changed = False
    body = custom_proxy_catalog_body(catalog)

    for field, value in (
        ('alpns', list(body.get('alpns') or [])),
        ('download_alpns', list(body.get('download_alpns') or [])),
        ('custom_path', normalize_custom_path(body.get('custom_path'))),
        ('domain_modes', list(body.get('domain_modes') or [])),
    ):
        if getattr(row, field) != value:
            setattr(row, field, value)
            changed = True

    from hiddifypanel.models.custom_proxy import ServerCore, _parse_server_core
    server_core = _parse_server_core(body.get('server_core'))
    if row.server_core != server_core:
        row.server_core = server_core
        changed = True

    for field in ('server_tag', 'server_inbound_tcp_ports', 'server_inbound_udp_ports', 'server_template_slugs'):
        value = body.get(field)
        if getattr(row, field) != value:
            setattr(row, field, value)
            changed = True

    builtin_server = body.get('server_config') or ''
    if row.builtin_server_config != builtin_server:
        row.builtin_server_config = builtin_server
        changed = True
    if not row.server_override and row.server_config != builtin_server:
        row.server_config = builtin_server
        changed = True

    core_configs = list(body.get('client_cores') or [])
    if core_configs:
        _replace_client_core_rows(row, core_configs, builtin=True)
        changed = True

    mode_val = catalog.get('mode')
    if mode_val:
        from hiddifypanel.models.custom_proxy import _parse_mode, _parse_l7_proto
        mode = _parse_mode(mode_val)
        if row.mode != mode:
            row.mode = mode
            changed = True
        l7_proto = _parse_l7_proto(catalog.get('l7_proto')) if catalog.get('l7_proto') else None
        if row.l7_proto != l7_proto:
            row.l7_proto = l7_proto
            changed = True

    return changed


def effective_template_content(row) -> str:
    if not row.is_builtin:
        return row.content or ''
    if row.builtin_override and (row.content or '').strip():
        return row.content or ''
    return row.builtin_content or row.content or ''


def effective_base_config_content(row) -> str:
    if not row.is_builtin:
        return row.content or ''
    if row.builtin_override and (row.content or '').strip():
        return row.content or ''
    return row.builtin_content or row.content or ''


def sync_builtin_template(row, catalog: dict[str, Any]) -> bool:
    if not row.is_builtin:
        return False
    changed = False
    catalog_content = catalog.get('content') or ''
    if row.builtin_content != catalog_content:
        row.builtin_content = catalog_content
        changed = True
    for field in ('name', 'description'):
        val = catalog.get(field) or ''
        if getattr(row, field) != val:
            setattr(row, field, val)
            changed = True
    category = catalog.get('category')
    if category is not None and row.category != category:
        row.category = category
        changed = True
    if not row.builtin_override:
        effective = row.builtin_content or ''
        if row.content != effective:
            row.content = effective
            changed = True
    return changed


def sync_builtin_base_config(row, catalog: dict[str, Any]) -> bool:
    if not row.is_builtin:
        return False
    changed = False
    catalog_content = catalog.get('content') or ''
    if row.builtin_content != catalog_content:
        row.builtin_content = catalog_content
        changed = True
    for field in ('name', 'description'):
        val = catalog.get(field) or ''
        if getattr(row, field) != val:
            setattr(row, field, val)
            changed = True
    if not row.builtin_override:
        effective = row.builtin_content or ''
        if row.content != effective:
            row.content = effective
            changed = True
    return changed


def apply_builtin_override_template(row, *, override: bool) -> None:
    row.builtin_override = bool(override)
    if override:
        if not (row.content or '').strip():
            row.content = row.builtin_content or row.content or ''
    else:
        row.content = row.builtin_content or row.content or ''


def apply_builtin_override_base_config(row, *, override: bool) -> None:
    row.builtin_override = bool(override)
    if override:
        if not (row.content or '').strip():
            row.content = row.builtin_content or row.content or ''
    else:
        row.content = row.builtin_content or ''
