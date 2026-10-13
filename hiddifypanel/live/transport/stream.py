"""A ``Connection`` over plain HTTP requests: what the server says is one streamed response (``text/event-stream``: a ``data:``
line per message), what the other side says are POSTs to ``…/<session id>/`` (a JSON array of frames). Both ride whatever the
page already uses — HTTP/3, HTTP/2 or keep-alive HTTP/1.1 — and pass every proxy and CDN, unlike a WebSocket upgrade.

The stream starts with ``event: session`` carrying the session id: only who reads the stream can post to it. A comment line
every ``KEEPALIVE`` seconds keeps proxies (HAProxy ``timeout server``, CDNs) from closing a quiet stream.

Sessions live in this process (the panel runs one granian worker); a POST for a session that is not here is answered 404, and
the client opens a new stream.
"""

from __future__ import annotations

import asyncio
import json
import secrets
from collections.abc import Callable
from typing import Any

from hiddifypanel.asgi_types import Receive, Scope, Send

from .base import Codec, Connection, Frame

KEEPALIVE = 15.0
CLEANUP_TIMEOUT = 5.0
MAX_POST = 16 * 1024 * 1024
HEADERS = [
    (b"content-type", b"text/event-stream; charset=utf-8"),
    (b"cache-control", b"no-store"),
    (b"x-accel-buffering", b"no"),  # nginx: pass each line on at once
]

#: session id -> its connection, while its stream is open
SESSIONS: dict[str, StreamConnection] = {}


class StreamConnection(Connection):
    def __init__(self, channel: str, codec: Codec, ignore: frozenset[str] = frozenset()) -> None:
        super().__init__(codec.as_text(), ignore)
        self.channel = channel
        self.session = secrets.token_urlsafe(24)
        self._out: asyncio.Queue[str | None] = asyncio.Queue()

    async def _write(self, frame: Frame) -> None:
        self._out.put_nowait(frame if isinstance(frame, str) else frame.decode())

    async def close(self, code: int = 1000) -> None:
        self.ended()
        self._out.put_nowait(None)


async def _respond(send: Send, status: int, body: bytes = b"", content_type: bytes = b"application/json") -> None:
    await send({"type": "http.response.start", "status": status, "headers": [(b"content-type", content_type), (b"cache-control", b"no-store")]})
    await send({"type": "http.response.body", "body": body})


async def refuse(send: Send, status: int, message: str) -> None:
    await _respond(send, status, json.dumps({"message": message}).encode())


async def _until_disconnect(receive: Receive, conn: StreamConnection) -> None:
    try:
        while (await receive())["type"] != "http.disconnect":
            pass
    finally:
        conn.ended()


async def serve_stream(conn: StreamConnection, receive: Receive, send: Send) -> None:
    """Write ``conn``'s stream until it ends (the other side left, or ``conn.close()``)."""
    SESSIONS[conn.session] = conn
    watcher = asyncio.get_running_loop().create_task(_until_disconnect(receive, conn))
    try:
        await send({"type": "http.response.start", "status": 200, "headers": HEADERS})
        await send({"type": "http.response.body", "body": f"event: session\ndata: {conn.session}\n\n".encode(), "more_body": True})
        while not conn.closed.is_set():
            out = asyncio.ensure_future(conn._out.get())
            closed = asyncio.ensure_future(conn.closed.wait())
            done, _ = await asyncio.wait({out, closed}, timeout=KEEPALIVE, return_when=asyncio.FIRST_COMPLETED)
            closed.cancel()
            if out not in done:
                out.cancel()
                if not done:
                    await send({"type": "http.response.body", "body": b": keepalive\n\n", "more_body": True})
                continue
            frame = out.result()
            if frame is None:
                break
            await send({"type": "http.response.body", "body": f"data: {frame}\n\n".encode(), "more_body": True})
    finally:
        SESSIONS.pop(conn.session, None)
        watcher.cancel()
        conn.ended()
        try:
            await send({"type": "http.response.body", "body": b"", "more_body": False})
        except Exception:  # noqa: BLE001  the other side is gone
            pass


async def run_with_stream(conn: StreamConnection, serving: asyncio.Task[None], receive: Receive, send: Send) -> None:
    """Write ``conn``'s stream while ``serving`` processes it; when the stream ends, let the processing end on its own (its
    cleanup runs: the connection is gone for it), and cancel it only if it does not within ``CLEANUP_TIMEOUT``."""
    serving.add_done_callback(lambda _: conn.ended())  # the processing ended first: so does the stream
    try:
        await serve_stream(conn, receive, send)
    finally:
        conn.ended()
        try:
            await asyncio.wait_for(asyncio.shield(serving), CLEANUP_TIMEOUT)
        except (TimeoutError, asyncio.CancelledError):
            serving.cancel()
        except Exception:  # noqa: BLE001  the processing failed: it logged it
            pass


async def _read_body(receive: Receive) -> bytes | None:
    """The request body, or None when it is larger than ``MAX_POST``."""
    chunks: list[bytes] = []
    size = 0
    while True:
        event = await receive()
        if event["type"] == "http.disconnect":
            return b""
        chunk = event.get("body") or b""
        size += len(chunk)
        if size > MAX_POST:
            return None
        chunks.append(chunk)
        if not event.get("more_body"):
            return b"".join(chunks)


async def handle_post(scope: Scope, receive: Receive, send: Send, channel: str, session: str, allowed: Callable[[Scope], bool] | None = None) -> None:
    """Frames the other side sends to its session (a JSON array), in order."""
    conn = SESSIONS.get(session)
    if conn is None or conn.channel != channel or conn.closed.is_set():
        return await refuse(send, 404, "no such session (open a new stream)")
    if allowed is not None and not allowed(scope):
        return await refuse(send, 403, "not allowed")
    body = await _read_body(receive)
    if body is None:
        return await refuse(send, 413, "too large")
    try:
        frames: Any = json.loads(body or b"[]")
    except ValueError:
        return await refuse(send, 400, "not JSON")
    if not isinstance(frames, list) or not all(isinstance(f, str) for f in frames):
        return await refuse(send, 400, "a list of frames is expected")
    for frame in frames:
        conn.received(frame)
    await _respond(send, 204)
