from __future__ import annotations

from .paths import TEMPLATES_ROOT


def load_base_config_file(core: str, side: str) -> str:
    """Load `{core}/{side}/base.j2` from proxy_templates only."""
    path = TEMPLATES_ROOT / core / side / "base.j2"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    raise FileNotFoundError(path)


def default_base_content(side: str, core: str) -> str:
    return load_base_config_file(core, side)
