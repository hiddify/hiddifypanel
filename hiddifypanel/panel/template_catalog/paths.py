from __future__ import annotations

from pathlib import Path

# panel/proxy_templates — single source for fragments, snippets, base shells, presets.
TEMPLATES_ROOT = Path(__file__).resolve().parents[1] / 'proxy_templates'

# Cores with protocol/stream fragments under common/ (xray) or server|client/ (hiddify-core).
FRAGMENT_CORES = ('xray', 'hiddify-core')

# All cores that may appear in discovered template slugs (includes singbox client TLS).
TEMPLATE_CORES = ('xray', 'hiddify-core', 'singbox', 'sublink', 'haproxy')

FRAGMENT_KINDS = ('protocols', 'streams', 'stream', 'tls')

# Paths excluded from ProxyTemplate DB seed (internal preset shells only).
INTERNAL_SLUG_MARKERS = ('/presets/',)
