"""What a node last got from (or sent to) its parent, for the node's sync page (debugging).

Every sync path writes here: registering, the HTTP sync, the WebSocket change feed and inventory, and the usage report. It is
kept in redis, not in memory, because the WebSocket client runs in one process and the page is served by any of them.
Writing never raises: a failed note must not fail a sync.
"""

from __future__ import annotations

import base64
import json
import time
import zlib
from collections.abc import Iterable
from typing import Any

from loguru import logger
from pydantic import BaseModel, ValidationError
from strenum import StrEnum

_KEY = "node:sync_status"
_WS_KEY = "node:sync_status:ws"
#: the last syncs of any kind, newest first
_LOG_KEY = "node:sync_status:log"
LOG_SIZE = 30
#: items shown per log entry (the rest are counted); kept in redis with the log, never in the database
ITEMS_PER_ENTRY = 50
#: the exchanged rows as JSON are kept zlib-compressed up to this size; bigger ones keep only their first RAW_HEAD bytes
RAW_MAX_COMPRESSED = 12 * 1024
RAW_HEAD = 4096


class SyncKind(StrEnum):
    """What a sync carried."""

    admins = "admins"
    users = "users"
    domains = "domains"
    outbounds = "outbounds"
    usage = "usage"


class SyncSource(StrEnum):
    """Which path did it."""

    register = "register"
    http_sync = "http_sync"
    ws_feed = "ws_feed"
    inventory = "inventory"
    usage_report = "usage_report"


class SyncEntry(BaseModel):
    kind: SyncKind
    source: SyncSource
    #: Unix seconds
    at: float
    #: rows it carried (None: not counted)
    count: int | None = None
    ok: bool = True
    detail: dict[str, str | int | bool] = {}
    #: what was exchanged, one short line per row ("name 1234abcd enabled"); at most ITEMS_PER_ENTRY
    items: list[str] = []
    #: rows not listed in ``items``
    items_more: int = 0
    #: the exchanged rows as JSON, zlib-compressed then base64 ("" when nothing was carried); see raw_json()
    raw_z: str = ""
    #: size of the whole JSON, and whether raw_z holds only its beginning
    raw_size: int = 0
    raw_truncated: bool = False


class WsState(BaseModel):
    """The WebSocket client's state (``ws_client.status()``); Unix seconds."""

    running: bool = False
    connected: bool = False
    host: str = ""
    transport: str = ""
    connected_since: float | None = None
    last_batch_at: float | None = None
    last_http_sync: float | None = None
    rows: int = 0
    last_error: str = ""
    saved_at: float | None = None


class SyncLog(BaseModel):
    last: dict[SyncKind, SyncEntry | None]
    last_error: dict[SyncKind, SyncEntry | None]
    log: list[SyncEntry]
    websocket: WsState | None


def _redis():
    from hiddifypanel.cache import redis_client

    return redis_client


def _field(row: Any, name: str) -> Any:
    return row.get(name) if isinstance(row, dict) else getattr(row, name, None)


def item_label(row: Any) -> str:
    """One exchanged row in a few words: its name, short uuid and, for users, whether it is enabled."""
    if isinstance(row, str):
        return row
    parts: list[str] = []
    name = _field(row, "name") or _field(row, "domain") or _field(row, "tag")
    if name:
        parts.append(str(name))
    if uuid := _field(row, "uuid"):
        parts.append(str(uuid).replace("-", "")[:8])
    enable = _field(row, "enable")
    if enable is not None:
        parts.append("enabled" if enable else "disabled")
    if (mode := _field(row, "mode")) is not None and _field(row, "usage_limit") is None:  # an admin's mode (users have reset modes)
        parts.append(str(mode))
    upload, download = _field(row, "upload"), _field(row, "download")
    if upload is not None or download is not None:  # usage
        parts.append(f"+{((upload or 0) + (download or 0)) / 1024 / 1024:.1f} MB")
    return " ".join(parts) or str(row)[:60]


def _jsonable(row: Any) -> Any:
    if hasattr(row, "model_dump"):
        return row.model_dump(mode="json")
    return row


def raw_json(rows: list[Any]) -> tuple[str, int, bool]:
    """The rows as compressed JSON for the debug view: (base64 zlib, size of the whole JSON, truncated)."""
    if not rows:
        return "", 0, False
    data = json.dumps([_jsonable(row) for row in rows], default=str, ensure_ascii=False, separators=(",", ":")).encode()
    packed = zlib.compress(data, 6)
    truncated = len(packed) > RAW_MAX_COMPRESSED
    if truncated:
        packed = zlib.compress(data[:RAW_HEAD], 6)
    return base64.b64encode(packed).decode(), len(data), truncated


def record(
    kind: SyncKind, source: SyncSource, count: int | None = None, *, ok: bool = True, items: Iterable[Any] | None = None, **detail: str | int | bool
) -> None:
    """Note one sync of ``kind`` by ``source``; a failed one (``ok=False``) is kept apart, so it does not hide the last success.
    ``items``: the rows exchanged (shown on the node's sync page; only the first ITEMS_PER_ENTRY are kept)."""
    try:
        rows = list(items or [])
        labels = [item_label(row) for row in rows[:ITEMS_PER_ENTRY]]
        raw_z, raw_size, raw_truncated = raw_json(rows)
        entry = SyncEntry(
            kind=kind, source=source, at=time.time(), count=count, ok=ok, detail=detail,
            items=labels, items_more=max(0, len(rows) - len(labels)),
            raw_z=raw_z, raw_size=raw_size, raw_truncated=raw_truncated,
        )
        raw = entry.model_dump_json()
        pipe = _redis().pipeline()
        pipe.hset(_KEY, kind if ok else f"{kind}:error", raw)
        pipe.lpush(_LOG_KEY, raw)
        pipe.ltrim(_LOG_KEY, 0, LOG_SIZE - 1)
        pipe.execute()
    except Exception as e:  # noqa: BLE001
        logger.debug(f"node sync status: could not note {kind} from {source}: {e}")


def save_ws(status: dict[str, Any]) -> None:
    """The WebSocket client's state, from its own process."""
    try:
        state = WsState.model_validate({**status, "saved_at": time.time()})
        _redis().set(_WS_KEY, state.model_dump_json())
    except Exception as e:  # noqa: BLE001
        logger.debug(f"node sync status: could not save the WebSocket state: {e}")


def _parse[M: BaseModel](model: type[M], raw: bytes | str | None) -> M | None:
    if not raw:
        return None
    try:
        return model.model_validate_json(raw)
    except ValidationError:  # written by another version
        return None


def read() -> SyncLog:
    r = _redis()
    stored = {(k.decode() if isinstance(k, bytes) else k): v for k, v in (r.hgetall(_KEY) or {}).items()}
    return SyncLog(
        last={kind: _parse(SyncEntry, stored.get(kind)) for kind in SyncKind},
        last_error={kind: _parse(SyncEntry, stored.get(f"{kind}:error")) for kind in SyncKind},
        log=[e for e in (_parse(SyncEntry, raw) for raw in r.lrange(_LOG_KEY, 0, LOG_SIZE - 1)) if e],
        websocket=_parse(WsState, r.get(_WS_KEY)),
    )
