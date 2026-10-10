"""Snell v5 and v6: two built-in proxies that share one protocol template.

Each row of the proxy matrix carries its version in ``l3`` (``snell_v5`` / ``snell_v6``). The builders put
``{% set snell_version = N %}`` in front of the generated server, client and link templates, and the shared Snell
templates read it (v5 when it is not set)."""

from __future__ import annotations

SNELL_L3 = {"snell_v5": 5, "snell_v6": 6}


def snell_version(combo) -> int | None:
    if str(combo.proto).lower() != "snell":
        return None
    return SNELL_L3.get(str(combo.l3).lower())


def with_snell_version(content: str, combo) -> str:
    """``content`` with the Snell version set for the templates it includes (inside its first block, if it has one)."""
    version = snell_version(combo)
    if version is None:
        return content
    line = f"{{% set snell_version = {version} %}}"
    import re

    match = re.search(r"\{%-?\s*block\s+\w+\s*-?%\}", content)
    if match:
        return content[: match.end()] + "\n" + line + content[match.end():]
    return line + "\n" + content
