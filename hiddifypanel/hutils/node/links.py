"""How a node reaches its parent's channel (ws_client.py): over a WebSocket, or over a streamed response plus POSTs where a proxy
or CDN on the way does not pass WebSockets (live/transport/stream.py is the parent's end). Both carry the same frames; the
session code above them does not know which one it has.
"""

from __future__ import annotations

import importlib.util
import json
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Protocol

from hiddifypanel.live.transport import Codec, NodeCodec, NodeTextCodec

from . import ws_proto

OPEN_TIMEOUT = 15.0
#: Answers that mean "not here" (an older parent, a proxy that does not pass this, not a node of it): no point asking again soon.
REFUSED_STATUSES = frozenset({400, 401, 403, 404, 405})


class Refused(Exception):
    def __init__(self, status: int) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status


class Link(Protocol):
    kind: str
    codec: Codec

    async def send(self, frame: str | bytes) -> None: ...
    async def recv(self) -> str | bytes: ...
    def frames(self) -> AsyncIterator[str | bytes]: ...


def base_parts(base: str) -> tuple[str, str]:
    """``https://host/path/`` → (``https``, ``host/path``)."""
    scheme, rest = base.split("://", 1) if "://" in base else ("https", base)
    return scheme, rest.rstrip("/")


class _WebSocketLink:
    kind = "websocket"

    def __init__(self, ws: Any) -> None:
        self.ws = ws
        self.codec: Codec = NodeCodec()

    async def send(self, frame: str | bytes) -> None:
        await self.ws.send(frame)

    async def recv(self) -> str | bytes:
        return await self.ws.recv()

    async def frames(self) -> AsyncIterator[str | bytes]:
        async for frame in self.ws:
            yield frame


@asynccontextmanager
async def websocket(base: str, apikey: str) -> AsyncGenerator[Link]:
    import websockets
    from websockets.exceptions import InvalidStatus

    scheme, rest = base_parts(base)
    url = f"{'ws' if scheme == 'http' else 'wss'}://{rest}/{ws_proto.PATH}"
    try:
        connection = websockets.connect(
            url,
            additional_headers={"Hiddify-API-Key": apikey},
            open_timeout=OPEN_TIMEOUT,
            ping_interval=20,  # also keeps a CDN from closing an idle connection
            ping_timeout=20,
            close_timeout=5,
            max_size=ws_proto.MAX_MESSAGE,
            compression=None,  # messages are compressed already
        )
        ws = await connection.__aenter__()
    except InvalidStatus as e:
        if e.response.status_code in REFUSED_STATUSES:
            raise Refused(e.response.status_code) from e
        raise
    try:
        yield _WebSocketLink(ws)
    finally:
        await connection.__aexit__(None, None, None)


def _http2() -> bool:
    """HTTP/2 when httpx can (``httpx[http2]``): the stream and the POSTs share one connection."""
    return importlib.util.find_spec("h2") is not None


class _StreamLink:
    kind = "stream"

    def __init__(self, client: Any, data: AsyncIterator[str], post_url: str) -> None:
        self.client = client
        self.data = data  # the data of the stream's events, one message each
        self.post_url = post_url
        self.codec: Codec = NodeTextCodec()

    async def send(self, frame: str | bytes) -> None:
        text = frame if isinstance(frame, str) else frame.decode()
        answer = await self.client.post(self.post_url, content=json.dumps([text]), headers={"content-type": "application/json"})
        if answer.status_code == 404:
            raise ConnectionError("the parent no longer has this session")
        answer.raise_for_status()

    async def recv(self) -> str | bytes:
        async for frame in self.frames():
            return frame
        raise ConnectionError("the stream ended")

    async def frames(self) -> AsyncIterator[str | bytes]:
        async for value in self.data:
            yield value


async def _events(lines: AsyncIterator[str]) -> AsyncIterator[tuple[str, str]]:
    """``(event, data)`` of an event stream; comments (keepalives) and blank lines are skipped."""
    event = "message"
    async for raw in lines:
        line = raw.rstrip("\r")
        if not line:
            event = "message"
        elif line.startswith(":"):
            continue
        elif line.startswith("event: "):
            event = line[7:]
        elif line.startswith("data: "):
            yield event, line[6:]


@asynccontextmanager
async def stream(base: str, apikey: str) -> AsyncGenerator[Link]:
    import httpx

    scheme, rest = base_parts(base)
    root = f"{scheme}://{rest}/"
    timeout = httpx.Timeout(OPEN_TIMEOUT, read=None)  # the stream is quiet for a while (keepalive comments every 15 s)
    async with httpx.AsyncClient(http2=_http2(), headers={"Hiddify-API-Key": apikey}, timeout=timeout) as client:
        async with client.stream("GET", root + ws_proto.STREAM_PATH) as response:
            if response.status_code in REFUSED_STATUSES:
                raise Refused(response.status_code)
            response.raise_for_status()
            events = _events(response.aiter_lines())
            kind, session = await anext(events)
            if kind != "session":
                raise ws_proto.ProtocolError(f"expected the session, got {kind}")

            async def data() -> AsyncIterator[str]:
                async for _kind, value in events:
                    yield value

            yield _StreamLink(client, data(), f"{root}{ws_proto.NODE_BASE}{session}/")
