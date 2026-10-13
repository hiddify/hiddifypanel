"""The parent's end of the WebSocket its nodes keep open (``/<admin proxy path>/api/v2/node/ws/``, served by the ASGI app).

A node says where it is in the change feed (``hello``); the parent sends what changed since, a batch at a time, each one
after the node confirmed the one before (``ack``). Then it waits: a commit that writes users or admins anywhere in the panel
publishes their tables (live/changes.py) and wakes every connection; without one it looks again every ``IDLE_TICK`` seconds.

The node opens the connection, so the parent never has to reach the node. While a node is connected the parent does not ask it
to sync over HTTP (``is_connected``).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from loguru import logger

from hiddifypanel.asgi_types import Receive, Send
from hiddifypanel.cache import redis_client
from hiddifypanel.live import changes
from hiddifypanel.live.app_thread import in_app
from hiddifypanel.live.transport import Connection, Gone, NodeCodec, StreamConnection, WebSocketConnection, run_with_stream
from hiddifypanel.live.transport import handle_post as post_to_stream
from hiddifypanel.live.transport.stream import refuse

from . import ws_proto
from .ws_proto import ProtocolError

CONNECTED_KEY = "node:ws:{}"
CONNECTED_TTL = 90
IDLE_TICK = 30.0
HELLO_TIMEOUT = 30.0
ACK_TIMEOUT = 300.0



# --------------------------------------------------------------------------- for the rest of the panel (sync code)


#: The tables the nodes get (sync_feed.py): a commit writing one of them wakes the connections.
ACCOUNT_TAGS = ("user", "admin_user")


def publish_change() -> None:
    """Users or admins changed outside the ORM: wake the connected nodes (they look again every ``IDLE_TICK`` anyway)."""
    changes.publish(ACCOUNT_TAGS)


def is_connected(unique_id: str) -> bool:
    """The node is connected to this panel over the WebSocket (it then gets every change without being asked)."""
    try:
        return bool(redis_client.exists(CONNECTED_KEY.format(unique_id)))
    except Exception:  # noqa: BLE001
        return False


def _mark_connected(unique_id: str, connected: bool) -> None:
    try:
        if connected:
            redis_client.set(CONNECTED_KEY.format(unique_id), b"1", ex=CONNECTED_TTL)
        else:
            redis_client.delete(CONNECTED_KEY.format(unique_id))
    except Exception:  # noqa: BLE001
        logger.warning("could not record a node's connection in Redis")


# --------------------------------------------------------------------------- the connection


def _header(scope: dict[str, Any], name: str) -> str:
    wanted = name.lower().encode()
    for key, value in scope.get("headers") or []:
        if key.lower() == wanted:
            return value.decode("latin-1")
    return ""


def _authenticate(proxy_path: str, apikey: str) -> tuple[str, str] | None:
    """The node calling: ``(unique_id, name)``; None when it is not one of this panel's nodes (same rule as the HTTP node calls)."""
    from hiddifypanel.models import Child, ChildMode, ConfigEnum, hconfig

    if not apikey or proxy_path != hconfig(ConfigEnum.proxy_path_admin):
        return None
    node = Child.by_unique_id(apikey)
    if node is None or node.id == 0 or node.mode != ChildMode.remote:
        return None
    return node.unique_id, node.name


def _open(cursor: object) -> tuple[Any, dict[str, Any]]:
    from hiddifypanel.models import ConfigEnum, hconfig

    from . import endpoints
    from .sync_feed import Cursor, Feed

    feed = Feed(Cursor.from_json(cursor), str(hconfig(ConfigEnum.unique_id)))
    welcome = {
        "type": "welcome",
        "version": ws_proto.VERSION,
        "parent_unique_id": feed.parent,
        "parent_hosts": [{"domain": h.domain, "mode": h.mode} for h in endpoints.own_hosts()],
    }
    return feed, welcome


def _heard_from(unique_id: str) -> None:
    from hiddifypanel.models import Child

    _mark_connected(unique_id, True)
    node = Child.by_unique_id(unique_id)
    if node is not None:
        node.mark_node_to_parent(commit=True)


#: The channel name of the streamed transport's sessions (live/transport/stream.py).
STREAM_CHANNEL = "node"
#: The node's heartbeat is not a message to answer.
IGNORE = frozenset({"ping"})


async def handle(flask_app: Any, proxy_path: str, scope: dict[str, Any], receive: Receive, send: Send) -> None:
    """A node over a WebSocket (``/<admin path>/api/v2/node/ws/``)."""
    if (await receive())["type"] != "websocket.connect":
        return
    node = await in_app(flask_app, _authenticate, proxy_path, _header(scope, "Hiddify-API-Key"))
    if node is None:
        await send({"type": "websocket.close", "code": ws_proto.CLOSE_UNAUTHORIZED})  # before accept: the client sees HTTP 403
        return
    await send({"type": "websocket.accept"})
    await serve(flask_app, *node, WebSocketConnection(receive, send, NodeCodec(), IGNORE))


async def handle_stream(flask_app: Any, proxy_path: str, scope: dict[str, Any], receive: Receive, send: Send) -> None:
    """A node over a streamed response plus POSTs (``/<admin path>/api/v2/node/stream/``): for a way to the parent that does not
    pass WebSockets (some CDNs), over HTTP/2 when it can."""
    node = await in_app(flask_app, _authenticate, proxy_path, _header(scope, "Hiddify-API-Key"))
    if node is None:
        return await refuse(send, 403, "not a node of this panel")
    conn = StreamConnection(STREAM_CHANNEL, NodeCodec(), IGNORE)
    await run_with_stream(conn, asyncio.get_running_loop().create_task(serve(flask_app, *node, conn)), receive, send)


async def handle_post(scope: dict[str, Any], receive: Receive, send: Send, session: str) -> None:
    await post_to_stream(scope, receive, send, STREAM_CHANNEL, session)


async def serve(flask_app: Any, unique_id: str, name: str, sock: Connection) -> None:
    """One node until it leaves, whatever carries its messages."""
    tag = f"[node-ws {name}]"
    sent_rows = 0
    started = time.monotonic()
    logger.info(f"{tag} connected")
    try:
        hello = await sock.recv(HELLO_TIMEOUT)
        if hello["type"] != "hello":
            raise ProtocolError(f"expected hello, got {hello['type']}")
        feed, welcome = await in_app(flask_app, _open, hello.get("cursor"))
        await sock.send(welcome)
        heard = 0.0
        awaiting_ack_since: float | None = None
        next_inventory = 0.0  # right after catching up, then every RECONCILE_EVERY
        while True:
            now = time.monotonic()
            if now - sock.last_heard > ws_proto.SILENT:
                raise Gone  # a connection that looks open but carries nothing (the node's network went away)
            if now - heard > CONNECTED_TTL / 3:  # "seen" only while it talks
                await in_app(flask_app, _heard_from, unique_id)
                heard = now
            while (message := sock.poll()) is not None:
                kind = message["type"]
                if kind == "ack" and awaiting_ack_since is not None:
                    awaiting_ack_since = None
                elif kind == "inventory_please":  # "Sync now" on the parent's Nodes page reaches the node, which asks for this
                    next_inventory = 0.0
                elif kind == "users_list_please":
                    await sock.send({"type": "users_list", "users": await in_app(flask_app, feed.user_list)})
                elif kind == "resend":
                    feed.ask_again(ws_proto.str_list(message.get("users", []), "resend.users"), ws_proto.str_list(message.get("admins", []), "resend.admins"))
                else:
                    raise ProtocolError(f"unexpected {kind}")
            if awaiting_ack_since is not None:
                if now - awaiting_ack_since > ACK_TIMEOUT:
                    raise Gone
                await sock.wait(timeout=5.0)
                continue
            seen = changes.hub.versions(ACCOUNT_TAGS)  # before reading: a change published while reading wakes the wait below at once
            batch = await in_app(flask_app, feed.next_batch)
            if batch is not None:
                await sock.send(batch)
                awaiting_ack_since = time.monotonic()
                sent_rows += len(batch["users"]) + len(batch["admins"])
                if not batch["more"]:
                    logger.info(f"{tag} up to date ({sent_rows} rows sent on this connection)")
                continue
            if now >= next_inventory:
                await sock.send(await in_app(flask_app, feed.inventory))
                next_inventory = now + ws_proto.RECONCILE_EVERY
                continue
            await sock.wait(changes.hub.wait(ACCOUNT_TAGS, seen, IDLE_TICK), timeout=IDLE_TICK + 1)
    except Gone:
        logger.info(f"{tag} disconnected after {time.monotonic() - started:.0f}s ({sent_rows} rows sent)")
        await sock.close()
    except ProtocolError as e:
        logger.warning(f"{tag} closing: {e}")
        await sock.close(ws_proto.CLOSE_PROTOCOL)
    except Exception:
        logger.exception(f"{tag} failed")
        await sock.close(1011)
    finally:
        await sock.close()
        await asyncio.to_thread(_mark_connected, unique_id, False)
