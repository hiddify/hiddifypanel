from __future__ import annotations

import copy
from typing import Any

from hiddifypanel.models.custom_proxy import CustomProxy, CustomProxyClientCore

GENERAL_OVERRIDE_FIELDS: tuple[str, ...] = (
    'alpns',
    'download_alpns',
    'custom_path',
    'domain_modes',
    'l7_proto',
)

SERVER_OVERRIDE_FIELDS: tuple[str, ...] = (
    'server_core',
    'server_tag',
    'server_inbound_tcp_ports',
    'server_inbound_udp_ports',
    'server_config',
)


def client_override_key(core: str) -> str:
    return f'client:{(core or "").strip()}'


def _builtin_dict(row: CustomProxy) -> dict[str, Any]:
    return dict(row.builtin or {})


def _overrides_dict(row: CustomProxy) -> dict[str, bool]:
    return {str(k): bool(v) for k, v in (row.builtin_overrides or {}).items()}


def is_field_overridden(row: CustomProxy, key: str) -> bool:
    return _overrides_dict(row).get(key, False)


def builtin_value(row: CustomProxy, key: str, default: Any = None) -> Any:
    builtin = _builtin_dict(row)
    if key in builtin:
        return builtin[key]
    return default


def ensure_builtin_migrated(row: CustomProxy) -> None:
    """Populate builtin / builtin_overrides from legacy columns once."""
    builtin = _builtin_dict(row)
    overrides = _overrides_dict(row)
    changed = False

    if 'server_config' not in builtin and (row.builtin_server_config or row.server_config):
        builtin['server_config'] = row.builtin_server_config or row.server_config or ''
        changed = True
    if row.server_override and not overrides.get('server_config'):
        overrides['server_config'] = True
        changed = True

    for field in GENERAL_OVERRIDE_FIELDS + SERVER_OVERRIDE_FIELDS:
        if field == 'server_config':
            continue
        if field not in builtin:
            val = getattr(row, field, None)
            if field == 'server_core' and val is not None:
                builtin[field] = val.value if hasattr(val, 'value') else str(val)
                changed = True
            elif val is not None:
                builtin[field] = copy.deepcopy(val)
                changed = True

    for cc in row.client_cores:
        key = client_override_key(cc.core.value if cc.core else '')
        if key not in builtin:
            builtin[key] = cc.builtin_outbounds_template or cc.outbounds_template or ''
            changed = True
        if cc.override and not overrides.get(key):
            overrides[key] = True
            changed = True

    if changed:
        row.builtin = builtin
        row.builtin_overrides = overrides


def _set_builtin(row: CustomProxy, key: str, value: Any) -> None:
    builtin = _builtin_dict(row)
    builtin[key] = copy.deepcopy(value)
    row.builtin = builtin


def _set_override_flag(row: CustomProxy, key: str, enabled: bool) -> None:
    overrides = _overrides_dict(row)
    if enabled:
        overrides[key] = True
    else:
        overrides.pop(key, None)
    row.builtin_overrides = overrides


def _apply_live(row: CustomProxy, key: str, value: Any) -> None:
    from hiddifypanel.models.custom_proxy import ServerCore, _parse_server_core

    if key == 'server_config':
        row.server_config = str(value or '')
        return
    if key == 'server_core':
        row.server_core = _parse_server_core(value)
        return
    if key == 'l7_proto':
        from hiddifypanel.models.custom_proxy import _parse_l7_proto

        row.l7_proto = _parse_l7_proto(value) if value else None
        return
    if key.startswith('client:'):
        core_name = key.split(':', 1)[1]
        from hiddifypanel.models.custom_proxy import _parse_client_core

        core = _parse_client_core(core_name)
        cc = next((r for r in row.client_cores if r.core == core), None)
        if cc:
            cc.outbounds_template = str(value or '')
        return
    if hasattr(row, key):
        setattr(row, key, copy.deepcopy(value))


def effective_field(row: CustomProxy, key: str, *, default: Any = None) -> Any:
    ensure_builtin_migrated(row)
    if is_field_overridden(row, key):
        return _live_value(row, key, default=default)
    return builtin_value(row, key, default=default)


def _live_value(row: CustomProxy, key: str, *, default: Any = None) -> Any:
    if key == 'server_config':
        return row.server_config or default
    if key == 'server_core':
        return row.server_core.value if row.server_core else default
    if key.startswith('client:'):
        core_name = key.split(':', 1)[1]
        from hiddifypanel.models.custom_proxy import _parse_client_core

        core = _parse_client_core(core_name)
        cc = next((r for r in row.client_cores if r.core == core), None)
        return (cc.outbounds_template if cc else None) or default
    return getattr(row, key, default)


def set_field_override(row: CustomProxy, key: str, enabled: bool) -> None:
    ensure_builtin_migrated(row)
    if enabled:
        if key not in (row.builtin or {}):
            _set_builtin(row, key, _live_value(row, key))
        _set_override_flag(row, key, True)
        if key == 'server_config':
            row.server_override = True
        elif key.startswith('client:'):
            core_name = key.split(':', 1)[1]
            from hiddifypanel.models.custom_proxy import _parse_client_core

            core = _parse_client_core(core_name)
            cc = next((r for r in row.client_cores if r.core == core), None)
            if cc:
                cc.override = True
    else:
        catalog = builtin_value(row, key)
        if catalog is not None:
            _apply_live(row, key, catalog)
        _set_override_flag(row, key, False)
        if key == 'server_config':
            row.server_override = False
        elif key.startswith('client:'):
            core_name = key.split(':', 1)[1]
            from hiddifypanel.models.custom_proxy import _parse_client_core

            core = _parse_client_core(core_name)
            cc = next((r for r in row.client_cores if r.core == core), None)
            if cc:
                cc.override = False


def sync_catalog_field(row: CustomProxy, key: str, catalog_value: Any) -> bool:
    ensure_builtin_migrated(row)
    changed = False
    if builtin_value(row, key) != catalog_value:
        _set_builtin(row, key, catalog_value)
        changed = True
    if not is_field_overridden(row, key):
        if _live_value(row, key) != catalog_value:
            _apply_live(row, key, catalog_value)
            changed = True
    return changed


def builtin_payload(row: CustomProxy) -> dict[str, Any]:
    ensure_builtin_migrated(row)
    return copy.deepcopy(row.builtin or {})


def overrides_payload(row: CustomProxy) -> dict[str, bool]:
    ensure_builtin_migrated(row)
    return copy.deepcopy(row.builtin_overrides or {})


def catalog_body_to_builtin_fields(body: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for field in GENERAL_OVERRIDE_FIELDS:
        if field in body:
            out[field] = copy.deepcopy(body[field])
    for field in SERVER_OVERRIDE_FIELDS:
        if field in body:
            out[field] = copy.deepcopy(body[field])
    for item in body.get('client_cores') or []:
        core = str(item.get('core') or '').strip()
        if core:
            out[client_override_key(core)] = str(
                item.get('outbounds_template') or item.get('link_template') or ''
            )
    return out
