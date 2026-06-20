from __future__ import annotations

from pathlib import Path

from .paths import TEMPLATES_ROOT


def load_base_config_file(core: str, side: str) -> str:
    candidates = [
        TEMPLATES_ROOT / core / 'base' / f'{side}.j2',
        TEMPLATES_ROOT / core / side / 'base.j2',
    ]
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding='utf-8')
    raise FileNotFoundError(candidates[0])


def default_base_content(side: str, core: str) -> str:
    if core == 'xray':
        return load_base_config_file('xray', side)
    if core in ('hiddify-core', 'singbox'):
        return load_base_config_file('hiddify-core', side)
    if core == 'haproxy':
        return load_base_config_file('haproxy', side)
    if core == 'sublink' and side == 'client':
        return '{\n  "links": []\n}'
    return '{}'
