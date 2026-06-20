from __future__ import annotations

from functools import lru_cache
from typing import Any

from hiddifypanel.models.custom_proxy import TemplateCategory

from .fragment_loader import iter_template_files, load_template_slug
from .paths import INTERNAL_SLUG_MARKERS, TEMPLATE_CORES


def _infer_template_meta(slug: str) -> tuple[str, TemplateCategory, str, str]:
    core = slug.split('/')[0]
    leaf = slug.rsplit('/', 1)[-1]

    if slug.endswith('/base') or '/base/' in slug:
        side = leaf
        return core, TemplateCategory.base_config, f'{core} base {side}', f'Base {side} shell'

    if '/client/' in slug:
        category = TemplateCategory.client_outbound
    elif '/server/' in slug:
        category = TemplateCategory.server_inbound
    elif core == 'singbox' or slug.endswith('client_tls'):
        category = TemplateCategory.client_outbound
    elif core == 'sublink' or '/links/' in slug:
        category = TemplateCategory.client_outbound
    else:
        category = TemplateCategory.server_inbound

    if '/protocols/' in slug:
        label = leaf.upper()
        return core, category, f'{core} {label}', f'Protocol: {label}'
    if '/stream/' in slug or '/streams/' in slug:
        return core, category, f'{core} {leaf}', f'Stream: {leaf}'
    if '/tls/' in slug:
        return core, category, f'{core} {leaf} TLS', f'TLS: {leaf}'
    if '/common/security/' in slug:
        return core, category, f'{core} {leaf} security', f'Security: {leaf}'
    if '/snippets/' in slug:
        return core, category, f'{core} {leaf}', f'Snippet: {leaf}'
    if '/inbound/' in slug:
        return core, category, f'{core} {leaf}', f'Inbound: {leaf}'
    if '/client/tls' in slug or slug.endswith('client_tls'):
        return core, TemplateCategory.client_outbound, f'{core} client TLS', 'Client TLS'
    if '/links/' in slug:
        return core, TemplateCategory.client_outbound, f'{core} {leaf}', f'Link: {leaf}'
    if '/common/' in slug and core == 'sublink':
        return core, TemplateCategory.client_outbound, f'sublink {leaf}', f'Sublink: {leaf}'

    title = leaf.replace('_', ' ').title()
    return core, category, f'{core} {title}', title


def _discover_templates() -> list[dict[str, Any]]:
    templates: list[dict[str, Any]] = []
    for slug, path in iter_template_files():
        if any(marker in slug for marker in INTERNAL_SLUG_MARKERS):
            continue
        core = slug.split('/')[0]
        if core not in TEMPLATE_CORES:
            continue
        core, category, name, description = _infer_template_meta(slug)
        normalize = path.suffix == '.pj2'
        content = load_template_slug(slug, normalize=normalize)
        templates.append({
            'slug': slug,
            'core': core,
            'category': category,
            'name': name,
            'description': description,
            'content': content,
        })
    return templates


@lru_cache(maxsize=1)
def build_builtin_templates() -> tuple[dict[str, Any], ...]:
    """All proxy_templates on disk (server, client, base shells) except internal presets."""
    return tuple(_discover_templates())


def get_builtin_templates() -> list[dict[str, Any]]:
    return list(build_builtin_templates())
