"""Database work from async code (the WebSockets): on a few threads of its own, each call inside an app context of its own
(its own session).

The panel's threads that can hold a database connection at once: the requests (``HIDDIFY_PANEL_THREADS``, asgi.py), the live
updates (``HIDDIFY_LIVE_THREADS``, live/dispatch.py) and these (``HIDDIFY_WS_THREADS``); database.py sizes the pool for them.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

THREADS = int(os.environ.get("HIDDIFY_WS_THREADS") or 4)
_executor = ThreadPoolExecutor(max_workers=THREADS, thread_name_prefix="ws-db")


async def in_app[T](flask_app: Any, fn: Callable[..., T], *args: Any) -> T:
    """Run ``fn(*args)`` on a database thread with an app context of its own: the session is removed when it returns."""

    def run() -> T:
        with flask_app.app_context():
            return fn(*args)

    return await asyncio.get_running_loop().run_in_executor(_executor, run)
