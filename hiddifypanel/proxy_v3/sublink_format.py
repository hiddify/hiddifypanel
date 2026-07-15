from __future__ import annotations

from typing import Any


def build_sublink_formats(raw: str) -> dict[str, Any]:
    """Return rendered sublink text for admin preview."""
    return {
        "raw": (raw or "").strip(),
        "parse_error": None,
    }
