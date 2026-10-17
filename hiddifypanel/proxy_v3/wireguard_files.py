"""The /wireguard download: a WireGuard .conf holds one tunnel ([Interface] + its peers), so several configs go out as a zip
of .conf files, one config as its .conf.

File names become tunnel names: wg-quick (Linux) takes at most 15 characters of ``A-Z a-z 0-9 _ = + . -``, so a name
is the config's tag cut to that, unique within the download.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass

MAX_NAME = 15  # wg-quick's interface name limit (IFNAMSIZ - 1)
_UNSAFE = re.compile(r"[^A-Za-z0-9_=+.-]+")
_NAME_LINE = re.compile(r"^\s*#\s*Name\s*=\s*(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class WireguardFile:
    name: str  # without ".conf"
    content: str

    @property
    def filename(self) -> str:
        return f"{self.name}.conf"


def _safe_name(label: str, fallback: str) -> str:
    name = _UNSAFE.sub("_", label).strip("_.")
    return name[:MAX_NAME].rstrip("_.") or fallback


def _unique(name: str, used: set[str]) -> str:
    unique, n = name, 1
    while unique.lower() in used:
        n += 1
        suffix = f"_{n}"
        unique = name[: MAX_NAME - len(suffix)] + suffix
    used.add(unique.lower())
    return unique


def split_configs(text: str) -> list[WireguardFile]:
    """The rendered .conf text (configs one after another) → one file per [Interface]."""
    parts = re.split(r"(?m)^(?=\[Interface\]\s*$)", text or "")
    files: list[WireguardFile] = []
    used: set[str] = set()
    for part in parts:
        if "[Interface]" not in part or "[Peer]" not in part:
            continue
        label = m.group(1) if (m := _NAME_LINE.search(part)) else ""
        name = _unique(_safe_name(label, f"wg{len(files) + 1}"), used)
        files.append(WireguardFile(name=name, content=part.strip() + "\n"))
    return files


def zip_configs(files: list[WireguardFile]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.writestr(f.filename, f.content)
    return buf.getvalue()
