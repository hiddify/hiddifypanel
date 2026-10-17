"""The WebSocket test of the Actions page (``call`` on the live channel): what this process is, the nodes' WebSockets, and the
first batch a new node would get."""

from __future__ import annotations

import json
import os
import threading
import time
import zlib
from typing import Any

MAX_ECHO = 8 * 1024 * 1024
MAX_FEED_LIMIT = 5000


def _panel_mode() -> str:
    from hiddifypanel.hutils.node import shared

    mode = shared.panel_mode()
    return "node" if mode == "child" else mode


def hello() -> dict[str, Any]:
    from hiddifypanel.hutils.node import ws_proto

    from . import changes

    return {"server_time": time.time(), "pid": os.getpid(), "threads": threading.active_count(), "protocol": ws_proto.VERSION, "change_count": changes.hub.total}


def status() -> dict[str, Any]:
    from hiddifypanel.hutils.node import ws_client, ws_server
    from hiddifypanel.hutils.node.sync_feed import stored_cursor
    from hiddifypanel.models import Child, ChildMode

    mode = _panel_mode()
    nodes = [
        {
            "id": c.id,
            "name": c.name,
            "unique_id": c.unique_id,
            "websocket": ws_server.is_connected(c.unique_id),
            "last_seen": c.last_node_to_parent_time.isoformat() if getattr(c, "last_node_to_parent_time", None) else None,
        }
        for c in Child.query.filter(Child.id != 0, Child.mode == ChildMode.remote).order_by(Child.id).all()
    ]
    parent = {**ws_client.status(), "cursor": stored_cursor().to_json()} if mode == "node" else None
    return {"panel_mode": mode, "nodes": nodes, "parent": parent}


def feed_preview(limit: int) -> dict[str, Any]:
    """The first batch a new node would get: what it holds and how big it is on the wire."""
    from hiddifypanel.hutils.node.sync_feed import Cursor, Feed
    from hiddifypanel.models import ConfigEnum, hconfig

    started = time.perf_counter()
    batch = Feed(Cursor(), str(hconfig(ConfigEnum.unique_id))).next_batch(limit)
    built = time.perf_counter() - started
    if batch is None:
        return {"limit": limit, "admins": 0, "users": 0, "more": False, "json_bytes": 0, "wire_bytes": 0, "build_ms": round(built * 1000, 1), "sample": None}
    raw = json.dumps(batch, separators=(",", ":"), default=str).encode()
    rows = batch["users"] or batch["admins"]
    return {
        "limit": limit,
        "admins": len(batch["admins"]),
        "users": len(batch["users"]),
        "more": batch["more"],
        "json_bytes": len(raw),
        "wire_bytes": len(zlib.compress(raw, 6)),
        "build_ms": round(built * 1000, 1),
        "sample": rows[0] if rows else None,
    }
