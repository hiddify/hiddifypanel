from __future__ import annotations

import copy
import re
from typing import Any

from hiddifypanel.database import db
from hiddifypanel.models import ProxyTemplate

INCLUDE_RE = re.compile(r"\{%-?\s*include\s+['\"]([^'\"]+)['\"]")
INCLUDE_PATH_RE = re.compile(r"include_path\s*\(\s*(?:\w+\s*,\s*)?['\"]([^'\"]+)['\"]")

BUNDLE_VERSION = 1


def _referenced_slugs_from_text(text: str) -> set[str]:
    found: set[str] = set()
    found.update(INCLUDE_RE.findall(text or ''))
    found.update(INCLUDE_PATH_RE.findall(text or ''))
    return found


def collect_template_slugs_from_proxy(proxy: dict[str, Any]) -> list[str]:
    found: set[str] = set()
    server = proxy.get('server_config') or {}
    for slug in server.get('template_slugs') or []:
        if slug:
            found.add(str(slug))
    inbound = server.get('inbound_template') or ''
    found.update(_referenced_slugs_from_text(inbound))

    client = proxy.get('client_config') or {}
    for cfg in client.get('core_configs') or []:
        for slug in cfg.get('template_slugs') or []:
            if slug:
                found.add(str(slug))
        if cfg.get('core') == 'sublink':
            found.update(_referenced_slugs_from_text(
                cfg.get('outbounds_template') or cfg.get('link_template') or ''
            ))
        else:
            found.update(_referenced_slugs_from_text(cfg.get('outbounds_template') or ''))
    return sorted(found)


def collect_template_slugs_from_base_config(config: dict[str, Any]) -> list[str]:
    found: set[str] = set()
    for slug in config.get('template_slugs') or []:
        if slug:
            found.add(str(slug))
    found.update(_referenced_slugs_from_text(config.get('content') or ''))
    return sorted(found)


def replace_include_slugs(text: str, slug_map: dict[str, str]) -> str:
    if not text or not slug_map:
        return text
    result = text
    for old, new in slug_map.items():
        if old == new:
            continue
        result = result.replace(f"include '{old}'", f"include '{new}'")
        result = result.replace(f'include "{old}"', f'include "{new}"')
    return result


def remap_proxy_template_slugs(proxy: dict[str, Any], slug_map: dict[str, str]) -> dict[str, Any]:
    if not slug_map:
        return proxy
    out = copy.deepcopy(proxy)
    server = out.setdefault('server_config', {})
    if server.get('template_slugs'):
        server['template_slugs'] = [slug_map.get(s, s) for s in server['template_slugs']]
    server['inbound_template'] = replace_include_slugs(server.get('inbound_template') or '', slug_map)

    client = out.get('client_config') or {}
    out['client_config'] = client
    for cfg in client.get('core_configs') or []:
        if cfg.get('template_slugs'):
            cfg['template_slugs'] = [slug_map.get(s, s) for s in cfg['template_slugs']]
        legacy = cfg.get('link_template')
        if legacy and not cfg.get('outbounds_template'):
            cfg['outbounds_template'] = legacy
            cfg.pop('link_template', None)
        cfg['outbounds_template'] = replace_include_slugs(cfg.get('outbounds_template') or '', slug_map)
    return out


def remap_base_config_template_slugs(config: dict[str, Any], slug_map: dict[str, str]) -> dict[str, Any]:
    if not slug_map:
        return config
    out = copy.deepcopy(config)
    if out.get('template_slugs'):
        out['template_slugs'] = [slug_map.get(s, s) for s in out['template_slugs']]
    out['content'] = replace_include_slugs(out.get('content') or '', slug_map)
    return out


def _allocate_unique_slug(base_slug: str, taken: set[str]) -> str:
    if base_slug not in taken:
        return base_slug
    i = 2
    while f'{base_slug}-{i}' in taken:
        i += 1
    return f'{base_slug}-{i}'


def fetch_templates_for_slugs(
    slugs: list[str],
    child_id: int,
    *,
    exclude_builtin: bool = False,
) -> list[dict[str, Any]]:
    if not slugs:
        return []
    rows = ProxyTemplate.query.filter(
        ProxyTemplate.slug.in_(slugs),
        (ProxyTemplate.child_id == child_id) | (ProxyTemplate.child_id == 0),
    ).all()
    by_slug = {t.slug: t for t in rows}
    ordered: list[dict[str, Any]] = []
    for slug in slugs:
        tpl = by_slug.get(slug)
        if not tpl:
            continue
        if exclude_builtin and tpl.is_builtin:
            continue
        data = tpl.to_dict()
        data.pop('id', None)
        data.pop('child_id', None)
        ordered.append(data)
    return ordered


def import_templates_from_bundle(templates: list[dict[str, Any]], child_id: int) -> dict[str, str]:
    existing = {
        t.slug
        for t in ProxyTemplate.query.filter(ProxyTemplate.child_id == child_id).all()
    }
    slug_map: dict[str, str] = {}

    for tpl in templates:
        old_slug = (tpl.get('slug') or '').strip()
        if not old_slug:
            continue
        new_slug = _allocate_unique_slug(old_slug, existing | set(slug_map.values()))
        slug_map[old_slug] = new_slug
        existing.add(new_slug)

        tpl_data = dict(tpl)
        tpl_data.pop('id', None)
        tpl_data.pop('child_id', None)
        tpl_data.pop('is_builtin', None)
        tpl_data['slug'] = new_slug
        ProxyTemplate.add_or_update(child_id=child_id, commit=False, **tpl_data)

    db.session.commit()
    return slug_map


def build_export_bundle(
    proxy: dict[str, Any],
    child_id: int,
    *,
    exclude_builtin: bool = False,
) -> dict[str, Any]:
    proxy_out = copy.deepcopy(proxy)
    proxy_out.pop('id', None)
    proxy_out.pop('child_id', None)
    proxy_out.pop('client_cores', None)
    slugs = collect_template_slugs_from_proxy(proxy_out)
    return {
        'version': BUNDLE_VERSION,
        'proxy': proxy_out,
        'templates': fetch_templates_for_slugs(slugs, child_id, exclude_builtin=exclude_builtin),
    }


def build_base_config_export_bundle(
    config: dict[str, Any],
    child_id: int,
    *,
    exclude_builtin: bool = False,
) -> dict[str, Any]:
    config_out = copy.deepcopy(config)
    config_out.pop('id', None)
    config_out.pop('child_id', None)
    slugs = collect_template_slugs_from_base_config(config_out)
    return {
        'version': BUNDLE_VERSION,
        'base_config': config_out,
        'templates': fetch_templates_for_slugs(slugs, child_id, exclude_builtin=exclude_builtin),
    }


def import_bundle(bundle: dict[str, Any], child_id: int) -> dict[str, Any]:
    proxy = copy.deepcopy(bundle.get('proxy') or {})
    templates = list(bundle.get('templates') or [])
    slug_map = import_templates_from_bundle(templates, child_id)
    proxy = remap_proxy_template_slugs(proxy, slug_map)
    proxy.pop('id', None)
    if proxy.get('client_config'):
        proxy['client_config'] = dict(proxy['client_config'])
    return {
        'proxy': proxy,
        'slug_map': slug_map,
        'templates_imported': len(slug_map),
    }


def import_base_config_bundle(bundle: dict[str, Any], child_id: int) -> dict[str, Any]:
    config = copy.deepcopy(bundle.get('base_config') or {})
    templates = list(bundle.get('templates') or [])
    slug_map = import_templates_from_bundle(templates, child_id)
    config = remap_base_config_template_slugs(config, slug_map)
    config.pop('id', None)
    return {
        'base_config': config,
        'slug_map': slug_map,
        'templates_imported': len(slug_map),
    }
