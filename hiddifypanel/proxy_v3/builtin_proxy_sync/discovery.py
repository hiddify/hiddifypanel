from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from .paths import BASE_CONFIG_SIDES, PRESET_SLUG_MARKER, TEMPLATES_ROOT

ProxyPathKind = Literal["base", "preset", "template"]

_BASE_CONFIG_RE = re.compile(r"^([^/]+)/(client|server)/base\.j2$")


def _rel_path(path: Path) -> str:
    return str(path.relative_to(TEMPLATES_ROOT)).replace("\\", "/")


def is_preset_path(rel: str) -> bool:
    return PRESET_SLUG_MARKER in f"/{rel}/"


def is_base_config_path(rel: str) -> bool:
    return bool(_BASE_CONFIG_RE.match(rel))


def parse_base_config_path(rel: str) -> tuple[str, str] | None:
    match = _BASE_CONFIG_RE.match(rel)
    if not match:
        return None
    return match.group(1), match.group(2)


def classify_path(rel: str) -> ProxyPathKind:
    if is_preset_path(rel):
        return "preset"
    if is_base_config_path(rel):
        return "base"
    return "template"


def iter_template_files() -> Iterator[tuple[str, Path]]:
    """Discover fragment templates: .pj2 files and non-base-shell .j2 files."""
    if not TEMPLATES_ROOT.is_dir():
        return
    for path in sorted(TEMPLATES_ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = _rel_path(path)
        kind = classify_path(rel)
        if kind == "preset":
            continue
        if path.suffix == ".pj2":
            slug = str(path.relative_to(TEMPLATES_ROOT).with_suffix("")).replace("\\", "/")
            yield slug, path
        elif path.suffix == ".j2" and kind == "template":
            slug = str(path.relative_to(TEMPLATES_ROOT).with_suffix("")).replace("\\", "/")
            yield slug, path


def iter_base_config_files() -> Iterator[tuple[str, str, Path]]:
    """Discover {core}/{client|server}/base.j2 shells for ProxyBaseConfig sync."""
    if not TEMPLATES_ROOT.is_dir():
        return
    for path in sorted(TEMPLATES_ROOT.rglob("base.j2")):
        if not path.is_file():
            continue
        rel = _rel_path(path)
        parsed = parse_base_config_path(rel)
        if not parsed:
            continue
        core, side = parsed
        if side not in BASE_CONFIG_SIDES:
            continue
        yield core, side, path
