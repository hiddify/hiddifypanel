"""How much RAM xray and hiddify-core need for their users (plus the panel), compared with the server's RAM.

Each core keeps one entry per user in every inbound that takes users, so its memory grows with
users × inbounds (40 000 users × 50 inbounds ≈ 2 million entries ≈ 2.6 GB for xray while it loads).
The dump of the server configs counts the entries it writes (``generated/core-load.json``; the user list
is dumped again on every change), and the admin notices compare the estimate with the RAM.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LOAD_FILE = "core-load.json"
GENERATED_DIR = Path("/opt/hiddify-manager/generated")
#: One user entry while a core loads its config, with a margin: measured ~1.2 KB once loaded on xray 26.10 /
#: hiddify-core 5.3, more while the JSON is parsed; doubled so the notices come at half the users.
BYTES_PER_USER_ENTRY = 3 * 1024
#: A core with no users (runtime, geo files, outbounds; an idle xray uses ~30 MB).
CORE_BASE_BYTES = 50 * 1024**2
#: The panel itself, which runs on the same server: 200 MB, and 2 MB more per user, up to 1 GB.
PANEL_BASE_BYTES = 200 * 1024**2
PANEL_BYTES_PER_USER = 2 * 1024**2
PANEL_MAX_BYTES = 1024**3
WARN_RATIO = 0.5
ERROR_RATIO = 0.8
CORES = ("xray", "hiddify-core")


def count_user_entries(data: Any) -> int:
    """User entries of a rendered xray / hiddify-core config: ``settings.clients`` (xray) or ``users`` (hiddify-core)."""
    if not isinstance(data, dict):
        return 0
    total = 0
    for section in ("inbounds", "endpoints"):
        for item in data.get(section) or []:
            if not isinstance(item, dict):
                continue
            settings = item.get("settings")
            clients = settings.get("clients") if isinstance(settings, dict) else None
            users = item.get("users")
            for entries in (clients, users):
                if isinstance(entries, list):
                    total += len(entries)
    return total


def save(target: Path, users: int, entries: dict[str, int]) -> None:
    """Keeps the cores not dumped this time (``--cores``) as they were."""
    path = target / LOAD_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    cores = data.get("cores") if isinstance(data.get("cores"), dict) else {}
    for core, count in entries.items():
        cores[core] = {"entries": count, "users": users}
    path.write_text(json.dumps({"cores": cores}), encoding="utf-8")


@dataclass
class CoreLoad:
    users: int
    entries: int
    estimate_bytes: int
    ram_bytes: int

    @property
    def ratio(self) -> float:
        return self.estimate_bytes / self.ram_bytes if self.ram_bytes else 0.0

    @property
    def inbounds(self) -> int:
        """User inbounds of both cores together: the entries of one user."""
        return round(self.entries / self.users) if self.users else 0

    @property
    def level(self) -> str | None:
        if self.ratio >= ERROR_RATIO:
            return "error"
        if self.ratio >= WARN_RATIO:
            return "warn"
        return None


def _ram_bytes() -> int:
    import psutil

    return int(psutil.virtual_memory().total)


def panel_bytes(users: int) -> int:
    return min(PANEL_BASE_BYTES + users * PANEL_BYTES_PER_USER, PANEL_MAX_BYTES)


def estimate(generated: Path = GENERATED_DIR, ram_bytes: int | None = None) -> CoreLoad | None:
    """``None`` before the first dump, or when no core has users."""
    try:
        data = json.loads((generated / LOAD_FILE).read_text(encoding="utf-8"))
        cores = data["cores"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    entries = 0
    users = 0
    estimate_bytes = 0
    for core in CORES:
        row = cores.get(core) if isinstance(cores, dict) else None
        if not isinstance(row, dict) or not row.get("entries"):
            continue
        entries += int(row["entries"])
        users = max(users, int(row.get("users") or 0))
        estimate_bytes += CORE_BASE_BYTES + int(row["entries"]) * BYTES_PER_USER_ENTRY
    if not entries:
        return None
    estimate_bytes += panel_bytes(users)
    return CoreLoad(users=users, entries=entries, estimate_bytes=estimate_bytes, ram_bytes=ram_bytes or _ram_bytes())
