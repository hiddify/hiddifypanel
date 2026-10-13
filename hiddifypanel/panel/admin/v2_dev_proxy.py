"""In dev, forward the Admin V2 frontend to Vite.

HAProxy opens HTTP/2 to the panel on port 9000. The API, including the live stream, is served here.
Vite listens on 127.0.0.1:9001 and only has the frontend; ``HIDDIFY_ADMIN_V2_DEV`` (for example
``http://127.0.0.1:9001``) turns this proxy on. Unset, every request stays on the panel.
"""

from __future__ import annotations

import asyncio
import base64
import os
import re
from collections.abc import AsyncIterator
from urllib.parse import urlsplit

from loguru import logger

from hiddifypanel.asgi_types import ASGIApp, Receive, Scope, Send

_FRONTEND = re.compile(r"^/[^/]+/admin/v2(?:/|$)")
_HOP = {b"connection", b"keep-alive", b"proxy-connection", b"transfer-encoding", b"upgrade", b"te"}


def wrap(app: ASGIApp) -> ASGIApp:
    raw = os.environ.get("HIDDIFY_ADMIN_V2_DEV", "").strip()
    if not raw:
        return app
    parts = urlsplit(raw if "://" in raw else f"http://{raw}")
    host = parts.hostname or "127.0.0.1"
    port = parts.port or 80

    async def wrapped(scope: Scope, receive: Receive, send: Send) -> None:
        kind = scope.get("type")
        if kind not in ("http", "websocket") or not _FRONTEND.match(scope.get("path") or ""):
            await app(scope, receive, send)
            return
        try:
            if kind == "http":
                await _proxy_http(scope, receive, send, host, port)
            else:
                await _proxy_websocket(scope, receive, send, host, port)
        except _GaveUp:
            return
        except Exception:
            logger.exception("admin v2 dev proxy to {}:{} failed", host, port)
            if kind == "http":
                await _send_text(send, 502, b"Admin V2 dev server is not running\n")

    return wrapped


class _GaveUp(Exception):
    """The client went away, or a response was already started."""


async def _proxy_http(scope: Scope, receive: Receive, send: Send, host: str, port: int) -> None:
    body = await _request_body(receive)
    try:
        reader, writer = await _connect(host, port)
    except ConnectionError:
        await _send_text(send, 502, b"Admin V2 dev server is not running\n")
        return
    started = False
    try:
        writer.write(_http_request(scope, host, port, body))
        await writer.drain()
        status, headers, transfer = await _read_response_head(reader)
        started = True
        await send({"type": "http.response.start", "status": status, "headers": headers})
        async for chunk in _response_body(reader, transfer):
            await send({"type": "http.response.body", "body": chunk, "more_body": True})
        await send({"type": "http.response.body", "body": b""})
    except ConnectionError:
        if not started:
            await _send_text(send, 502, b"Admin V2 dev server is not running\n")
    except Exception:
        if started:
            logger.exception("admin v2 dev proxy to {}:{} failed while streaming", host, port)
            return
        raise
    finally:
        writer.close()


async def _proxy_websocket(scope: Scope, receive: Receive, send: Send, host: str, port: int) -> None:
    if (await receive()).get("type") != "websocket.connect":
        return
    try:
        reader, writer = await _connect(host, port)
    except ConnectionError:
        await send({"type": "websocket.close", "code": 1011})
        return
    try:
        writer.write(_ws_request(scope, host, port))
        await writer.drain()
        status, _headers, _transfer = await _read_response_head(reader)
        if status != 101:
            await send({"type": "websocket.close", "code": 1011})
            return
        await send({"type": "websocket.accept"})
        incoming = asyncio.create_task(_ws_from_client(receive, writer))
        outgoing = asyncio.create_task(_ws_from_vite(reader, send))
        _done, pending = await asyncio.wait({incoming, outgoing}, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(incoming, outgoing, return_exceptions=True)
    except (ConnectionError, asyncio.IncompleteReadError):
        await send({"type": "websocket.close", "code": 1011})
    finally:
        writer.close()


async def _connect(host: str, port: int) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    try:
        return await asyncio.wait_for(asyncio.open_connection(host, port), timeout=3)
    except (TimeoutError, OSError) as exc:
        raise ConnectionError(str(exc)) from exc


async def _request_body(receive: Receive) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            raise _GaveUp
        if message["type"] != "http.request":
            continue
        if message.get("body"):
            chunks.append(message["body"])
        if not message.get("more_body"):
            return b"".join(chunks)


def _target(scope: Scope) -> bytes:
    target = (scope.get("path") or "/").encode()
    query = scope.get("query_string") or b""
    return target + b"?" + query if query else target


def _http_request(scope: Scope, host: str, port: int, body: bytes) -> bytes:
    lines = [f"{scope.get('method') or 'GET'} {_target(scope).decode()} HTTP/1.1".encode()]
    lines.extend(_forward_headers(scope, host, port))
    lines.append(f"content-length: {len(body)}".encode())
    lines.append(b"connection: close")
    return b"\r\n".join(lines) + b"\r\n\r\n" + body


def _ws_request(scope: Scope, host: str, port: int) -> bytes:
    key = base64.b64encode(os.urandom(16)).decode()
    lines = [f"GET {_target(scope).decode()} HTTP/1.1".encode(), f"host: {host}:{port}".encode()]
    for name, value in scope.get("headers") or []:
        if name.lower() in {b"host", b"connection", b"upgrade", b"sec-websocket-key", b"sec-websocket-version", *_HOP}:
            continue
        lines.append(name + b": " + value)
    lines.extend(
        [
            b"upgrade: websocket",
            b"connection: upgrade",
            f"sec-websocket-key: {key}".encode(),
            b"sec-websocket-version: 13",
            b"",
            b"",
        ]
    )
    return b"\r\n".join(lines)


def _forward_headers(scope: Scope, host: str, port: int) -> list[bytes]:
    lines = [f"host: {host}:{port}".encode()]
    for name, value in scope.get("headers") or []:
        if name.lower() in _HOP or name.lower() in {b"host", b"content-length"}:
            continue
        lines.append(name + b": " + value)
    return lines


async def _read_response_head(reader: asyncio.StreamReader) -> tuple[int, list[tuple[bytes, bytes]], tuple[str, int]]:
    status_line = await reader.readline()
    if not status_line:
        raise ConnectionError("vite closed the connection")
    parts = status_line.split()
    status = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 502
    headers: list[tuple[bytes, bytes]] = []
    transfer = ("eof", 0)
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            break
        name, _, value = line.partition(b":")
        key = name.strip().lower()
        item = value.strip()
        if key in _HOP or key == b"connection":
            if key == b"transfer-encoding" and item.lower() == b"chunked":
                transfer = ("chunked", 0)
            continue
        if key == b"content-length" and transfer[0] != "chunked":
            transfer = ("length", int(item or b"0"))
        headers.append((key, item))
    return status, headers, transfer


async def _response_body(reader: asyncio.StreamReader, transfer: tuple[str, int]) -> AsyncIterator[bytes]:
    kind, length = transfer
    if kind == "length":
        remaining = length
        while remaining:
            chunk = await reader.read(min(65536, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
        return
    if kind == "chunked":
        while True:
            size_line = await reader.readline()
            size = int(size_line.split(b";", 1)[0] or b"0", 16)
            if size == 0:
                while await reader.readline() not in (b"\r\n", b"\n", b""):
                    pass
                return
            yield await reader.readexactly(size)
            await reader.readexactly(2)
        return
    while chunk := await reader.read(65536):
        yield chunk


async def _ws_from_client(receive: Receive, writer: asyncio.StreamWriter) -> None:
    while True:
        message = await receive()
        kind = message.get("type")
        if kind == "websocket.disconnect":
            writer.write(_client_frame(0x8, b""))
            await writer.drain()
            return
        if kind != "websocket.receive":
            continue
        if message.get("text") is not None:
            writer.write(_client_frame(0x1, message["text"].encode()))
        elif message.get("bytes") is not None:
            writer.write(_client_frame(0x2, message["bytes"]))
        await writer.drain()


async def _ws_from_vite(reader: asyncio.StreamReader, send: Send) -> None:
    while True:
        opcode, data = await _read_frame(reader)
        if opcode == 0x1:
            await send({"type": "websocket.send", "text": data.decode()})
        elif opcode == 0x2:
            await send({"type": "websocket.send", "bytes": data})
        elif opcode == 0x8:
            code = int.from_bytes(data[:2], "big") if len(data) >= 2 else 1000
            await send({"type": "websocket.close", "code": code})
            return
        elif opcode == 0x9:
            continue


async def _read_frame(reader: asyncio.StreamReader) -> tuple[int, bytes]:
    header = await reader.readexactly(2)
    opcode = header[0] & 0x0F
    length = header[1] & 0x7F
    if length == 126:
        length = int.from_bytes(await reader.readexactly(2), "big")
    elif length == 127:
        length = int.from_bytes(await reader.readexactly(8), "big")
    mask = await reader.readexactly(4) if header[1] & 0x80 else None
    data = await reader.readexactly(length) if length else b""
    if mask is not None:
        data = bytes(byte ^ mask[i % 4] for i, byte in enumerate(data))
    return opcode, data


def _client_frame(opcode: int, data: bytes) -> bytes:
    mask = os.urandom(4)
    masked = bytes(byte ^ mask[i % 4] for i, byte in enumerate(data))
    length = len(data)
    head = bytearray([0x80 | opcode])
    if length < 126:
        head.append(0x80 | length)
    elif length < 65536:
        head.append(0x80 | 126)
        head += length.to_bytes(2, "big")
    else:
        head.append(0x80 | 127)
        head += length.to_bytes(8, "big")
    return bytes(head) + mask + masked


async def _send_text(send: Send, status: int, body: bytes) -> None:
    await send({"type": "http.response.start", "status": status, "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
    await send({"type": "http.response.body", "body": body})
