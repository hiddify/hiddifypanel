from __future__ import annotations

from typing import Any

from loguru import logger
from pydantic import BaseModel

from hiddifypanel.database import db
from hiddifypanel.models.custom_proxy import (
    DEFAULT_SERVER_TEMPLATE_SLUG,
    DEFAULT_SUBLINK_TEMPLATE_SLUG,
    ProxyTemplate,
    TemplateCategory,
    TemplateCore,
)
from hiddifypanel.models.proxy_base_config import (
    BUILTIN_BASE_CONFIGS,
    BaseConfigSide,
    ProxyBaseConfig,
    default_base_content,
)

from .catalog import (
    BuiltinTemplateRecord,
    build_builtin_templates,
    clear_builtin_template_cache,
    discover_builtin_templates,
    get_builtin_templates,
)
from .discovery import iter_base_config_files
from .paths import TEMPLATES_ROOT
from .sync import (
    apply_builtin_override_base_config,
    apply_builtin_override_template,
    apply_custom_proxy_general,
    apply_server_override,
    custom_proxy_body_from_dict,
    custom_proxy_catalog_body,
    effective_base_config_content,
    effective_custom_proxy_body,
    effective_template_content,
    sync_builtin_base_config,
    sync_builtin_custom_proxy,
    sync_builtin_template,
)

__all__ = [
    'TEMPLATES_ROOT',
    'BuiltinTemplateRecord',
    'SyncStats',
    'apply_builtin_override_base_config',
    'apply_builtin_override_template',
    'apply_custom_proxy_general',
    'apply_server_override',
    'build_builtin_templates',
    'clear_builtin_template_cache',
    'custom_proxy_body_from_dict',
    'custom_proxy_catalog_body',
    'discover_builtin_templates',
    'effective_base_config_content',
    'effective_custom_proxy_body',
    'effective_template_content',
    'get_builtin_templates',
    'seed_proxy_catalog',
    'sync_all',
    'sync_base_configs',
    'sync_builtin_template',
    'sync_builtin_base_config',
    'sync_builtin_custom_proxy',
    'sync_custom_proxy_presets',
    'sync_templates',
]


class SyncStats(BaseModel):
    child_id: int = 0
    templates_added: int = 0
    templates_updated: int = 0
    templates_removed: int = 0
    templates_total: int = 0
    base_configs_refreshed: int = 0
    builtin_templates: int = 0
    builtin_base_configs: int = 0
    builtin_custom_proxies: int = 0


def _seed_default_proxy_shells(child_id: int = 0) -> None:
    from ..template_catalog.template_defaults import (
        default_server_inbound_template,
        default_sublink_link_template,
    )

    shells = [
        {
            'slug': DEFAULT_SERVER_TEMPLATE_SLUG,
            'core': TemplateCore.xray,
            'category': TemplateCategory.server_inbound,
            'name': 'Default Xray server inbound',
            'description': 'Default listen snippet for new custom proxies',
            'content': default_server_inbound_template(),
        },
        {
            'slug': DEFAULT_SUBLINK_TEMPLATE_SLUG,
            'core': TemplateCore.sublink,
            'category': TemplateCategory.client_outbound,
            'name': 'Default sublink client',
            'description': 'Default sublink URI template for new custom proxies',
            'content': default_sublink_link_template(),
        },
    ]
    for spec in shells:
        row = ProxyTemplate.query.filter(
            ProxyTemplate.child_id == child_id,
            ProxyTemplate.slug == spec['slug'],
        ).first()
        content = spec['content'] or ''
        if row:
            if row.builtin_content != content:
                row.builtin_content = content
            if not row.builtin_override:
                row.content = content
            continue
        db.session.add(
            ProxyTemplate(
                child_id=child_id,
                slug=spec['slug'],
                core=spec['core'],
                category=spec['category'],
                name=spec['name'],
                description=spec['description'],
                content=content,
                builtin_content=content,
                is_builtin=True,
            )
        )
    db.session.commit()


def sync_templates(child_id: int = 0) -> tuple[int, int, int, int]:
    """Sync proxy_templates/ fragments into ProxyTemplate rows (excludes presets and base.j2)."""
    clear_builtin_template_cache()
    _seed_default_proxy_shells(child_id)

    templates = get_builtin_templates()
    disk_slugs = {tpl.slug for tpl in templates}
    added = updated = removed = 0

    for tpl in templates:
        row = ProxyTemplate.query.filter(
            ProxyTemplate.child_id == child_id,
            ProxyTemplate.slug == tpl.slug,
        ).first()
        if row:
            if not row.is_builtin:
                row.is_builtin = True
            if sync_builtin_template(row, tpl):
                updated += 1
            continue
        catalog_content = tpl.content or ''
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

    stale = (
        ProxyTemplate.query.filter(
            ProxyTemplate.child_id == child_id,
            ProxyTemplate.is_builtin.is_(True),
        )
        .filter(~ProxyTemplate.slug.in_(disk_slugs))
        .all()
    )
    for row in stale:
        if row.slug in (DEFAULT_SERVER_TEMPLATE_SLUG, DEFAULT_SUBLINK_TEMPLATE_SLUG):
            continue
        db.session.delete(row)
        removed += 1

    if added or updated or removed:
        db.session.commit()

    logger.info(
        'Proxy templates synced: child_id={} added={} updated={} removed={} total={}',
        child_id, added, updated, removed, len(templates),
    )
    return added, updated, removed, len(templates)


def sync_base_configs(child_id: int = 0, *, refresh_builtin: bool = True) -> int:
    """Refresh builtin ProxyBaseConfig rows from {core}/{client|server}/base.j2 on disk."""
    refreshed = 0
    for spec in BUILTIN_BASE_CONFIGS:
        side = spec['side']
        core = spec['core']
        version = spec['version']
        existing = ProxyBaseConfig.query.filter(
            ProxyBaseConfig.child_id == child_id,
            ProxyBaseConfig.side == side,
            ProxyBaseConfig.core == core,
            ProxyBaseConfig.version == version,
        ).first()
        catalog_content = default_base_content(side.value, core)
        catalog = {**spec, 'content': catalog_content, 'side': side.value}
        if existing:
            if refresh_builtin and existing.is_builtin:
                if sync_builtin_base_config(existing, catalog):
                    refreshed += 1
            continue
        db.session.add(ProxyBaseConfig(
            child_id=child_id,
            side=side,
            core=core,
            version=version,
            name=spec['name'],
            description=spec['description'],
            content=catalog_content,
            builtin_content=catalog_content,
            builtin_override=False,
            is_builtin=True,
            enable=True,
        ))
        refreshed += 1
    db.session.commit()
    return refreshed


def sync_custom_proxy_presets(child_id: int = 0) -> None:
    from ..template_catalog.custom_proxy_presets import seed_custom_proxy_presets

    seed_custom_proxy_presets(child_id)


def sync_all(child_id: int = 0, *, refresh_base_configs: bool = True) -> SyncStats:
    """Sync all builtin proxies, templates, and base configs from proxy_templates/."""
    from hiddifypanel.models.custom_proxy import CustomProxy

    logger.info('Syncing builtin proxy catalog for child_id={}…', child_id)
    added, updated, removed, total = sync_templates(child_id)
    base_refreshed = sync_base_configs(child_id, refresh_builtin=refresh_base_configs)
    sync_custom_proxy_presets(child_id)

    stats = SyncStats(
        child_id=child_id,
        templates_added=added,
        templates_updated=updated,
        templates_removed=removed,
        templates_total=total,
        base_configs_refreshed=base_refreshed,
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
        'Builtin catalog synced for child_id={}: {} templates, {} base configs, {} custom proxies',
        child_id,
        stats.builtin_templates,
        stats.builtin_base_configs,
        stats.builtin_custom_proxies,
    )
    return stats


def seed_proxy_catalog(child_id: int = 0, *, refresh_builtin_base_configs: bool = False) -> None:
    """Preload template catalog: fragments, presets, custom proxies, base configs."""
    from ..template_catalog.custom_proxy_presets import iter_custom_proxy_presets

    logger.info('Seeding proxy catalog for child_id={}…', child_id)
    sync_templates(child_id)
    sync_base_configs(child_id, refresh_builtin=refresh_builtin_base_configs)
    logger.info(
        'Proxy catalog done for child_id={}: {} templates, {} custom-proxy presets',
        child_id,
        len(build_builtin_templates()),
        len(iter_custom_proxy_presets()),
    )
