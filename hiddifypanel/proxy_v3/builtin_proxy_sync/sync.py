from __future__ import annotations

from hiddifypanel.database import db
from hiddifypanel.models.custom_proxy import (
    CustomProxy,
    CustomProxyClientCore,
    normalize_custom_path,
    _parse_l7_reverse_proto,
    _parse_proto,
    _parse_server_core,
    _parse_tcp_udp,
    _parse_tls_layer,
    _parse_transport,
)

from ..template_catalog.custom_proxy_builtin import (
    catalog_fields_from_snapshot,
    client_override_key,
    ensure_builtin_migrated,
    sync_catalog_field,
)
from .catalog import BuiltinTemplateRecord
from .types import ClientCoreSnapshot, CustomProxyPreset, CustomProxySnapshot


def snapshot_from_row(row: CustomProxy) -> CustomProxySnapshot:
    return CustomProxySnapshot.from_row(row)


def has_custom_proxy_overrides(row: CustomProxy) -> bool:
    ensure_builtin_migrated(row)
    if row.server_override or any((row.builtin_overrides or {}).values()):
        return True
    return any(cc.override for cc in row.client_cores)


def apply_custom_proxy_general(row: CustomProxy, body: dict) -> None:
    if "custom_path" in body:
        row.custom_path = normalize_custom_path(body.get("custom_path"))
    if "domain_modes" in body:
        row.domain_modes = list(body.get("domain_modes") or [])
    if "transport" in body and body.get("transport") not in (None, ""):
        row.transport = _parse_transport(body.get("transport"))
    if "tls_layer" in body and body.get("tls_layer") not in (None, ""):
        row.tls_layer = _parse_tls_layer(body.get("tls_layer"))
    if "l7_reverse_proto" in body and body.get("l7_reverse_proto") not in (None, ""):
        row.l7_reverse_proto = _parse_l7_reverse_proto(body.get("l7_reverse_proto"))
    elif "l7_proto" in body and body.get("l7_proto") not in (None, ""):
        row.l7_reverse_proto = _parse_l7_reverse_proto(body.get("l7_proto"))
    from hiddifypanel.models.custom_proxy import _apply_download_xhttp_fields

    _apply_download_xhttp_fields(row, body)


def apply_server_override(row: CustomProxy, *, override: bool) -> None:
    from ..template_catalog.custom_proxy_builtin import set_field_override

    set_field_override(row, "server_config", override)


def _replace_client_core_rows(row: CustomProxy, cores: tuple[ClientCoreSnapshot, ...], *, builtin: bool) -> None:
    from hiddifypanel.models.custom_proxy import _parse_client_core

    incoming = {cc.slug: cc for cc in cores}
    for existing in list(row.client_cores):
        slug = existing.slug or f"client-{existing.core.value}"
        if slug not in incoming and not existing.is_builtin:
            db.session.delete(existing)
    db.session.flush()

    by_slug = {cc.slug or f"client-{cc.core.value}": cc for cc in row.client_cores}
    for slug, item in incoming.items():
        core = _parse_client_core(item.core)
        existing = by_slug.get(slug)
        if existing:
            existing.core = core
            existing.version = item.version
            if builtin:
                existing.is_builtin = True
                existing.builtin_outbounds_template = item.outbounds_template
                if not existing.override:
                    existing.outbounds_template = item.outbounds_template
            else:
                existing.outbounds_template = item.outbounds_template
                existing.override = bool(item.outbounds_template)
            continue
        row.client_cores.append(
            CustomProxyClientCore(
                core=core,
                version=item.version,
                slug=slug,
                is_builtin=builtin,
                outbounds_template=item.outbounds_template,
                builtin_outbounds_template=item.outbounds_template if builtin else "",
                override=not builtin and bool(item.outbounds_template),
            )
        )


def sync_builtin_custom_proxy(row: CustomProxy, catalog: CustomProxyPreset) -> bool:
    if not row.is_builtin:
        return False
    ensure_builtin_migrated(row)
    snapshot = catalog.snapshot()
    changed = False

    proto = _parse_proto(catalog.proto)
    if row.proto != proto:
        row.proto = proto
        changed = True
    if snapshot.transport:
        transport = _parse_transport(snapshot.transport)
        if row.transport != transport:
            row.transport = transport
            changed = True
    if snapshot.tls_layer:
        tls_layer = _parse_tls_layer(snapshot.tls_layer)
        if row.tls_layer != tls_layer:
            row.tls_layer = tls_layer
            changed = True
    l7_reverse = _parse_l7_reverse_proto(snapshot.l7_reverse_proto) if snapshot.l7_reverse_proto else None
    if row.l7_reverse_proto != l7_reverse:
        row.l7_reverse_proto = l7_reverse
        changed = True

    tcp_udp = _parse_tcp_udp(snapshot.server_inbound_tcp_udp)
    if row.server_inbound_tcp_udp != tcp_udp:
        row.server_inbound_tcp_udp = tcp_udp
        changed = True
    download_tcp_udp = (
        _parse_tcp_udp(snapshot.server_inbound_download_tcp_udp)
        if snapshot.server_inbound_download_tcp_udp
        else None
    )
    if row.server_inbound_download_tcp_udp != download_tcp_udp:
        row.server_inbound_download_tcp_udp = download_tcp_udp
        changed = True

    for key, value in catalog_fields_from_snapshot(snapshot).items():
        if sync_catalog_field(row, key, value):
            changed = True

    server_core = _parse_server_core(snapshot.server_core)
    if row.server_core != server_core:
        row.server_core = server_core
        changed = True

    if snapshot.client_cores:
        _replace_client_core_rows(row, snapshot.client_cores, builtin=True)
        for item in snapshot.client_cores:
            if item.core and sync_catalog_field(row, client_override_key(item.core), item.outbounds_template):
                changed = True
        changed = True
    else:
        removed_any = False
        for existing in list(row.client_cores):
            if existing.is_builtin and not existing.override:
                db.session.delete(existing)
                removed_any = True
        if removed_any:
            changed = True

    if row.mode != catalog.mode:
        row.mode = catalog.mode
        changed = True

    row.builtin_server_config = str((row.builtin or {}).get("server_config") or "")
    row.server_override = bool((row.builtin_overrides or {}).get("server_config"))
    return changed


def effective_template_content(row) -> str:
    if not row.is_builtin:
        return row.content or ""
    if row.builtin_override and (row.content or "").strip():
        return row.content or ""
    return row.builtin_content or row.content or ""


def effective_base_config_content(row) -> str:
    if not row.is_builtin:
        return row.content or ""
    if row.builtin_override and (row.content or "").strip():
        return row.content or ""
    return row.builtin_content or row.content or ""


def sync_builtin_template(row, catalog: BuiltinTemplateRecord | dict) -> bool:
    if not row.is_builtin:
        return False
    if isinstance(catalog, BuiltinTemplateRecord):
        catalog_data = catalog.model_dump() if hasattr(catalog, "model_dump") else catalog.dict()
    else:
        catalog_data = catalog
    changed = False
    catalog_content = catalog_data.get("content") or ""
    if row.builtin_content != catalog_content:
        row.builtin_content = catalog_content
        changed = True
    for field in ("name", "description"):
        val = catalog_data.get(field) or ""
        if getattr(row, field) != val:
            setattr(row, field, val)
            changed = True
    category = catalog_data.get("category")
    if category is not None and row.category != category:
        row.category = category
        changed = True
    if not row.builtin_override:
        effective = row.builtin_content or ""
        if row.content != effective:
            row.content = effective
            changed = True
    return changed


def sync_builtin_base_config(row, catalog: dict) -> bool:
    if not row.is_builtin:
        return False
    changed = False
    catalog_content = catalog.get("content") or ""
    if row.builtin_content != catalog_content:
        row.builtin_content = catalog_content
        changed = True
    for field in ("name", "description"):
        val = catalog.get(field) or ""
        if getattr(row, field) != val:
            setattr(row, field, val)
            changed = True
    if not row.builtin_override:
        effective = row.builtin_content or ""
        if row.content != effective:
            row.content = effective
            changed = True
    return changed


def apply_builtin_override_template(row, *, override: bool) -> None:
    row.builtin_override = bool(override)
    if override:
        if not (row.content or "").strip():
            row.content = row.builtin_content or row.content or ""
    else:
        row.content = row.builtin_content or row.content or ""


def apply_builtin_override_base_config(row, *, override: bool) -> None:
    row.builtin_override = bool(override)
    if override:
        if not (row.content or "").strip():
            row.content = row.builtin_content or row.content or ""
    else:
        row.content = row.builtin_content or row.content or ""
