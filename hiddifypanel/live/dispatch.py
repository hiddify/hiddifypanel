"""A request to the admin API made inside this process for a browser on the live channel: through the whole Flask app (sign
in, permissions, the endpoint itself) with the browser's own cookies and forwarded headers, so it answers exactly what the
same request over HTTP would, without the page sending it.

Requests run on their own few threads (``HIDDIFY_LIVE_THREADS``, default 4): live updates never take the threads (or the
database connections) of the pages' own requests.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

_executor = ThreadPoolExecutor(max_workers=int(os.environ.get("HIDDIFY_LIVE_THREADS") or 4), thread_name_prefix="live")

#: Headers of the WebSocket handshake that the API requests carry on (sign in, address, language); not the WebSocket ones.
FORWARDED = frozenset({"cookie", "host", "user-agent", "accept-language", "x-forwarded-for", "x-forwarded-proto", "x-forwarded-host", "x-real-ip", "hiddify-api-key"})
_SAFE_PATH = re.compile(r"^[A-Za-z0-9_\-./]*$")


class BadPath(ValueError):
    pass


@dataclass(frozen=True)
class Caller:
    """Who is on the live channel: the request a page would send, minus its path."""

    api_base: str  # /<admin proxy path>/api/v2/admin/
    base_url: str  # https://<host>
    headers: tuple[tuple[str, str], ...]
    remote_addr: str

    @classmethod
    def from_scope(cls, scope: dict[str, Any], proxy_path: str) -> Caller:
        raw = [(k.decode("latin-1").lower(), v.decode("latin-1")) for k, v in scope.get("headers") or []]
        headers = [(k, v) for k, v in raw if k in FORWARDED]
        values = dict(raw)
        host = values.get("host") or "localhost"
        proto = values.get("x-forwarded-proto") or ("https" if scope.get("scheme") in ("wss", "https") else "http")
        client = scope.get("client") or ("127.0.0.1", 0)
        return cls(api_base=f"/{proxy_path}/api/v2/admin/", base_url=f"{proto}://{host}", headers=tuple(headers), remote_addr=str(client[0]))


@dataclass(frozen=True)
class Answer:
    status: int
    body: bytes
    content_type: str

    def data(self) -> Any:
        """The JSON answer, or its text."""
        if "json" in self.content_type:
            try:
                return json.loads(self.body)
            except ValueError:
                pass
        return self.body.decode("utf-8", "replace")

    def message(self) -> str:
        data = self.data()
        if isinstance(data, dict):
            for key in ("message", "msg"):
                if isinstance(data.get(key), str) and data[key]:
                    return data[key]
        return (data if isinstance(data, str) else json.dumps(data))[:500]


def check_path(path: str) -> str:
    """A path under the admin API (``dashboard/``, ``apply/log/``…): relative, no ``..``."""
    path = path.lstrip("/")
    if not _SAFE_PATH.match(path) or ".." in path.split("/"):
        raise BadPath(f"not an admin API path: {path!r}")
    return path


def _call(flask_app: Any, caller: Caller, method: str, path: str, query: dict[str, Any] | None, body: Any) -> Answer:
    client = flask_app.test_client(use_cookies=False)
    response = client.open(
        caller.api_base + path,
        method=method,
        base_url=caller.base_url,
        query_string={k: v for k, v in (query or {}).items() if v is not None},
        headers=list(caller.headers),
        environ_base={"REMOTE_ADDR": caller.remote_addr},
        json=body,
    )
    try:
        return Answer(response.status_code, response.get_data(), response.content_type or "")
    finally:
        response.close()


async def request(flask_app: Any, caller: Caller, method: str, path: str, query: dict[str, Any] | None = None, body: Any = None) -> Answer:
    path = check_path(path)
    return await asyncio.get_running_loop().run_in_executor(_executor, _call, flask_app, caller, method, path, query, body)
