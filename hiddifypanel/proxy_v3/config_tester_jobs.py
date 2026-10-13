"""A config test runs as a job on the server, not inside one HTTP request: the page reads its events as they come
(and again after a reload, a dropped connection or a restarted proxy) and the test is not cut with it.

Events are kept in a Redis list, so any panel process can answer for a job. A job whose process went away stops
beating and is reported as lost.
"""

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Iterator
from typing import cast

import redis
from loguru import logger

from hiddifypanel.proxy_v3.config_tester_types import DoneEvent, ErrorEvent, Event, JobPage, QueuedEvent

type RedisClient = redis.Redis[bytes]

TTL = 3600  # a finished job stays readable for an hour
BEAT_TTL = 30  # a running job beats at least every 5 s (the test sends a ping when nothing finishes)
EVENT_NAMES = frozenset({"start", "result", "ping", "queued", "done", "error"})


def _key(job: str, part: str) -> str:
    return f"cfgtest:{job}:{part}"


def new_id() -> str:
    return uuid.uuid4().hex


def is_cancelled(job: str, client: RedisClient) -> bool:
    return bool(client.exists(_key(job, "cancel")))


def cancel(job: str, client: RedisClient) -> None:
    client.set(_key(job, "cancel"), 1, ex=BEAT_TTL * 4)


def _push(job: str, ev: Event, client: RedisClient) -> None:
    key = _key(job, "events")
    client.rpush(key, json.dumps(ev))
    client.expire(key, TTL)
    from hiddifypanel.live import changes

    changes.publish([f"cfgtest:{job}"])  # the live page follows the job without asking again


def create(job: str, first: Event, events: Iterator[Event], client: RedisClient) -> str:
    """Start job ``job`` taking the rest of ``events`` in the background (they stop themselves when it is cancelled).
    ``first`` is already read: it is where the errors are."""
    _push(job, QueuedEvent(event="queued") if first["event"] == "ping" else first, client)
    client.set(_key(job, "beat"), 1, ex=BEAT_TTL)
    threading.Thread(target=_work, args=(job, events, client), daemon=True).start()
    return job


def _work(job: str, events: Iterator[Event], client: RedisClient) -> None:
    try:
        for ev in events:  # to its end: the last event is "done"
            client.set(_key(job, "beat"), 1, ex=BEAT_TTL)
            if ev["event"] != "ping":
                _push(job, ev, client)
    except Exception as e:  # the job reports it and ends  # noqa: BLE001
        logger.exception("config tester job failed")
        try:
            _push(job, ErrorEvent(event="error", error=str(e) or type(e).__name__), client)
            _push(job, DoneEvent(event="done"), client)
        except redis.RedisError:
            logger.exception("config tester job could not report its failure")


def _event(raw: bytes | str) -> Event | None:
    """An event read back from Redis (anything that is not one is left out)."""
    try:
        value: object = json.loads(raw)
    except ValueError:
        return None
    if isinstance(value, dict) and value.get("event") in EVENT_NAMES:
        return cast(Event, value)
    return None


def read(job: str, after: int, limit: int, client: RedisClient) -> JobPage | None:
    """Events from place ``after``; ``None`` when there is no such job (never was, or it expired)."""
    key = _key(job, "events")
    if not client.exists(key):
        return None
    raws = client.lrange(key, after, after + limit - 1)
    events = [ev for ev in (_event(r) for r in raws) if ev is not None]
    done = any(ev["event"] == "done" for ev in events)
    if not raws and not done:  # asked past the end: is the end a "done"?
        last = client.lindex(key, -1)
        done = last is not None and (_event(last) or QueuedEvent(event="queued"))["event"] == "done"
    lost = not done and not client.exists(_key(job, "beat"))
    return JobPage(events=events, next=after + len(raws), done=done, lost=lost)
