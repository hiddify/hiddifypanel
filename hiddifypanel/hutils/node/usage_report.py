"""Last usage report each node sent to this (parent) panel, kept in Redis (no schema change)."""

from __future__ import annotations

import json
from datetime import datetime

from loguru import logger

_KEY = "hiddify:node_usage_report:{child_id}"


def record_usage_report(child_id: int, users: int, usage_bytes: int) -> None:
    from hiddifypanel.cache import redis_client

    payload = {"time": datetime.now().isoformat(timespec="seconds"), "users": int(users), "bytes": int(usage_bytes)}
    try:
        redis_client.set(_KEY.format(child_id=child_id), json.dumps(payload))
    except Exception as err:  # reporting must never break the usage sync itself
        logger.warning(f"Could not record usage report for node {child_id}: {err}")


def last_usage_report(child_id: int) -> dict | None:
    """``{"time": iso, "users": int, "bytes": int}`` or None before the first report."""
    from hiddifypanel.cache import redis_client

    try:
        raw = redis_client.get(_KEY.format(child_id=child_id))
        return json.loads(raw) if raw else None
    except Exception:
        return None
