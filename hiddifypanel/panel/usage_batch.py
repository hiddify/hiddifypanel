"""Exactly-once delivery of a node's usage report to its parent panel.

A node sends its usage deltas as one batch with an id and keeps resending that same batch, unchanged, until the parent
has answered. The parent remembers the id of the last batch it applied and skips a repeat. So a report whose answer got
lost (a timeout, a gateway error, a retry on another address) is never added twice.

State is in Redis: the node's batch in flight, and per node the last batch the parent applied. Redis is passed in, so the
functions are testable with a stand-in.
"""

from __future__ import annotations

import json
from typing import Any

from hiddifypanel.models.usage_data import UsageData

INFLIGHT_KEY = "hiddify:usage_batch:inflight"
APPLIED_KEY = "hiddify:usage_batch:applied:{child_id}"
APPLIED_TTL = 30 * 24 * 3600  # a node that sent nothing for a month starts a fresh batch id anyway


def _text(value: Any) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def load_inflight(redis: Any) -> tuple[str, list[UsageData]] | None:
    """The batch sent but not yet answered by the parent: ``(batch_id, usages)``, or None."""
    raw = redis.get(INFLIGHT_KEY)
    if not raw:
        return None
    try:
        data = json.loads(_text(raw))
        return str(data["id"]), [UsageData(uuid=str(u["uuid"]), upload=int(u.get("upload", 0)), download=int(u.get("download", 0))) for u in data["usages"]]
    except (ValueError, KeyError, TypeError):
        redis.delete(INFLIGHT_KEY)
        return None


def save_inflight(redis: Any, batch_id: str, usages: list[UsageData]) -> None:
    payload = {"id": batch_id, "usages": [{"uuid": u.uuid, "upload": u.upload, "download": u.download} for u in usages]}
    redis.set(INFLIGHT_KEY, json.dumps(payload))


def drop_inflight(redis: Any) -> None:
    redis.delete(INFLIGHT_KEY)


def already_applied(redis: Any, child_id: int, batch_id: str) -> bool:
    last = redis.get(APPLIED_KEY.format(child_id=child_id))
    return bool(last) and _text(last) == batch_id


def mark_applied(redis: Any, child_id: int, batch_id: str) -> None:
    redis.set(APPLIED_KEY.format(child_id=child_id), batch_id, ex=APPLIED_TTL)
