from __future__ import annotations

import copy
from typing import Any

from hiddifypanel.database import db
from hiddifypanel.models.custom_proxy import (
    CustomProxy,
    CustomProxyClientCore,
    normalize_custom_path,
)

from ..template_catalog.custom_proxy_builtin import (
    catalog_body_to_builtin_fields,
    client_override_key,
    ensure_builtin_migrated,
    sync_catalog_field,
)
from .catalog import BuiltinTemplateRecord


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
        'server_config': server.get('inbound_template') or '',
        'client_cores': copy.deepcopy((preset.get('client_config') or {}).get('core_configs') or []),
    }


def custom_proxy_body_from_dict(data: dict[str, Any]) -> dict[str, Any]:
    from hiddifypanel.proxy_v3.custom_proxy_ports import normalize_port_list

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
        'server_config': inbound_template,
        'client_cores': copy.deepcopy((data.get('client_config') or {}).get('core_configs') or []),
    }


def effective_custom_proxy_body(row: CustomProxy) -> dict[str, Any]:
    if not row.is_builtin:
        return custom_proxy_body_from_dict(row.to_dict())
    return row.to_dict()


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
    from ..template_catalog.custom_proxy_builtin import set_field_override

    set_field_override(row, 'server_config', override)


def _client_core_slug(item: dict[str, Any]) -> str:
    core = str(item.get('core') or '').strip()
    return str(item.get('slug') or f'client-{core}')


def _replace_client_core_rows(row: CustomProxy, core_configs: list[dict[str, Any]], *, builtin: bool) -> None:
    from hiddifypanel.models.custom_proxy import _parse_client_core

    incoming: dict[str, dict[str, Any]] = {}
    for item in core_configs:
        incoming[_client_core_slug(item)] = item

    for existing in list(row.client_cores):
        slug = existing.slug or f'client-{existing.core.value}'
        if slug not in incoming and not existing.is_builtin:
            db.session.delete(existing)
    db.session.flush()

    by_slug = {cc.slug or f'client-{cc.core.value}': cc for cc in row.client_cores}
    for slug, item in incoming.items():
        core = _parse_client_core(item.get('core'))
        outbound = _client_template(item)
        existing = by_slug.get(slug)
        if existing:
            existing.core = core
            existing.version = str(item.get('version') or '')
            if builtin:
                existing.is_builtin = True
                existing.builtin_outbounds_template = outbound
                if not existing.override:
                    existing.outbounds_template = outbound
            else:
                existing.outbounds_template = outbound
                existing.override = bool(outbound)
            continue
        row.client_cores.append(CustomProxyClientCore(
            core=core,
            version=str(item.get('version') or ''),
            slug=slug,
            is_builtin=builtin,
            outbounds_template=outbound,
            builtin_outbounds_template=outbound if builtin else '',
            override=not builtin and bool(outbound),
        ))


def sync_builtin_custom_proxy(row: CustomProxy, catalog: dict[str, Any]) -> bool:
    if not row.is_builtin:
        return False
    changed = False
    body = custom_proxy_catalog_body(catalog)
    ensure_builtin_migrated(row)

    builtin_fields = catalog_body_to_builtin_fields(body)
    for key, value in builtin_fields.items():
        if sync_catalog_field(row, key, value):
            changed = True

    from hiddifypanel.models.custom_proxy import _parse_l7_proto, _parse_mode, _parse_proto, _parse_server_core

    server_core = _parse_server_core(body.get('server_core'))
    if row.server_core != server_core:
        row.server_core = server_core
        changed = True

    core_configs = list(body.get('client_cores') or [])
    if core_configs:
        _replace_client_core_rows(row, core_configs, builtin=True)
        for item in core_configs:
            core = str(item.get('core') or '').strip()
            if core and sync_catalog_field(row, client_override_key(core), _client_template(item)):
                changed = True
        changed = True

    mode_val = catalog.get('mode')
    if mode_val:
        mode = _parse_mode(mode_val)
        if row.mode != mode:
            row.mode = mode
            changed = True
        proto_val = catalog.get('proto')
        if proto_val:
            proto = _parse_proto(proto_val)
            if row.proto != proto:
                row.proto = proto
                changed = True
        l7_proto = _parse_l7_proto(catalog.get('l7_proto')) if catalog.get('l7_proto') else None
        if row.l7_proto != l7_proto:
            row.l7_proto = l7_proto
            changed = True

    row.builtin_server_config = str((row.builtin or {}).get('server_config') or '')
    row.server_override = bool((row.builtin_overrides or {}).get('server_config'))
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


def sync_builtin_template(row, catalog: BuiltinTemplateRecord | dict[str, Any]) -> bool:
    if not row.is_builtin:
        return False
    if isinstance(catalog, BuiltinTemplateRecord):
        catalog_data = catalog.model_dump()
    else:
        catalog_data = catalog
    changed = False
    catalog_content = catalog_data.get('content') or ''
    if row.builtin_content != catalog_content:
        row.builtin_content = catalog_content
        changed = True
    for field in ('name', 'description'):
        val = catalog_data.get(field) or ''
        if getattr(row, field) != val:
            setattr(row, field, val)
            changed = True
    category = catalog_data.get('category')
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
        row.content = row.builtin_content or row.content or ''
