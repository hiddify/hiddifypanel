from __future__ import annotations

import re
from pathlib import Path

from .paths import FRAGMENT_CORES, FRAGMENT_KINDS, TEMPLATES_ROOT

# hiddify-core uses server|client/stream/; xray uses common/streams/.
_HIDDIFY_KIND_ALIASES = {"streams": "stream"}


def normalize_fragment(content: str) -> str:
    text = content.replace("\r\n", "\n")

    return text.strip()


def slug_to_path(slug: str) -> Path:
    """Map template slug to file under proxy_templates/ (.pj2 or .j2)."""
    pj2 = TEMPLATES_ROOT / f"{slug}.pj2"
    if pj2.is_file():
        return pj2
    j2 = TEMPLATES_ROOT / f"{slug}.j2"
    if j2.is_file():
        return j2
    return pj2


def load_template_slug(slug: str, *, normalize: bool = True) -> str:
    path = slug_to_path(slug)
    if not path.is_file():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    return normalize_fragment(text) if normalize and path.suffix == ".pj2" else text.strip()


def _normalize_kind(core: str, kind: str) -> str:
    if core == "hiddify-core":
        return _HIDDIFY_KIND_ALIASES.get(kind, kind)
    return kind


def _fragment_folder(core: str, kind: str, side: str = "server") -> Path:
    kind = _normalize_kind(core, kind)
    if core == "hiddify-core":
        return TEMPLATES_ROOT / core / side / kind
    return TEMPLATES_ROOT / core / "common" / kind


def fragment_path(core: str, kind: str, name: str, side: str = "server") -> Path:
    if core not in FRAGMENT_CORES:
        raise ValueError(f"Unknown core: {core}")
    kind = _normalize_kind(core, kind)
    if kind not in FRAGMENT_KINDS and kind not in ("stream", "tls"):
        raise ValueError(f"Unknown fragment kind: {kind}")
    return _fragment_folder(core, kind, side) / f"{name}.pj2"


def load_fragment(core: str, kind: str, name: str, side: str = "server") -> str:
    return load_template_slug(fragment_slug(core, kind, name, side=side))


def fragment_slug(core: str, kind: str, name: str, side: str = "server") -> str:
    kind = _normalize_kind(core, kind)
    if core == "hiddify-core":
        return f"{core}/{side}/{kind}/{name}"
    return f"{core}/common/{kind}/{name}"


def list_fragments(core: str, kind: str, side: str = "server") -> list[str]:
    folder = _fragment_folder(core, kind, side)
    if not folder.is_dir():
        return []
    return sorted(p.stem for p in folder.glob("*.pj2"))


from ..builtin_proxy_sync.discovery import iter_template_files as _iter_sync_template_files


def iter_template_files() -> list[tuple[str, Path]]:
    """All syncable template fragments (.pj2 and non-base .j2)."""
    return list(_iter_sync_template_files())
