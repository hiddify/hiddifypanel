"""The live channel of the admin pages: one WebSocket per browser tab (``/<admin proxy path>/api/v2/admin/live/``) that brings
the pages what they used to ask for again and again.

Signed in like the pages' own requests (the session cookie of the handshake). A handshake from another site's page is
refused (``Origin``).

The page sends JSON messages, each with its own ``id``:

- ``watch`` {path, query, interval, tags}: the answer of ``GET <admin API>/<path>`` now and whenever it changes. The server asks
  the endpoint itself (dispatch.py: the same sign in and permissions as the page's request) every ``interval`` seconds, and at
  once when one of ``tags`` is published (changes.py: table names, ``cert``…); it sends the answer only when it differs.
- ``stream`` {topic, params}: a log or job followed from a position (``STREAMS``): new data as it comes, then ``end``.
- ``call`` {method, params}: one answer: ``request`` {method, path, query, body} (a request of the page, see ``_request``),
  ``ping``, and the WebSocket test of the Actions page.
- ``stop`` {id}.

The server answers ``data`` {id, data}, ``result`` {id, data}, ``error`` {id, status, message} and ``end`` {id}.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
from collections.abc import AsyncIterator, Callable
from typing import Any
from urllib.parse import urlparse

from loguru import logger

from hiddifypanel.asgi_types import Receive, Send
from hiddifypanel.hutils.node.ws_proto import ProtocolError

from . import changes
from .app_thread import in_app
from .dispatch import Answer, BadPath, Caller, request
from .transport import Connection, Gone, JsonCodec, StreamConnection, WebSocketConnection, run_with_stream
from .transport import handle_post as post_to_stream
from .transport.stream import refuse

CLOSE_UNAUTHORIZED = 4403
CLOSE_BAD_ORIGIN = 4401
MAX_SUBSCRIPTIONS = 32
#: Calls answered at once per connection (the rest wait): an echo of megabytes must not pile up.
MAX_CALLS = 4
#: A burst of changes (a bulk edit) asks again once, not once per change.
MIN_GAP = 1.0

type Json = Any


class Context:
    def __init__(self, flask_app: Any, caller: Caller, me: dict[str, Any], conn: Connection) -> None:
        self.app = flask_app
        self.caller = caller
        self.me = me
        self.conn = conn

    @property
    def super_admin(self) -> bool:
        return self.me.get("mode") == "super_admin"

    async def send(self, message: dict[str, Any]) -> None:
        try:
            await self.conn.send(message)
        except Gone:
            pass  # the page left: its subscriptions are being stopped

    async def get(self, path: str, query: dict[str, Any] | None = None) -> Answer:
        return await request(self.app, self.caller, "GET", path, query)


class Stop(Exception):
    """The subscription is over (the endpoint refused, or the stream ended)."""


async def _sleep_or_change(tags: list[str], seen: tuple[int, ...], timeout: float) -> None:
    if tags:
        await changes.hub.wait(tags, seen, timeout)
    else:
        await asyncio.sleep(timeout)


def _clamp(value: object, low: float, high: float, default: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        return default
    try:
        return max(low, min(high, float(value)))
    except ValueError:
        return default


def _tags(raw: object) -> list[str]:
    return [str(t)[:64] for t in raw][:20] if isinstance(raw, list) else []


# --------------------------------------------------------------------------- watch


async def _watch(ctx: Context, sid: str, params: dict[str, Any]) -> AsyncIterator[Json]:
    path = str(params.get("path") or "")
    query = params.get("query") if isinstance(params.get("query"), dict) else None
    interval = _clamp(params.get("interval"), 1, 3600, 30)
    tags = _tags(params.get("tags"))
    last = ""
    while True:
        seen = changes.hub.versions(tags)
        answer = await ctx.get(path, query)
        if answer.status in (401, 403, 404, 405):
            raise Stop(answer.status, answer.message())
        if answer.status == 200:
            digest = hashlib.sha1(answer.body).hexdigest()
            if digest != last:
                last = digest
                yield answer.data()
        else:  # the endpoint failed this time: say so, and ask again later
            await ctx.send({"type": "error", "id": sid, "status": answer.status, "message": answer.message(), "retrying": True})
        await _sleep_or_change(tags, seen, interval)
        await asyncio.sleep(MIN_GAP)


# --------------------------------------------------------------------------- streams


async def _apply_log(ctx: Context, _sid: str, params: dict[str, Any]) -> AsyncIterator[Json]:
    """The log of an Apply page run from ``offset`` (apply/log/): each new piece, until it says it finished."""
    offset = int(params.get("offset") or 0)
    since = params.get("since") or None
    query: dict[str, Any] = {"file": params.get("file"), "since": since}
    last_progress: object = None
    while True:
        answer = await ctx.get("apply/log/", {**query, "offset": offset})
        if answer.status != 200:
            raise Stop(answer.status, answer.message())
        chunk = answer.data()
        if not isinstance(chunk, dict):
            raise Stop(502, "not a log")
        changed = chunk.get("text") or chunk.get("reset") or chunk.get("finished") or chunk.get("progress") != last_progress or not chunk.get("started")
        if changed:
            last_progress = chunk.get("progress")
            yield chunk
        if chunk.get("finished"):
            return
        offset = int(chunk.get("offset") or 0)
        await asyncio.sleep(0.1 if chunk.get("text") else 0.5)


async def _config_tester(ctx: Context, _sid: str, params: dict[str, Any]) -> AsyncIterator[Json]:
    """The events of a config test from ``after`` (config-tester/<job>/): each page as soon as the job adds to it."""
    job = str(params.get("job") or "")
    after = int(params.get("after") or 0)
    tags = [f"cfgtest:{job}"]
    while True:
        seen = changes.hub.versions(tags)
        answer = await ctx.get(f"config-tester/{job}/", {"after": after})
        if answer.status != 200:
            raise Stop(answer.status, answer.message())
        page = answer.data()
        if not isinstance(page, dict):
            raise Stop(502, "not a test page")
        if page.get("events") or page.get("done") or page.get("lost"):
            yield page
        if page.get("done") or page.get("lost"):
            return
        if page.get("events"):
            after = int(page.get("next") or after)
            continue
        await _sleep_or_change(tags, seen, 3.0)  # the job beats every few seconds: "lost" is seen within that


async def _node_job(ctx: Context, _sid: str, params: dict[str, Any]) -> AsyncIterator[Json]:
    """A node registration job (nodes/jobs/<job>/): its state once it is done or failed."""
    job = str(params.get("job") or "")
    tags = [f"nodejob:{job}"]
    while True:
        seen = changes.hub.versions(tags)
        answer = await ctx.get(f"nodes/jobs/{job}/")
        if answer.status != 200:
            raise Stop(answer.status, answer.message())
        state = answer.data()
        if not isinstance(state, dict):
            raise Stop(502, "not a job state")
        if state.get("state") != "running":
            yield state  # reading it marks it delivered: what restarts the services waits for that (async_job.after_fetched)
            return
        await _sleep_or_change(tags, seen, 5.0)


async def _changes(ctx: Context, _sid: str, params: dict[str, Any]) -> AsyncIterator[Json]:
    """The change tags published while subscribed (the WebSocket test)."""
    if not ctx.super_admin:
        raise Stop(403, "super admins only")
    tags = _tags(params.get("tags")) or ["debug"]
    seen = changes.hub.versions(tags)
    while True:
        if await changes.hub.wait(tags, seen, 60.0):
            now = changes.hub.versions(tags)
            yield {"tags": [t for t, a, b in zip(tags, seen, now, strict=True) if a != b], "server_time": time.time()}
            seen = now


async def _ticks(ctx: Context, _sid: str, params: dict[str, Any]) -> AsyncIterator[Json]:
    """Messages the server sends on its own, ``count`` of them every ``interval_ms`` (the WebSocket test: is it a push, how
    regular is it), then the end."""
    if not ctx.super_admin:
        raise Stop(403, "super admins only")
    count = int(_clamp(params.get("count"), 1, 100, 5))
    interval = _clamp(params.get("interval_ms"), 50, 10_000, 1000) / 1000
    for n in range(1, count + 1):
        await asyncio.sleep(interval)
        yield {"n": n, "count": count, "server_time": time.time()}


STREAMS: dict[str, Callable[[Context, str, dict[str, Any]], AsyncIterator[Json]]] = {
    "apply.log": _apply_log,
    "config-tester": _config_tester,
    "node.job": _node_job,
    "changes": _changes,
    "ticks": _ticks,
}


# --------------------------------------------------------------------------- calls

REQUEST_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})


async def _request(ctx: Context, params: dict[str, Any]) -> Json:
    """A request of the page sent over the socket (``liveRequest``): the endpoint answers it as it would over HTTP (sign in and
    permissions included); its status comes back with the answer, so an error of the endpoint is not an error of the call."""
    method = str(params.get("method") or "GET").upper()
    if method not in REQUEST_METHODS:
        raise Stop(400, f"not a request method: {method}")
    query = params.get("query") if isinstance(params.get("query"), dict) else None
    answer = await request(ctx.app, ctx.caller, method, str(params.get("path") or ""), query, params.get("body"))
    return {"status": answer.status, "data": answer.data()}




async def _call(ctx: Context, method: str, params: dict[str, Any]) -> Json:
    from . import debug

    if method == "ping":
        return {"t": params.get("t"), "server_time": time.time()}
    if method == "request":
        return await _request(ctx, params)
    if not ctx.super_admin:
        raise Stop(403, "super admins only")
    if method == "hello":
        return debug.hello()
    if method == "echo":
        size = int(_clamp(params.get("size"), 0, debug.MAX_ECHO, 0))
        return {"t": params.get("t"), "size": size, "data": "x" * size}
    if method == "publish":
        await asyncio.to_thread(changes.publish, ["debug"])
        return {"server_time": time.time()}
    if method == "status":
        return await in_app(ctx.app, debug.status)
    if method == "feed":
        return await in_app(ctx.app, debug.feed_preview, int(_clamp(params.get("limit"), 1, debug.MAX_FEED_LIMIT, 100)))
    raise Stop(404, f"unknown method {method!r}")


# --------------------------------------------------------------------------- the connection


async def _run_subscription(ctx: Context, sid: str, source: AsyncIterator[Json]) -> None:
    try:
        async for data in source:
            await ctx.send({"type": "data", "id": sid, "data": data})
        await ctx.send({"type": "end", "id": sid})
    except asyncio.CancelledError:
        raise
    except Stop as e:
        status, message = (e.args + (0, ""))[:2]
        await ctx.send({"type": "error", "id": sid, "status": status, "message": message})
        await ctx.send({"type": "end", "id": sid})
    except BadPath as e:
        await ctx.send({"type": "error", "id": sid, "status": 400, "message": str(e)})
        await ctx.send({"type": "end", "id": sid})
    except Exception as e:  # noqa: BLE001
        logger.exception(f"live: subscription {sid} failed")
        await ctx.send({"type": "error", "id": sid, "status": 500, "message": f"{type(e).__name__}: {e}"})
        await ctx.send({"type": "end", "id": sid})


async def _answer_call(ctx: Context, sid: str, method: str, params: dict[str, Any]) -> None:
    try:
        await ctx.send({"type": "result", "id": sid, "data": await _call(ctx, method, params)})
    except Stop as e:
        status, message = (e.args + (0, ""))[:2]
        await ctx.send({"type": "error", "id": sid, "status": status, "message": message})
    except BadPath as e:
        await ctx.send({"type": "error", "id": sid, "status": 400, "message": str(e)})
    except Exception as e:  # noqa: BLE001
        await ctx.send({"type": "error", "id": sid, "status": 500, "message": f"{type(e).__name__}: {e}"})


def _origin_ok(scope: dict[str, Any]) -> bool:
    """A page of another site may open a WebSocket here with this browser's cookies: only this panel's own pages may."""
    headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers") or []}
    origin = headers.get("origin")
    if not origin:
        return True  # not a browser (a browser always sends it)
    host = (headers.get("x-forwarded-host") or headers.get("host") or "").split(",")[0].strip()
    # Host names only: a proxy in front may drop the port of a non-443 address from Host.
    return (urlparse(origin).hostname or "") == (urlparse(f"//{host}").hostname or "") or os.environ.get("HIDDIFY_LIVE_ANY_ORIGIN") == "1"


#: The channel name of the streamed transport's sessions (live/transport/stream.py).
STREAM_CHANNEL = "admin-live"


async def _authenticate(flask_app: Any, proxy_path: str, scope: dict[str, Any]) -> tuple[Caller, dict[str, Any]] | int:
    """Who opens the channel (signed in like the page's own requests), or the close code that refuses it."""
    if not _origin_ok(scope):
        return CLOSE_BAD_ORIGIN
    caller = Caller.from_scope(scope, proxy_path)
    me = await request(flask_app, caller, "GET", "me/")
    data = me.data()
    if me.status != 200 or not isinstance(data, dict):
        return CLOSE_UNAUTHORIZED
    return caller, data


async def handle(flask_app: Any, proxy_path: str, scope: dict[str, Any], receive: Receive, send: Send) -> None:
    """The channel over a WebSocket (``/<admin path>/api/v2/admin/live/``)."""
    if (await receive())["type"] != "websocket.connect":
        return
    who = await _authenticate(flask_app, proxy_path, scope)
    if isinstance(who, int):
        await send({"type": "websocket.close", "code": who})  # before accept: the browser sees a refused handshake
        return
    await send({"type": "websocket.accept"})
    conn = WebSocketConnection(receive, send, JsonCodec())
    try:
        await serve(Context(flask_app, *who, conn))
    finally:
        await conn.close()


async def handle_stream(flask_app: Any, proxy_path: str, scope: dict[str, Any], receive: Receive, send: Send) -> None:
    """The channel over a streamed response plus POSTs (``…/live/stream/``, ``…/live/<session>/``): rides the page's HTTP/3 or
    HTTP/2 connection."""
    who = await _authenticate(flask_app, proxy_path, scope)
    if isinstance(who, int):
        return await refuse(send, 401 if who == CLOSE_UNAUTHORIZED else 403, "not signed in" if who == CLOSE_UNAUTHORIZED else "another site")
    conn = StreamConnection(STREAM_CHANNEL, JsonCodec())
    await run_with_stream(conn, asyncio.get_running_loop().create_task(serve(Context(flask_app, *who, conn))), receive, send)


async def handle_post(scope: dict[str, Any], receive: Receive, send: Send, session: str) -> None:
    await post_to_stream(scope, receive, send, STREAM_CHANNEL, session, allowed=_origin_ok)


async def serve(ctx: Context) -> None:
    """The page's messages until it leaves: whatever carries them."""
    conn = ctx.conn
    changes.hub.start()
    tasks: dict[str, asyncio.Task[None]] = {}
    calls: set[asyncio.Task[None]] = set()
    call_slots = asyncio.Semaphore(MAX_CALLS)

    async def answer_call(sid: str, method: str, params: dict[str, Any]) -> None:
        async with call_slots:
            await _answer_call(ctx, sid, method, params)

    await ctx.send({"type": "hello", "server_time": time.time(), "pid": os.getpid()})
    try:
        while True:
            try:
                message = conn.poll()
            except ProtocolError:
                continue  # not a message: skipped
            except Gone:
                return
            if message is None:
                await conn.wait()
                continue
            sid = str(message.get("id") or "")
            kind = message.get("type")
            raw_params = message.get("params")
            params: dict[str, Any] = raw_params if isinstance(raw_params, dict) else {}
            for done in [k for k, t in tasks.items() if t.done()]:
                del tasks[done]
            if kind == "stop":
                if (task := tasks.pop(sid, None)) is not None:
                    task.cancel()
                continue
            if kind == "call":
                call = asyncio.get_running_loop().create_task(answer_call(sid, str(message.get("method") or ""), params))
                calls.add(call)
                call.add_done_callback(calls.discard)
                continue
            if kind not in ("watch", "stream") or not sid:
                await ctx.send({"type": "error", "id": sid, "status": 400, "message": f"unknown message {kind!r}"})
                await ctx.send({"type": "end", "id": sid})
                continue
            if len(tasks) >= MAX_SUBSCRIPTIONS and sid not in tasks:
                await ctx.send({"type": "error", "id": sid, "status": 429, "message": "too many subscriptions"})
                await ctx.send({"type": "end", "id": sid})  # the page goes on over HTTP
                continue
            if kind == "watch":
                source = _watch(ctx, sid, params)
            elif (topic := STREAMS.get(str(message.get("topic") or ""))) is not None:
                source = topic(ctx, sid, params)
            else:
                await ctx.send({"type": "error", "id": sid, "status": 404, "message": f"unknown topic {message.get('topic')!r}"})
                await ctx.send({"type": "end", "id": sid})
                continue
            if (old := tasks.pop(sid, None)) is not None:
                old.cancel()  # the same id again: the page changed what it watches
            tasks[sid] = asyncio.get_running_loop().create_task(_run_subscription(ctx, sid, source))
    finally:
        for task in [*tasks.values(), *calls]:
            task.cancel()
