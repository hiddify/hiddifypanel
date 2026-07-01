"""Proxy template catalog — import submodules directly to avoid circular imports."""

from __future__ import annotations

from typing import Any

_LAZY_EXPORTS = {
    'TEMPLATES_ROOT': '.paths',
    'default_base_content': '.base_configs',
    'load_base_config_file': '.base_configs',
    'BUILTIN_TEMPLATES': '.builtin_templates',
    'build_builtin_templates': '.builtin_templates',
    'get_builtin_templates': '.builtin_templates',
    'fragment_slug': '.fragment_loader',
    'list_fragments': '.fragment_loader',
    'load_fragment': '.fragment_loader',
    'load_template_slug': '.fragment_loader',
    'iter_template_files': '.fragment_loader',
    'iter_proxy_combinations': '.proxy_matrix',
    'ProxyCombination': '.proxy_matrix',
    'iter_custom_proxy_presets': '.custom_proxy_presets',
    'seed_custom_proxy_presets': '.custom_proxy_presets',
    'build_xray_inbound_template': '.inbound_builder',
    'build_hiddify_inbound_template': '.inbound_builder',
    'build_all_client_configs': '.client_builder',
    'default_sublink_link_template': '.template_defaults',
    'seed_proxy_catalog': '.seed',
}

__all__ = list(_LAZY_EXPORTS.keys())


def __getattr__(name: str) -> Any:
    if name == 'BUILTIN_TEMPLATES':
        from .builtin_templates import get_builtin_templates
        return get_builtin_templates()
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
    import importlib
    module = importlib.import_module(_LAZY_EXPORTS[name], __name__)
    return getattr(module, name)
