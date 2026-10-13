"""One connection to a page or a node, whatever carries it: the processing code (live/channel.py, hutils/node/ws_server.py) only
sees a ``Connection`` — messages in a queue, ``send`` — and never the transport underneath (websocket.py: a WebSocket;
stream.py: a streamed response plus POSTs, which rides the page's HTTP/3 or HTTP/2 connection).

Each channel has a ``Codec``: how a message is written in a frame (JSON text for the admin pages; zlib-compressed JSON for the
nodes, in base64 where the transport carries text only).
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Mapping
from typing import Any

from hiddifypanel.hutils.node import ws_proto
from hiddifypanel.hutils.node.ws_proto import ProtocolError

type Frame = str | bytes


class Gone(Exception):
    """The other side closed the connection (or stopped answering)."""


class Codec(ABC):
    @abstractmethod
    def encode(self, message: Mapping[str, Any]) -> Frame: ...

    @abstractmethod
    def decode(self, frame: Frame) -> dict[str, Any]: ...

    def as_text(self) -> Codec:
        """The same messages for a transport that carries text only."""
        return self


class JsonCodec(Codec):
    """The admin pages' live channel: a message is a JSON object with a ``type``."""

    def encode(self, message: Mapping[str, Any]) -> Frame:
        return json.dumps(message, default=str, separators=(",", ":"))

    def decode(self, frame: Frame) -> dict[str, Any]:
        try:
            message = json.loads(frame)
        except ValueError as e:
            raise ProtocolError(f"not JSON: {e}") from e
        if not isinstance(message, dict):
            raise ProtocolError("a message is an object")
        return message


class NodeCodec(Codec):
    """The nodes' channel: zlib-compressed JSON (ws_proto) in binary frames."""

    def encode(self, message: Mapping[str, Any]) -> Frame:
        return ws_proto.encode(dict(message))

    def decode(self, frame: Frame) -> dict[str, Any]:
        return ws_proto.decode(frame)

    def as_text(self) -> Codec:
        return NodeTextCodec()


class NodeTextCodec(Codec):
    """``NodeCodec`` in base64, for a text-only transport."""

    def encode(self, message: Mapping[str, Any]) -> Frame:
        return base64.b64encode(ws_proto.encode(dict(message))).decode("ascii")

    def decode(self, frame: Frame) -> dict[str, Any]:
        try:
            raw = base64.b64decode(frame, validate=True)
        except ValueError as e:
            raise ProtocolError(f"not base64: {e}") from e
        return ws_proto.decode(raw)


class Connection(ABC):
    """Messages from the other side in a queue (read all the time, so a close is seen while waiting for something else), and
    ``last_heard``: when the other side last said anything (its heartbeat included, which is not queued: ``ignore``)."""

    def __init__(self, codec: Codec, ignore: frozenset[str] = frozenset()) -> None:
        self.codec = codec
        self.ignore = ignore
        self.inbox: asyncio.Queue[dict[str, Any] | ProtocolError] = asyncio.Queue()
        self.arrived = asyncio.Event()
        self.closed = asyncio.Event()
        self.last_heard = time.monotonic()
        self._send_lock = asyncio.Lock()

    # ------------------------------------------------------------------ for the transport

    def received(self, frame: Frame) -> None:
        """A frame from the other side (the transport calls this)."""
        self.last_heard = time.monotonic()
        try:
            message = self.codec.decode(frame)
        except ProtocolError as e:
            self.inbox.put_nowait(e)
        else:
            if message.get("type") in self.ignore:
                return
            self.inbox.put_nowait(message)
        self.arrived.set()

    def ended(self) -> None:
        """The transport is over (the other side left)."""
        self.closed.set()
        self.arrived.set()

    @abstractmethod
    async def _write(self, frame: Frame) -> None: ...

    @abstractmethod
    async def close(self, code: int = 1000) -> None:
        """End the connection from this side (``code``: a WebSocket close code; streams just end)."""

    # ------------------------------------------------------------------ for the processing code

    async def send(self, message: Mapping[str, Any]) -> None:
        if self.closed.is_set():
            raise Gone
        async with self._send_lock:
            await self._write(self.codec.encode(message))

    def poll(self) -> dict[str, Any] | None:
        """The next message if one is there."""
        if self.inbox.empty():
            self.arrived.clear()
            if self.closed.is_set():
                raise Gone
            return None
        item = self.inbox.get_nowait()
        if isinstance(item, ProtocolError):
            raise item
        return item

    async def recv(self, timeout: float) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while (message := self.poll()) is None:
            if time.monotonic() >= deadline:
                raise Gone
            await self.wait(timeout=deadline - time.monotonic())
        return message

    async def wait(self, other: Awaitable[object] | None = None, timeout: float | None = None) -> None:
        """Until a message arrives, ``other`` is done, the connection closes or ``timeout`` passes."""
        waiters = {asyncio.ensure_future(self.arrived.wait()), asyncio.ensure_future(self.closed.wait())}
        if other is not None:
            waiters.add(asyncio.ensure_future(other))
        try:
            await asyncio.wait(waiters, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for w in waiters:
                w.cancel()
