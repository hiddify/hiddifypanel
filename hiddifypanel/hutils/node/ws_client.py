"""The node's end of the WebSocket to its parent (see ws_server.py): a task of the ASGI app that keeps the connection open while
this panel is a node, writes what the parent sends and confirms each batch, and makes its accounts the parent's when the
parent sends its inventory (``sync_feed.reconcile_*``).

The node only connects out, on the parent's addresses in the order ``endpoints`` gives them (direct, relay, CDN), over a WebSocket
or — where a proxy or CDN on the way does not pass WebSockets — a streamed response plus POSTs (links.py). While neither
can be used (an older parent answers 404, a proxy on the way does not pass WebSockets…) the node takes the parent's
users over HTTP instead (``child.sync_with_parent``), at most every ``HTTP_SYNC_EVERY`` seconds.

One process of the panel runs it (a Redis lock): with several granian workers they would all write the same batches.
"""

from __future__ import annotations

import asyncio
import os
import random
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from loguru import logger

from hiddifypanel.live.app_thread import in_app

from . import links, sync_status, ws_proto
from .sync_status import SyncKind, SyncSource

if TYPE_CHECKING:
    from .sync_feed import Applied
from .links import Link, Refused

#: The ways to the parent (links.py), tried in this order (the stream first once a WebSocket was refused).
OPENERS = {"websocket": links.websocket, "stream": links.stream}


def _is_disconnect(e: Exception) -> bool:
    from websockets.exceptions import ConnectionClosed

    return isinstance(e, ConnectionClosed | ConnectionError) or type(e).__name__ in {"ReadError", "RemoteProtocolError", "StreamClosed"}

MAX_BACKOFF = 60.0
#: The parent answered that it does not know this call (or this node): asking every minute would not change that.
REFUSED_BACKOFF = 600.0
WELCOME_TIMEOUT = 30.0
#: Without the WebSocket for this long, the users come over HTTP; again every HTTP_SYNC_EVERY while it stays so.
HTTP_SYNC_AFTER = 120.0
HTTP_SYNC_EVERY = 600.0
LOCK_KEY = "node:ws:client"
LOCK_TTL = 90

_connected = False
_loop: asyncio.AbstractEventLoop | None = None
_wake: asyncio.Event | None = None
_outbox: asyncio.Queue[dict[str, Any]] | None = None
#: For the WebSocket test of the Actions page (live/debug.py).
_status: dict[str, Any] = {"running": False, "host": "", "connected_since": None, "last_batch_at": None, "rows": 0, "last_error": "", "next_try_in": None, "last_http_sync": None, "transport": ""}


def connected() -> bool:
    """The WebSocket to the parent is open: every change of the parent comes over it without asking."""
    return _connected


def status() -> dict[str, Any]:
    return {**_status, "connected": _connected}


def wake() -> None:
    """Try to connect now (this panel just became a node). Safe from any thread."""
    if _loop is not None and _wake is not None:
        _loop.call_soon_threadsafe(_wake.set)


def request_inventory() -> bool:
    """Ask the parent for its inventory now ("Sync now" on the parent): what differs is put right. Safe from any thread;
    False when the WebSocket is not open."""
    loop, outbox = _loop, _outbox
    if not _connected or loop is None or outbox is None:
        return False
    loop.call_soon_threadsafe(outbox.put_nowait, {"type": "inventory_please"})
    return True


@dataclass(frozen=True)
class _Target:
    #: the parent's addresses, best first (``https://host/<admin path>/``)
    bases: list[str]
    apikey: str
    cursor: ws_proto.CursorJson


def _target() -> _Target | None:
    from hiddifypanel.models import ConfigEnum, hconfig

    from . import child, endpoints, shared, sync_feed

    if not shared.is_child():
        return None
    base = child._parent_base_url()
    if not base:
        return None
    bases = list(endpoints.live_first(endpoints.alternates(base)))
    return _Target(bases, str(hconfig(ConfigEnum.unique_id)), sync_feed.stored_cursor().to_json())


def _welcomed(welcome: dict[str, Any]) -> None:
    from . import endpoints

    hosts = welcome.get("parent_hosts")
    if isinstance(hosts, list) and hosts:
        endpoints.remember_parent_hosts(endpoints.PanelHost(str(h["domain"]), str(h["mode"])) for h in hosts if isinstance(h, dict) and h.get("domain"))


def _after_batches(users_changed: bool, outbounds_changed: bool, admins_changed: bool) -> None:
    from hiddifypanel.cache import cache
    from hiddifypanel.panel import hiddify

    from . import child

    if users_changed or outbounds_changed or admins_changed:
        cache.invalidate_all_cached_functions()
    if users_changed:
        logger.info("node-ws: users from the parent changed who is active: applying users")
        hiddify.quick_apply_users()
    if outbounds_changed:
        child._apply_server_config()


def _note_batch(batch: ws_proto.ChangesMessage, applied: Applied) -> None:
    """A change-feed batch, in the sync log; the WebSocket state goes with it (it runs in this process only)."""
    if applied.admins:
        sync_status.record(SyncKind.admins, SyncSource.ws_feed, applied.admins, items=batch.get("admins"))
    if applied.users:
        sync_status.record(SyncKind.users, SyncSource.ws_feed, applied.users, items=batch.get("users"), more=bool(batch.get("more")))
    if batch.get("outbounds") is not None:
        sync_status.record(SyncKind.outbounds, SyncSource.ws_feed, len(batch["outbounds"]), items=batch["outbounds"])
    sync_status.save_ws(status())


def _http_sync() -> bool:
    from . import child

    return child.sync_with_parent(pull_users=True)


def _hold_lock() -> bool:
    """This process runs the client (the lock is its own, or free)."""
    from hiddifypanel.cache import redis_client

    me = str(os.getpid()).encode()
    try:
        if redis_client.set(LOCK_KEY, me, nx=True, ex=LOCK_TTL):
            return True
        if redis_client.get(LOCK_KEY) == me:
            redis_client.expire(LOCK_KEY, LOCK_TTL)
            return True
        return False
    except Exception:  # noqa: BLE001  without Redis there is nothing to share it with
        return True


@dataclass
class _Pending:
    """What the batches written so far need done once (done even when the connection ends half way)."""

    users: bool = False
    outbounds: bool = False
    admins: bool = False

    def any(self) -> bool:
        return self.users or self.outbounds or self.admins


@dataclass
class _Session:
    link: Link
    host: str
    pending: _Pending = field(default_factory=_Pending)
    rows: int = 0
    #: It got everything once: a dropped connection after that is tried again at once.
    up_to_date: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def send(self, message: dict[str, Any]) -> None:
        async with self.lock:
            await self.link.send(self.link.codec.encode(message))

    async def recv(self) -> dict[str, Any]:
        return self.link.codec.decode(await self.link.recv())

    async def messages(self) -> AsyncIterator[dict[str, Any]]:
        async for frame in self.link.frames():
            yield self.link.codec.decode(frame)


class _Client:
    def __init__(self, flask_app: Any) -> None:
        self.app = flask_app
        self.failures = 0
        self.disconnected_since = time.monotonic()
        self.last_http_sync = 0.0
        self.prefer_stream = False

    async def run_forever(self) -> None:
        global _loop, _wake
        _loop = asyncio.get_running_loop()
        _wake = asyncio.Event()
        _status["running"] = True
        next_try = 0.0  # when to connect again; the loop wakes at least every LOCK_TTL / 3 to keep the lock
        while True:
            try:
                target = await in_app(self.app, _target)
                holder = target is not None and await asyncio.to_thread(_hold_lock)
                if target is None or not holder:
                    self.disconnected_since = time.monotonic()
                else:
                    if time.monotonic() >= next_try:
                        next_try = time.monotonic() + await self._connect_any(target)
                    await self._http_sync_if_needed()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("node-ws: failed")
                _status["last_error"] = f"{type(e).__name__}: {e}"
                sync_status.save_ws(status())
                next_try = time.monotonic() + self._backoff()
            _status["next_try_in"] = round(max(0.0, next_try - time.monotonic()), 1)
            _wake.clear()
            try:
                await asyncio.wait_for(_wake.wait(), min(LOCK_TTL / 3, max(1.0, next_try - time.monotonic())))
                next_try = 0.0  # woken: this panel just became a node, try now
            except TimeoutError:
                pass

    def _backoff(self) -> float:
        self.failures += 1
        return min(MAX_BACKOFF, 2.0 ** min(self.failures, 6)) * random.uniform(0.8, 1.2)

    async def _http_sync_if_needed(self) -> None:
        """The WebSocket has not worked for a while: take the parent's users over HTTP, as before it existed."""
        now = time.monotonic()
        if _connected or now - self.disconnected_since < HTTP_SYNC_AFTER or now - self.last_http_sync < HTTP_SYNC_EVERY:
            return
        self.last_http_sync = now
        logger.info("node-ws: no WebSocket to the parent for a while: taking its users over HTTP")
        if await in_app(self.app, _http_sync):
            _status["last_http_sync"] = time.time()

    async def _connect_any(self, target: _Target) -> float:
        """Connect on the first address and transport that answers and stay until the connection ends; seconds to wait before the
        next try. A WebSocket first; where it is refused (a proxy or CDN that does not pass WebSockets) the streamed transport."""
        refused: list[str] = []
        for base in target.bases:
            host = base.split("://", 1)[-1].split("/", 1)[0]
            for kind in self._kinds():
                session: _Session | None = None
                try:
                    async with OPENERS[kind](base, target.apikey) as link:
                        session = _Session(link, host)
                        await self._run(session, target)
                    return 1.0
                except asyncio.CancelledError:
                    raise
                except Refused as e:
                    refused.append(f"{host} ({kind}): {e}")
                    _status["last_error"] = refused[-1]
                    if kind == "websocket":
                        self.prefer_stream = True  # the way there does not pass WebSockets: start with the stream next time
                    continue
                except Exception as e:  # noqa: BLE001  connection errors of any kind: the next transport, then the next address
                    _status["last_error"] = f"{host} ({kind}): {type(e).__name__}: {e}"
                    if session is None:
                        logger.warning(f"node-ws: could not connect to {host} ({kind}): {type(e).__name__}: {e}")
                        continue
                    logger.opt(exception=None if _is_disconnect(e) else e).warning(f"node-ws: connection to {host} ({kind}) ended: {type(e).__name__}: {e}")
                    # At once only after a session that got everything (a dropped connection); one that failed before that (the
                    # parent closed it on an error, a batch could not be written) waits longer each time.
                    return 1.0 if session.up_to_date else self._backoff()
        if refused and len(refused) == len(target.bases) * len(self._kinds()):
            logger.warning(f"node-ws: the parent refused every way in ({'; '.join(refused)}); its users come over HTTP meanwhile, trying again in {REFUSED_BACKOFF / 60:.0f} min")
            return REFUSED_BACKOFF
        return self._backoff()

    def _kinds(self) -> tuple[str, ...]:
        return ("stream", "websocket") if self.prefer_stream else ("websocket", "stream")

    async def _run(self, session: _Session, target: _Target) -> None:
        global _connected, _outbox

        await session.send({"type": "hello", "version": ws_proto.VERSION, "cursor": target.cursor})
        welcome = await asyncio.wait_for(session.recv(), WELCOME_TIMEOUT)
        if welcome["type"] != "welcome":
            raise ws_proto.ProtocolError(f"expected welcome, got {welcome['type']}")
        await in_app(self.app, _welcomed, welcome)
        logger.info(f"node-ws: connected to the parent {session.host} ({session.link.kind})")
        outbox: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        _connected, _outbox = True, outbox
        _status.update(host=session.host, transport=session.link.kind, connected_since=time.time(), last_error="", next_try_in=None)
        sync_status.save_ws(status())
        talker = asyncio.get_running_loop().create_task(self._talk(session, outbox))
        try:
            async for message in session.messages():
                await self._received(session, message)
        finally:
            _connected, _outbox = False, None
            self.disconnected_since = time.monotonic()
            sync_status.save_ws(status())
            talker.cancel()
            if session.pending.any():  # batches written before the connection ended still need it
                await in_app(self.app, _after_batches, session.pending.users, session.pending.outbounds, session.pending.admins)

    async def _talk(self, session: _Session, outbox: asyncio.Queue[dict[str, Any]]) -> None:
        """What this node says on its own: requests (``request_inventory``) and a heartbeat the parent waits for."""
        while True:
            try:
                message = await asyncio.wait_for(outbox.get(), ws_proto.HEARTBEAT)
            except TimeoutError:
                message = {"type": "ping"}
            await session.send(message)

    async def _flush_pending(self, session: _Session) -> None:
        pending, session.pending = session.pending, _Pending()
        if pending.any():
            await in_app(self.app, _after_batches, pending.users, pending.outbounds, pending.admins)

    async def _received(self, session: _Session, message: dict[str, Any]) -> None:
        from . import sync_feed

        kind = message["type"]
        if kind == "changes":
            batch = ws_proto.parse_changes(message)
            applied = await in_app(self.app, sync_feed.apply_batch, batch)
            await session.send({"type": "ack", "cursor": batch["cursor"]})
            session.rows += applied.users + applied.admins
            _status["rows"] += applied.users + applied.admins
            _status["last_batch_at"] = time.time()
            await in_app(self.app, _note_batch, batch, applied)
            session.pending.users |= applied.users_changed
            session.pending.outbounds |= applied.outbounds_changed
            session.pending.admins |= applied.admins > 0
            if not batch["more"]:
                logger.info(f"node-ws: up to date with the parent ({session.rows} rows)")
                await self._flush_pending(session)
                session.rows = 0
                session.up_to_date = True
                self.failures = 0
        elif kind == "inventory":
            inventory = ws_proto.parse_inventory(message)
            admins = await in_app(self.app, sync_feed.reconcile_admins, inventory["admins"])
            sync_status.record(SyncKind.admins, SyncSource.inventory, len(inventory["admins"]), items=inventory["admins"], removed=admins.removed, missing=len(admins.missing))
            if admins.removed:
                logger.info(f"node-ws: {admins.removed} admins are no longer on the parent: removed here")
                session.pending.admins = True
                await self._flush_pending(session)
            if admins.missing:
                await session.send({"type": "resend", "users": [], "admins": admins.missing})
            if await in_app(self.app, sync_feed.local_users_digest) != inventory["users_digest"]:
                await session.send({"type": "users_list_please"})
        elif kind == "users_list":
            parent_users = ws_proto.str_list(message.get("users", []), "users_list.users")
            users = await in_app(self.app, sync_feed.reconcile_users, parent_users)
            sync_status.record(SyncKind.users, SyncSource.inventory, len(parent_users), items=parent_users, removed=users.removed, missing=len(users.missing))
            if users.removed:
                logger.info(f"node-ws: {users.removed} users are no longer on the parent: removed here")
                session.pending.users = True
                await self._flush_pending(session)
            if users.missing:
                logger.info(f"node-ws: {len(users.missing)} users of the parent were missing here: asked for again")
                await session.send({"type": "resend", "users": users.missing, "admins": []})


async def run_forever(flask_app: Any) -> None:
    await _Client(flask_app).run_forever()
