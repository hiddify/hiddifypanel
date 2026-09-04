from __future__ import annotations

from pathlib import Path

# proxy_templates/ — single source for fragments, snippets, base shells, presets.
TEMPLATES_ROOT = Path(__file__).resolve().parents[1] / 'proxy_templates'

FRAGMENT_CORES = ('xray', 'hiddify-core')
TEMPLATE_CORES = ('xray', 'hiddify-core', 'singbox', 'sublink', 'haproxy', 'clash', 'rust-rpxy-l4', 'nginx')
FRAGMENT_KINDS = ('protocols', 'streams', 'stream', 'tls', 'security')

# Slug path markers excluded from ProxyTemplate DB seed.
PRESET_SLUG_MARKER = '/presets/'
BASE_CONFIG_SIDES = ('client', 'server')
