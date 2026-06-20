from __future__ import annotations

from typing import Any

from loguru import logger


def sync_builtin_catalog(child_id: int = 0) -> dict[str, Any]:
    """Sync builtin templates, base configs, and custom-proxy presets from disk."""
    from hiddifypanel.models.custom_proxy import CustomProxy, ProxyTemplate, seed_proxy_templates
    from hiddifypanel.models.proxy_base_config import ProxyBaseConfig, seed_proxy_base_configs

    logger.info('Syncing builtin proxy catalog for child_id={}…', child_id)
    seed_proxy_templates(child_id)
    seed_proxy_base_configs(child_id, refresh_builtin=True)

    stats = {
        'child_id': child_id,
        'builtin_templates': ProxyTemplate.query.filter(
            ProxyTemplate.child_id == child_id,
            ProxyTemplate.is_builtin.is_(True),
        ).count(),
        'builtin_base_configs': ProxyBaseConfig.query.filter(
            ProxyBaseConfig.child_id == child_id,
            ProxyBaseConfig.is_builtin.is_(True),
        ).count(),
        'builtin_custom_proxies': CustomProxy.query.filter(
            CustomProxy.child_id == child_id,
            CustomProxy.is_builtin.is_(True),
        ).count(),
    }
    logger.info(
        'Builtin catalog synced for child_id={}: {} templates, {} base configs, {} custom proxies',
        child_id,
        stats['builtin_templates'],
        stats['builtin_base_configs'],
        stats['builtin_custom_proxies'],
    )
    return stats


def seed_proxy_catalog(child_id: int = 0, *, refresh_builtin_base_configs: bool = False) -> None:
    """Preload template catalog: fragments, presets, custom proxies, base configs."""
    from hiddifypanel.models.custom_proxy import seed_proxy_templates
    from hiddifypanel.models.proxy_base_config import seed_proxy_base_configs
    from hiddifypanel.panel.template_catalog.builtin_templates import build_builtin_templates
    from hiddifypanel.panel.template_catalog.custom_proxy_presets import iter_custom_proxy_presets

    logger.info('Seeding proxy catalog for child_id={}…', child_id)
    seed_proxy_templates(child_id)
    seed_proxy_base_configs(child_id, refresh_builtin=refresh_builtin_base_configs)
    logger.info(
        'Proxy catalog done for child_id={}: {} templates, {} custom-proxy presets',
        child_id,
        len(build_builtin_templates()),
        len(iter_custom_proxy_presets()),
    )
