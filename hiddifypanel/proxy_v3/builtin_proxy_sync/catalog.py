from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from hiddifypanel.models.custom_proxy import TemplateCategory, TemplateCore
from hiddifypanel.models.proxy_base_config import BUILTIN_BASE_CONFIGS, default_base_content

from ..template_catalog.fragment_loader import load_template_slug
from .discovery import iter_template_files
from .paths import TEMPLATE_CORES


class BuiltinTemplateRecord(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    slug: str
    core: TemplateCore
    category: TemplateCategory
    name: str
    description: str
    content: str


class BuiltinBaseConfigRecord(BaseModel):
    core: str
    side: str
    version: str
    name: str
    description: str
    content: str


def _infer_template_meta(slug: str) -> tuple[TemplateCore, TemplateCategory, str, str]:
    core_str = slug.split('/')[0]
    try:
        core = TemplateCore(core_str)
    except ValueError:
        core = TemplateCore.xray
    leaf = slug.rsplit('/', 1)[-1]

    if '/base/' in slug and not slug.endswith('/base'):
        return core, TemplateCategory.base_config, f'{core_str} base {leaf}', f'Base fragment: {leaf}'

    if '/client/' in slug:
        category = TemplateCategory.client_outbound
    elif '/server/' in slug:
        category = TemplateCategory.server_inbound
    elif core_str == 'singbox' or slug.endswith('client_tls'):
        category = TemplateCategory.client_outbound
    elif core_str == 'sublink' or '/links/' in slug:
        category = TemplateCategory.client_outbound
    else:
        category = TemplateCategory.server_inbound

    if '/protocols/' in slug:
        label = leaf.upper()
        return core, category, f'{core_str} {label}', f'Protocol: {label}'
    if '/stream/' in slug or '/streams/' in slug:
        return core, category, f'{core_str} {leaf}', f'Stream: {leaf}'
    if '/tls/' in slug:
        return core, category, f'{core_str} {leaf} TLS', f'TLS: {leaf}'
    if '/common/security/' in slug:
        return core, category, f'{core_str} {leaf} security', f'Security: {leaf}'
    if '/snippets/' in slug:
        return core, category, f'{core_str} {leaf}', f'Snippet: {leaf}'
    if '/inbound/' in slug:
        return core, category, f'{core_str} {leaf}', f'Inbound: {leaf}'
    if '/client/tls' in slug or slug.endswith('client_tls'):
        return core, TemplateCategory.client_outbound, f'{core_str} client TLS', 'Client TLS'
    if '/links/' in slug:
        return core, TemplateCategory.client_outbound, f'{core_str} {leaf}', f'Link: {leaf}'
    if '/common/' in slug and core_str == 'sublink':
        return core, TemplateCategory.client_outbound, f'sublink {leaf}', f'Sublink: {leaf}'

    title = leaf.replace('_', ' ').title()
    return core, category, f'{core_str} {title}', title


def _load_content(slug: str, path: Path) -> str:
    normalize = path.suffix == '.pj2'
    return load_template_slug(slug, normalize=normalize)


@lru_cache(maxsize=1)
def discover_builtin_templates() -> tuple[BuiltinTemplateRecord, ...]:
    records: list[BuiltinTemplateRecord] = []
    for slug, path in iter_template_files():
        core_str = slug.split('/')[0]
        if core_str not in TEMPLATE_CORES:
            continue
        core, category, name, description = _infer_template_meta(slug)
        records.append(BuiltinTemplateRecord(
            slug=slug,
            core=core,
            category=category,
            name=name,
            description=description,
            content=_load_content(slug, path),
        ))
    return tuple(records)


@lru_cache(maxsize=1)
def discover_base_configs() -> tuple[BuiltinBaseConfigRecord, ...]:
    records: list[BuiltinBaseConfigRecord] = []
    for spec in BUILTIN_BASE_CONFIGS:
        side = spec['side']
        core = spec['core']
        side_val = side.value if hasattr(side, 'value') else str(side)
        records.append(BuiltinBaseConfigRecord(
            core=core,
            side=side_val,
            version=spec['version'],
            name=spec['name'],
            description=spec['description'],
            content=default_base_content(side_val, core),
        ))
    return tuple(records)


def clear_builtin_template_cache() -> None:
    discover_builtin_templates.cache_clear()
    discover_base_configs.cache_clear()


def build_builtin_templates() -> tuple[BuiltinTemplateRecord, ...]:
    return discover_builtin_templates()


def get_builtin_templates() -> list[BuiltinTemplateRecord]:
    return list(discover_builtin_templates())


def get_builtin_base_configs() -> list[BuiltinBaseConfigRecord]:
    return list(discover_base_configs())
