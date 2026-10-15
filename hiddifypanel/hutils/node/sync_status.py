"""What a node last got from (or sent to) its parent, for the node's sync page (debugging).

Every sync path writes here: registering, the HTTP sync, the WebSocket change feed and inventory, and the usage report. It is
kept in redis, not in memory, because the WebSocket client runs in one process and the page is served by any of them.
Writing never raises: a failed note must not fail a sync.
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger
from pydantic import BaseModel, ValidationError
from strenum import StrEnum

_KEY = "node:sync_status"
_WS_KEY = "node:sync_status:ws"
#: the last syncs of any kind, newest first
_LOG_KEY = "node:sync_status:log"
LOG_SIZE = 30


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


def record(kind: SyncKind, source: SyncSource, count: int | None = None, *, ok: bool = True, **detail: str | int | bool) -> None:
    """Note one sync of ``kind`` by ``source``; a failed one (``ok=False``) is kept apart, so it does not hide the last success."""
    entry = SyncEntry(kind=kind, source=source, at=time.time(), count=count, ok=ok, detail=detail)
    try:
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
