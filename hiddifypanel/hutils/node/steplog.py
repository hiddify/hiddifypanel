"""Logs for registering a node, so a failure can be traced to the step and the side where it happened.

A registration id (``REG_HEADER``) is made by the parent and travels with every call, so the lines of the parent and of
the node (which are in different log files) can be put side by side. Nothing secret is written: hosts, counts, times.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import urlparse

from loguru import logger

REG_HEADER = "X-Registration-Id"


def new_id() -> str:
    return uuid.uuid4().hex[:8]


def host_of(url: str) -> str:
    """Only the host of an address: the rest of a panel link is its secret."""
    return urlparse(url if "://" in url else f"https://{url}").netloc or "?"


@contextmanager
def step(reg: str, side: str, title: str, /, **info: object) -> Iterator[None]:
    """Log the start and the end (with the time it took) of a step, and where it failed if it did.

    ``side`` is ``parent`` or ``node``: the side this log is written on.
    """
    tag = f"[register {reg or '-'} {side}]"
    details = " ".join(f"{k}={v}" for k, v in info.items())
    started = time.monotonic()
    logger.info(f"{tag} {title}: start {details}".rstrip())
    try:
        yield
    except BaseException as e:
        logger.error(f"{tag} {title}: FAILED after {time.monotonic() - started:.2f}s with {type(e).__name__}: {str(e)[:300]}")
        raise
    logger.info(f"{tag} {title}: done in {time.monotonic() - started:.2f}s")
