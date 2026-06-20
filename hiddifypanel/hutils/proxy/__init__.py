from __future__ import annotations

import importlib

from .shared import *

_LAZY_SUBMODULES = frozenset({'xray', 'xrayjson', 'singbox', 'clash', 'wireguard'})


def __getattr__(name: str):
    if name in _LAZY_SUBMODULES:
        module = importlib.import_module(f'.{name}', __name__)
        globals()[name] = module
        return module
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
