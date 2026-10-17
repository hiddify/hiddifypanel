"""Resolve built user-front entry files (same pattern as admin_v2 / Vite manifest)."""

from __future__ import annotations

import json
from pathlib import Path

_USER_FRONT_DIR = Path(__file__).resolve().parents[2] / "static" / "user-front"
_MANIFEST_PATHS = (_USER_FRONT_DIR / ".vite" / "manifest.json", _USER_FRONT_DIR / "manifest.json")
_ENTRY_FALLBACK = ("assets/index.js", "assets/index.css")


def user_front_built() -> bool:
    """True when a production bundle is present under static/user-front/."""
    if (_USER_FRONT_DIR / "manifest.json").is_file() or (_USER_FRONT_DIR / ".vite" / "manifest.json").is_file():
        return True
    return any(_USER_FRONT_DIR.joinpath("assets").glob("index-*.js"))


def user_front_entry_files() -> tuple[str, str | None]:
    """(js, css) relative to ``static/user-front/``; css may be None."""
    for manifest in _MANIFEST_PATHS:
        try:
            entries = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        entry = next((e for e in entries.values() if e.get("isEntry") and e.get("file")), None)
        if entry is None or not (_USER_FRONT_DIR / entry["file"]).is_file():
            continue
        css = next((c for c in entry.get("css") or [] if (_USER_FRONT_DIR / c).is_file()), None)
        return entry["file"], css
    # Prebuilt / older layouts: pick the hashed index bundle if present.
    assets = _USER_FRONT_DIR / "assets"
    js = next(iter(sorted(assets.glob("index-*.js"), reverse=True)), None)
    css = next(iter(sorted(assets.glob("index-*.css"), reverse=True)), None)
    if js is not None:
        return f"assets/{js.name}", f"assets/{css.name}" if css else None
    return _ENTRY_FALLBACK[0], _ENTRY_FALLBACK[1]
