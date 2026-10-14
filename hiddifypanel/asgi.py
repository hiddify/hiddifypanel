"""The panel as an ASGI app (granian ``--interface asgi``): the Flask app on a pool of threads, and on the same port the live
channels of the nodes (hutils/node/ws_server.py) and of the admin pages (live/channel.py), each over a WebSocket or over a
streamed response plus POSTs (live/transport: rides HTTP/3 and HTTP/2 where a WebSocket can not).

granian runs an ASGI app on one event loop: the Flask (WSGI) requests go to ``a2wsgi``'s threads, as many at a time as
``HIDDIFY_PANEL_THREADS`` (default 10, what ``--blocking-threads`` was for the WSGI interface).
"""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from loguru import logger

from hiddifypanel.asgi_types import ASGIApp, Receive, Scope, Send

if TYPE_CHECKING:
    from a2wsgi.asgi_typing import HTTPScope

#: The session id of a streamed connection (live/transport/stream.py: ``secrets.token_urlsafe(24)``).
_SESSION = r"(?P<session>[A-Za-z0-9_-]{24,64})"
_ADMIN = r"^/(?P<proxy_path>[^/]+)/api/v2"

type Handler = Callable[[Any, re.Match[str], Scope, Receive, Send], Awaitable[None]]


@dataclass(frozen=True)
class Route:
    kind: str  # "http" | "websocket"
    method: str | None  # for "http"
    pattern: re.Pattern[str]
    handler: Handler


def _routes() -> list[Route]:
    from hiddifypanel.hutils.node import ws_server
    from hiddifypanel.live import channel, ssh

    def route(kind: str, method: str | None, pattern: str, handler: Handler) -> Route:
        return Route(kind, method, re.compile(pattern), handler)

    return [
        # the admin pages' live channel
        route("websocket", None, _ADMIN + r"/admin/live/?$", lambda app, m, scope, receive, send: channel.handle(app, m["proxy_path"], scope, receive, send)),
        route("http", "GET", _ADMIN + r"/admin/live/stream/?$", lambda app, m, scope, receive, send: channel.handle_stream(app, m["proxy_path"], scope, receive, send)),
        route("http", "POST", _ADMIN + r"/admin/live/" + _SESSION + r"/?$", lambda app, m, scope, receive, send: channel.handle_post(scope, receive, send, m["session"])),
        # SSH from the panel (live/ssh.py): the same transports
        route("websocket", None, _ADMIN + r"/admin/ssh/?$", lambda app, m, scope, receive, send: ssh.handle(app, m["proxy_path"], scope, receive, send)),
        route("http", "GET", _ADMIN + r"/admin/ssh/stream/?$", lambda app, m, scope, receive, send: ssh.handle_stream(app, m["proxy_path"], scope, receive, send)),
        route("http", "POST", _ADMIN + r"/admin/ssh/" + _SESSION + r"/?$", lambda app, m, scope, receive, send: ssh.handle_post(scope, receive, send, m["session"])),
        # the nodes' channel
        route("websocket", None, _ADMIN + r"/node/ws/?$", lambda app, m, scope, receive, send: ws_server.handle(app, m["proxy_path"], scope, receive, send)),
        route("http", "GET", _ADMIN + r"/node/stream/?$", lambda app, m, scope, receive, send: ws_server.handle_stream(app, m["proxy_path"], scope, receive, send)),
        route("http", "POST", _ADMIN + r"/node/" + _SESSION + r"/?$", lambda app, m, scope, receive, send: ws_server.handle_post(scope, receive, send, m["session"])),
    ]


def build_asgi(flask_app: Any, *, threads: int | None = None, node_client: bool = True) -> ASGIApp:
    """``node_client``: while this panel is a node, keep its channel to the parent open (hutils/node/ws_client.py)."""
    from a2wsgi import WSGIMiddleware

    from hiddifypanel.hutils.node import ws_proto

    wsgi = WSGIMiddleware(flask_app, workers=threads or int(os.environ.get("HIDDIFY_PANEL_THREADS") or 10))
    routes = _routes()

    def find(scope: Scope) -> tuple[Route, re.Match[str]] | None:
        path = scope.get("path") or ""
        for r in routes:
            if r.kind == scope["type"] and (r.method is None or r.method == scope.get("method")) and (m := r.pattern.match(path)):
                return r, m
        return None

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        kind = scope["type"]
        if kind == "lifespan":
            return await _lifespan(flask_app, receive, send, node_client)
        if (found := find(scope)) is not None:
            r, match = found
            return await r.handler(flask_app, match, scope, receive, send)
        if kind == "websocket":
            await receive()  # websocket.connect
            await send({"type": "websocket.close", "code": ws_proto.CLOSE_NOT_FOUND})
            return
        # granian's receive/send return awaitables that are not coroutines; a2wsgi hands them from its threads to the loop with
        # run_coroutine_threadsafe, which takes coroutines only ("A coroutine object is required" on every request body).
        async def wsgi_receive() -> Any:
            return await receive()

        async def wsgi_send(message: Any) -> None:
            await send(message)

        await wsgi(cast("HTTPScope", scope), wsgi_receive, wsgi_send)

    from hiddifypanel.panel.admin.v2_dev_proxy import wrap

    return wrap(app)


async def _lifespan(flask_app: Any, receive: Receive, send: Send, node_client: bool) -> None:
    task: asyncio.Task[None] | None = None
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            if node_client:
                from hiddifypanel.hutils.node import ws_client

                task = asyncio.get_running_loop().create_task(ws_client.run_forever(flask_app))
            await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception:  # noqa: BLE001
                    logger.exception("the node WebSocket client failed while stopping")
            await send({"type": "lifespan.shutdown.complete"})
            return
