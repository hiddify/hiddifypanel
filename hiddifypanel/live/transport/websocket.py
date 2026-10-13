"""A ``Connection`` over an accepted ASGI WebSocket."""

from __future__ import annotations

import asyncio
from typing import Any

from hiddifypanel.asgi_types import Receive, Send

from .base import Codec, Connection, Frame


class WebSocketConnection(Connection):
    def __init__(self, receive: Receive, send: Send, codec: Codec, ignore: frozenset[str] = frozenset()) -> None:
        super().__init__(codec, ignore)
        self._receive = receive
        self._send = send
        self._reader = asyncio.get_running_loop().create_task(self._read())

    async def _read(self) -> None:
        try:
            while True:
                event = await self._receive()
                if event["type"] == "websocket.disconnect":
                    return
                if event["type"] == "websocket.receive":
                    frame = event.get("bytes")
                    self.received(frame if frame is not None else event.get("text") or "")
        finally:
            self.ended()

    async def _write(self, frame: Frame) -> None:
        message: dict[str, Any] = {"type": "websocket.send"}
        message["bytes" if isinstance(frame, bytes) else "text"] = frame
        await self._send(message)

    async def close(self, code: int = 1000) -> None:
        self._reader.cancel()
        if not self.closed.is_set():
            self.ended()
            try:
                await self._send({"type": "websocket.close", "code": code})
            except Exception:  # noqa: BLE001  already gone
                pass
