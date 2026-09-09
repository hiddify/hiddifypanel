from __future__ import annotations

import re
from pathlib import Path

from .paths import FRAGMENT_CORES, FRAGMENT_KINDS, TEMPLATES_ROOT

_STREAM_KIND_ALIASES = {"stream": "streams", "streams": "stream"}


def normalize_fragment(content: str) -> str:
    text = content.replace("\r\n", "\n")

    return text.strip()


def _stream_kind_alias_slug(slug: str) -> str:
    parts = slug.split("/")
    if len(parts) >= 3 and parts[2] in _STREAM_KIND_ALIASES:
        aliased = parts.copy()
        aliased[2] = _STREAM_KIND_ALIASES[parts[2]]
        return "/".join(aliased)
    return slug


def slug_to_path(slug: str) -> Path:
    """Map template slug to file under proxy_templates/ (.j2)."""
    for candidate in (slug, _stream_kind_alias_slug(slug)):
        j2 = TEMPLATES_ROOT / f"{candidate}.j2"
        if j2.is_file():
            return j2
    return TEMPLATES_ROOT / f"{slug}.j2"


def load_template_slug(slug: str, *, normalize: bool = True) -> str:
    path = slug_to_path(slug)
    if not path.is_file():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    return normalize_fragment(text) if normalize else text.strip()


def _fragment_folder(core: str, kind: str, side: str = "server") -> Path:
    return TEMPLATES_ROOT / core / side / kind


def fragment_path(core: str, kind: str, name: str, side: str = "server") -> Path:
    if core not in FRAGMENT_CORES:
        raise ValueError(f"Unknown core: {core}")
    if kind not in FRAGMENT_KINDS and kind not in ("streams", "tls"):
        raise ValueError(f"Unknown fragment kind: {kind}")
    return _fragment_folder(core, kind, side) / f"{name}.j2"


def load_fragment(core: str, kind: str, name: str, side: str = "server") -> str:
    return load_template_slug(fragment_slug(core, kind, name, side=side))


def fragment_slug(core: str, kind: str, name: str, side: str = "server") -> str:
    return f"{core}/{side}/{kind}/{name}"


def list_fragments(core: str, kind: str, side: str = "server") -> list[str]:
    folder = _fragment_folder(core, kind, side)
    if not folder.is_dir():
        alt = _STREAM_KIND_ALIASES.get(kind)
        folder = _fragment_folder(core, alt, side) if alt else folder
    if not folder.is_dir():
        return []
    return sorted(p.stem for p in folder.glob("*.j2"))


from ..builtin_proxy_sync.discovery import iter_template_files as _iter_sync_template_files


def iter_template_files() -> list[tuple[str, Path]]:
    """All syncable template fragments (.j2, excluding base shells and presets)."""
    return list(_iter_sync_template_files())
