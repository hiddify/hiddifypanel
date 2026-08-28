from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

from loguru import logger
from pydantic import BaseModel

from hiddifypanel.database import db
from hiddifypanel.models.custom_proxy import (
    DEFAULT_SERVER_TEMPLATE_SLUG,
    DEFAULT_SUBLINK_TEMPLATE_SLUG,
    CustomProxy,
    ProxyTemplate,
    TemplateCategory,
    TemplateCore,
)
from hiddifypanel.models.proxy_base_config import BaseConfigSide, ProxyBaseConfig

from .catalog import (
    build_builtin_templates,
    clear_builtin_template_cache,
    get_builtin_base_configs,
    get_builtin_templates,
)
from .stale import (
    handle_stale_base_config,
    handle_stale_custom_proxy,
    handle_stale_template,
    prepare_repromotion_base_config,
    prepare_repromotion_template,
)
from .sync import (
    sync_builtin_base_config,
    sync_builtin_custom_proxy,
    sync_builtin_template,
)

RowT = TypeVar("RowT")


class SyncStats(BaseModel):
    child_id: int = 0
    templates_added: int = 0
    templates_updated: int = 0
    templates_removed: int = 0
    templates_demoted: int = 0
    templates_total: int = 0
    base_configs_refreshed: int = 0
    base_configs_removed: int = 0
    base_configs_demoted: int = 0
    custom_proxies_added: int = 0
    custom_proxies_updated: int = 0
    custom_proxies_removed: int = 0
    custom_proxies_demoted: int = 0
    builtin_templates: int = 0
    builtin_base_configs: int = 0
    builtin_custom_proxies: int = 0


def _apply_stale_actions(rows: Iterable[RowT], handler: Callable[[RowT], str]) -> tuple[int, int]:
    removed = demoted = 0
    for row in rows:
        action = handler(row)
        if action == "removed":
            removed += 1
        else:
            demoted += 1
    return removed, demoted


def _seed_default_proxy_shells(child_id: int = 0) -> None:
    from ..template_catalog.template_defaults import (
        default_server_inbound_template,
        default_sublink_link_template,
    )

    shells = [
        {
            "slug": DEFAULT_SERVER_TEMPLATE_SLUG,
            "core": TemplateCore.xray,
            "category": TemplateCategory.server_inbound,
            "name": "Default Xray server inbound",
            "description": "Default listen snippet for new custom proxies",
            "content": default_server_inbound_template(),
        },
        {
            "slug": DEFAULT_SUBLINK_TEMPLATE_SLUG,
            "core": TemplateCore.sublink,
            "category": TemplateCategory.client_outbound,
            "name": "Default sublink client",
            "description": "Default sublink URI template for new custom proxies",
            "content": default_sublink_link_template(),
        },
    ]
    for spec in shells:
        row = ProxyTemplate.query.filter(
            ProxyTemplate.child_id == child_id,
            ProxyTemplate.slug == spec["slug"],
        ).first()
        content = spec["content"] or ""
        if row:
            if row.builtin_content != content:
                row.builtin_content = content
            if not row.builtin_override:
                row.content = content
            continue
        db.session.add(
            ProxyTemplate(
                child_id=child_id,
                slug=spec["slug"],
                core=spec["core"],
                category=spec["category"],
                name=spec["name"],
                description=spec["description"],
                content=content,
                builtin_content=content,
                is_builtin=True,
            )
        )
    db.session.commit()


def sync_templates(child_id: int = 0) -> tuple[int, int, int, int, int]:
    """Sync proxy_templates/ fragments into ProxyTemplate rows (excludes presets and base shells)."""
    clear_builtin_template_cache()
    _seed_default_proxy_shells(child_id)

    templates = get_builtin_templates()
    disk_slugs = {tpl.slug for tpl in templates}
    added = updated = removed = demoted = 0

    for tpl in templates:
        row = ProxyTemplate.query.filter(
            ProxyTemplate.child_id == child_id,
            ProxyTemplate.slug == tpl.slug,
        ).first()
        if row:
            prepare_repromotion_template(row, tpl.content or "")
            if sync_builtin_template(row, tpl):
                updated += 1
            continue
        catalog_content = tpl.content or ""
        db.session.add(
            ProxyTemplate(
                child_id=child_id,
                slug=tpl.slug,
                core=tpl.core,
                category=tpl.category,
                name=tpl.name,
                description=tpl.description,
                content=catalog_content,
                builtin_content=catalog_content,
                builtin_override=False,
                is_builtin=True,
            )
        )
        added += 1

    exempt = {DEFAULT_SERVER_TEMPLATE_SLUG, DEFAULT_SUBLINK_TEMPLATE_SLUG}
    stale = (
        ProxyTemplate.query.filter(
            ProxyTemplate.child_id == child_id,
            ProxyTemplate.is_builtin.is_(True),
        )
        .filter(~ProxyTemplate.slug.in_(disk_slugs))
        .all()
    )
    removed, demoted = _apply_stale_actions(
        (row for row in stale if row.slug not in exempt),
        handle_stale_template,
    )

    if added or updated or removed or demoted:
        db.session.commit()

    logger.info(
        "Proxy templates synced: child_id={} added={} updated={} removed={} demoted={} total={}",
        child_id,
        added,
        updated,
        removed,
        demoted,
        len(templates),
    )
    return added, updated, removed, demoted, len(templates)


def sync_base_configs(child_id: int = 0, *, refresh_builtin: bool = True) -> tuple[int, int, int]:
    """Refresh builtin ProxyBaseConfig rows from {core}/{side}/base.j2 on disk."""
    clear_builtin_template_cache()
    configs = get_builtin_base_configs()
    disk_keys = {(cfg.core, cfg.side, cfg.version) for cfg in configs}
    refreshed = removed = demoted = 0

    for cfg in configs:
        side = BaseConfigSide(cfg.side)
        existing = ProxyBaseConfig.query.filter(
            ProxyBaseConfig.child_id == child_id,
            ProxyBaseConfig.side == side,
            ProxyBaseConfig.core == cfg.core,
            ProxyBaseConfig.version == cfg.version,
        ).first()
        catalog = {
            "core": cfg.core,
            "side": cfg.side,
            "version": cfg.version,
            "name": cfg.name,
            "description": cfg.description,
            "content": cfg.content,
        }
        if existing:
            if refresh_builtin:
                prepare_repromotion_base_config(existing, cfg.content or "")
                if sync_builtin_base_config(existing, catalog):
                    refreshed += 1
            continue
        db.session.add(
            ProxyBaseConfig(
                child_id=child_id,
                side=side,
                core=cfg.core,
                version=cfg.version,
                name=cfg.name,
                description=cfg.description,
                content=cfg.content,
                builtin_content=cfg.content,
                builtin_override=False,
                is_builtin=True,
                enable=True,
            )
        )
        refreshed += 1

    stale = ProxyBaseConfig.query.filter(
        ProxyBaseConfig.child_id == child_id,
        ProxyBaseConfig.is_builtin.is_(True),
    ).all()
    removed, demoted = _apply_stale_actions(
        (row for row in stale if (row.core, row.side.value if row.side else "", row.version or "") not in disk_keys),
        handle_stale_base_config,
    )

    if refreshed or removed or demoted:
        db.session.commit()

    logger.info(
        "Base configs synced: child_id={} refreshed={} removed={} demoted={} total={}",
        child_id,
        refreshed,
        removed,
        demoted,
        len(configs),
    )
    return refreshed, removed, demoted


def sync_custom_proxy_presets(child_id: int = 0) -> tuple[int, int, int, int]:
    """Sync programmatic custom-proxy presets with unified stale handling."""
    from hiddifypanel.models.custom_proxy import normalize_custom_path
    from ..template_catalog.custom_proxy_presets import iter_custom_proxy_presets

    presets = iter_custom_proxy_presets(child_id)
    presets_by_slug = {preset.slug: preset for preset in presets}
    disk_slugs = set(presets_by_slug)
    added = updated = removed = demoted = 0

    for preset in presets:
        slug = preset.slug
        row = CustomProxy.query.filter(CustomProxy.child_id == child_id, CustomProxy.slug == slug).first()
        if row:
            if row.mode != preset.mode:
                row.mode = preset.mode
            if not row.is_builtin:
                row.is_builtin = True
            if sync_builtin_custom_proxy(row, preset):
                updated += 1
            continue
        server = preset.server_config
        row = CustomProxy.add_or_update(
            child_id=child_id,
            commit=False,
            is_builtin=True,
            name=preset.name,
            slug=slug,
            enable=preset.enable,
            mode=preset.mode.value,
            proto=preset.proto,
            transport=preset.transport,
            tls_layer=preset.tls_layer,
            l7_reverse_proto=preset.l7_reverse_proto,
            download_tls_layer=preset.download_tls_layer,
            download_domain_modes=list(preset.download_domain_modes),
            categories=list(preset.categories),
            domain_modes=list(preset.domain_modes),
            custom_path=preset.custom_path,
            server_config={
                "core": server.core,
                "inbound_template": server.inbound_template,
                "template_slugs": list(server.template_slugs),
                "tag": server.tag,
                "inbound_tcp_ports": list(server.inbound_tcp_ports),
                "inbound_udp_ports": list(server.inbound_udp_ports),
                "sni_domains": list(server.sni_domains),
                "tcp_udp": preset.tcp_udp.value,
                "download_tcp_udp": (preset.download_tcp_udp.value if preset.download_tcp_udp else None),
            },
        )
        db.session.flush()
        sync_builtin_custom_proxy(row, preset)
        added += 1

    stale = (
        CustomProxy.query.filter(
            CustomProxy.child_id == child_id,
            CustomProxy.is_builtin.is_(True),
        )
        .filter(~CustomProxy.slug.in_(disk_slugs))
        .all()
    )
    removed, demoted = _apply_stale_actions(stale, handle_stale_custom_proxy)

    for row in CustomProxy.query.filter(CustomProxy.child_id == child_id).all():
        if row.slug in presets_by_slug and not row.is_builtin:
            row.is_builtin = True
        path = normalize_custom_path(row.custom_path)
        if row.custom_path != path:
            row.custom_path = path

    if added or updated or removed or demoted:
        db.session.commit()

    logger.info(
        "Custom proxy presets synced: child_id={} added={} updated={} removed={} demoted={} total={}",
        child_id,
        added,
        updated,
        removed,
        demoted,
        len(presets),
    )
    return added, updated, removed, demoted


def sync_all(child_id: int = 0, *, refresh_base_configs: bool = True) -> SyncStats:
    """Sync all builtin proxies, templates, and base configs from proxy_templates/."""
    logger.info("Syncing builtin proxy catalog for child_id={}…", child_id)
    tpl_added, tpl_updated, tpl_removed, tpl_demoted, tpl_total = sync_templates(child_id)
    base_refreshed, base_removed, base_demoted = sync_base_configs(
        child_id,
        refresh_builtin=refresh_base_configs,
    )
    cp_added, cp_updated, cp_removed, cp_demoted = sync_custom_proxy_presets(child_id)

    stats = SyncStats(
        child_id=child_id,
        templates_added=tpl_added,
        templates_updated=tpl_updated,
        templates_removed=tpl_removed,
        templates_demoted=tpl_demoted,
        templates_total=tpl_total,
        base_configs_refreshed=base_refreshed,
        base_configs_removed=base_removed,
        base_configs_demoted=base_demoted,
        custom_proxies_added=cp_added,
        custom_proxies_updated=cp_updated,
        custom_proxies_removed=cp_removed,
        custom_proxies_demoted=cp_demoted,
        builtin_templates=ProxyTemplate.query.filter(
            ProxyTemplate.child_id == child_id,
            ProxyTemplate.is_builtin.is_(True),
        ).count(),
        builtin_base_configs=ProxyBaseConfig.query.filter(
            ProxyBaseConfig.child_id == child_id,
            ProxyBaseConfig.is_builtin.is_(True),
        ).count(),
        builtin_custom_proxies=CustomProxy.query.filter(
            CustomProxy.child_id == child_id,
            CustomProxy.is_builtin.is_(True),
        ).count(),
    )
    logger.info(
        "Builtin catalog synced for child_id={}: {} templates, {} base configs, {} custom proxies",
        child_id,
        stats.builtin_templates,
        stats.builtin_base_configs,
        stats.builtin_custom_proxies,
    )
    return stats


def seed_proxy_catalog(child_id: int = 0, *, refresh_builtin_base_configs: bool = False) -> None:
    """Preload template catalog: fragments, presets, custom proxies, base configs."""
    from ..template_catalog.custom_proxy_presets import iter_custom_proxy_presets

    logger.info("Seeding proxy catalog for child_id={}…", child_id)
    sync_templates(child_id)
    sync_base_configs(child_id, refresh_builtin=refresh_builtin_base_configs)
    logger.info(
        "Proxy catalog done for child_id={}: {} templates, {} custom-proxy presets",
        child_id,
        len(build_builtin_templates()),
        len(iter_custom_proxy_presets()),
    )
