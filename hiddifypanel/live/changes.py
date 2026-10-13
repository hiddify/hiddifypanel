"""What changed in the panel, as tags on one Redis channel: the tables a commit wrote (``user``, ``domain``, ``tls_store``…)
and named events of things outside the database (``cert``, ``apply``, ``cfgtest:<job>``, ``nodejob:<job>``).

Every commit publishes the tables it wrote (``after_flush`` notes them, ``after_commit`` publishes); code that writes with raw
SQL or keeps state elsewhere calls ``publish`` itself. In the ASGI process a single subscription (``hub``) counts the tags, and
whoever waits for some of them — the live channel of the admin pages (channel.py), the nodes' WebSocket — is woken.

Publishing never fails the caller: a missed tag only means the waiter looks again on its own timer.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import threading
import time
from collections.abc import Iterable
from typing import Any

import redis
from loguru import logger
from sqlalchemy import event, update
from sqlalchemy.orm import Session

CHANNEL = "hiddify:changes"
#: Publishing is done in the commit of every request: a Redis that hangs must not hang them.
PUBLISH_TIMEOUT = 0.5
#: Accounts written longer ago than this in a transaction get the commit's time (see ``_restamp_accounts``).
LONG_TRANSACTION = 30.0

_publisher: redis.Redis | None = None
_publisher_lock = threading.Lock()


def _client() -> redis.Redis:
    global _publisher
    with _publisher_lock:
        if _publisher is None:
            _publisher = redis.from_url(os.environ["REDIS_URI_MAIN"], socket_timeout=PUBLISH_TIMEOUT, socket_connect_timeout=PUBLISH_TIMEOUT)
        return _publisher


def publish(tags: Iterable[str]) -> None:
    wanted = sorted({t for t in tags if t})
    if not wanted:
        return
    try:
        _client().publish(CHANNEL, json.dumps(wanted))
    except Exception as e:  # noqa: BLE001
        logger.debug(f"could not publish changes {wanted}: {e}")


# --------------------------------------------------------------------------- the tables of each commit


def _is_account(obj: object) -> bool:
    from hiddifypanel.models.base_account import BaseAccount

    return isinstance(obj, BaseAccount)


@event.listens_for(Session, "after_flush")
def _note_tables(session: Session, _flush_context: Any) -> None:
    tables: set[str] = session.info.setdefault("changed_tables", set())
    for obj in (*session.new, *session.dirty, *session.deleted):
        table = getattr(obj, "__tablename__", None)
        if table:
            tables.add(table)
        if _is_account(obj) and obj not in session.deleted:
            written: dict[type, set[int]] = session.info.setdefault("accounts_written", {})
            written.setdefault(type(obj), set()).add(obj.id)  # type: ignore[attr-defined]
            session.info.setdefault("accounts_first_flush", time.monotonic())


@event.listens_for(Session, "before_commit")
def _restamp_accounts(session: Session) -> None:
    """``last_modified_time`` is set when a change is flushed, and becomes visible at the commit: the nodes look back two minutes
    for changes that commit late (sync_feed.OVERLAP), so the accounts of a long transaction (a restore, an import) get the
    time of its commit."""
    first = session.info.get("accounts_first_flush")
    if first is None or time.monotonic() - first < LONG_TRANSACTION:
        return
    now = datetime.datetime.now()
    for cls, ids in session.info.get("accounts_written", {}).items():
        ordered = sorted(ids)
        for i in range(0, len(ordered), 1000):
            stmt = update(cls).where(cls.id.in_(ordered[i : i + 1000])).values(last_modified_time=now)
            session.execute(stmt.execution_options(synchronize_session=False))


def _forget(session: Session) -> None:
    for key in ("changed_tables", "accounts_written", "accounts_first_flush"):
        session.info.pop(key, None)


@event.listens_for(Session, "after_commit")
def _publish_tables(session: Session) -> None:
    tables = session.info.pop("changed_tables", None)
    _forget(session)
    if tables:
        publish(tables)


@event.listens_for(Session, "after_rollback")
def _forget_tables(session: Session) -> None:
    _forget(session)


# --------------------------------------------------------------------------- waiting for them (ASGI process)


class Hub:
    """Counts each tag published since this process started; waiters compare counts (``versions``) instead of queueing events."""

    #: Per-job tags (``cfgtest:<job>``…) come and go: the counts are forgotten past this many (a waiter then wakes once more).
    MAX_TAGS = 5000

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.total = 0
        self._cond: asyncio.Condition | None = None
        self._task: asyncio.Task[None] | None = None
        self._ready: asyncio.Event | None = None

    def versions(self, tags: Iterable[str]) -> tuple[int, ...]:
        return tuple(self.counts.get(t, 0) for t in tags)

    def _start(self) -> asyncio.Condition:
        if self._cond is None:
            self._cond = asyncio.Condition()
            self._ready = asyncio.Event()
        if self._task is None or self._task.done():
            self._task = asyncio.get_running_loop().create_task(self._listen())
        return self._cond

    async def _listen(self) -> None:
        import redis.asyncio as aioredis

        while True:
            client = aioredis.from_url(os.environ["REDIS_URI_MAIN"])
            try:
                async with client.pubsub() as pubsub:
                    await pubsub.subscribe(CHANNEL)
                    if self._ready is not None:
                        self._ready.set()
                    async for message in pubsub.listen():
                        if message.get("type") == "message":
                            try:
                                tags = json.loads(message["data"])
                            except ValueError:
                                continue
                            await self.bump(tags if isinstance(tags, list) else [])
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                logger.warning(f"changes: Redis subscription lost ({e}); waiters fall back to their timers")
                await asyncio.sleep(5)
            finally:
                await client.aclose()

    async def bump(self, tags: Iterable[str]) -> None:
        cond = self._start()
        async with cond:
            if len(self.counts) > self.MAX_TAGS:
                self.counts = {t: n for t, n in self.counts.items() if ":" not in t}
            for tag in tags:
                self.counts[str(tag)] = self.counts.get(str(tag), 0) + 1
            self.total += 1
            cond.notify_all()

    async def subscribed(self) -> None:
        """Until the Redis subscription is up: changes published from then on are counted."""
        self._start()
        assert self._ready is not None
        await self._ready.wait()

    def start(self) -> None:
        """Subscribe now (call from the event loop), so that changes published from here on are counted."""
        self._start()

    async def wait(self, tags: Iterable[str], seen: tuple[int, ...], timeout: float) -> bool:
        """Until one of ``tags`` was published after ``seen`` (from ``versions``), at most ``timeout`` seconds; whether one was."""
        tags = tuple(tags)
        cond = self._start()
        async with cond:
            try:
                await asyncio.wait_for(cond.wait_for(lambda: self.versions(tags) != seen), timeout)
                return True
            except TimeoutError:
                return False

    def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None
        self._cond = None
        self._ready = None


hub = Hub()
