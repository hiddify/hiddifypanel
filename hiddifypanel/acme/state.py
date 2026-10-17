"""Shared ACME state in redis: the domains page's job of each domain, failures of each host, and the locks that keep a
domain (and a whole renewal) from running twice, across threads and processes (the panel, the CLI)."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

from loguru import logger
from redis import Redis

from hiddifypanel.acme.models import CertJob, Failure

JOB_TTL = 600
FAILURE_TTL = 7 * 86400
_JOB_KEY = "domains-page:cert:"
_FAIL_KEY = "hiddify:acme:fail:"
_DOMAIN_LOCK = "hiddify:acme:domain-lock:"
_RUN_LOCK = "hiddify:acme:renew-lock"

_local: set[str] = set()
_local_guard = threading.Lock()


def _redis() -> Redis:
    from hiddifypanel.cache import redis_client

    return redis_client


# ---------------------------------------------------------------------------------------------- jobs


def get_job(domain_id: int) -> CertJob | None:
    try:
        raw = _redis().get(_JOB_KEY + str(domain_id))
        return CertJob.from_dict(json.loads(raw)) if raw else None
    except Exception as e:
        logger.debug(f"cert job of {domain_id} unreadable: {e}")
        return None


def set_job(domain_id: int, job: CertJob) -> None:
    try:
        _redis().set(_JOB_KEY + str(domain_id), json.dumps(job.to_dict()), ex=JOB_TTL)
    except Exception as e:
        logger.debug(f"cert job state unavailable: {e}")
    try:
        from hiddifypanel.live import changes

        changes.publish(["cert", f"cert:{domain_id}"])
    except Exception as e:
        logger.debug(f"cert change not published: {e}")


# ---------------------------------------------------------------------------------------------- failures


def get_failure(host: str) -> Failure | None:
    try:
        raw = _redis().get(_FAIL_KEY + host)
        return Failure.from_dict(json.loads(raw)) if raw else None
    except Exception:
        return None


def add_failure(host: str, error: str, rate_limit_seconds: int | None) -> Failure:
    old = get_failure(host)
    now = time.time()
    fail = Failure(count=(old.count if old else 0) + 1, at=now, error=error[-500:], rate_limited_until=now + rate_limit_seconds if rate_limit_seconds else 0.0)
    try:
        _redis().set(_FAIL_KEY + host, json.dumps(fail.to_dict()), ex=FAILURE_TTL)
    except Exception as e:
        logger.debug(f"failure of {host} not kept: {e}")
    return fail


def clear_failure(host: str) -> None:
    try:
        _redis().delete(_FAIL_KEY + host)
    except Exception:
        pass


# ---------------------------------------------------------------------------------------------- locks


def _try_lock(name: str, ttl: int) -> bool:
    with _local_guard:
        if name in _local:
            return False
        _local.add(name)
    try:
        if _redis().set(name, "1", nx=True, ex=ttl):
            return True
    except Exception as e:
        logger.debug(f"redis lock {name} unavailable ({e}); this process only")
        return True
    with _local_guard:
        _local.discard(name)
    return False


def _unlock(name: str) -> None:
    with _local_guard:
        _local.discard(name)
    try:
        _redis().delete(name)
    except Exception:
        pass


@contextmanager
def domain_lock(domain_id: int) -> Iterator[bool]:
    """Yields False when the domain is processed already (elsewhere)."""
    name = _DOMAIN_LOCK + str(domain_id)
    got = _try_lock(name, 600)
    try:
        yield got
    finally:
        if got:
            _unlock(name)


def domain_busy(domain_id: int) -> bool:
    name = _DOMAIN_LOCK + str(domain_id)
    try:
        return bool(_redis().exists(name))
    except Exception:
        return name in _local


@contextmanager
def renewal_lock(wait_seconds: float = 0) -> Iterator[bool]:
    """Yields False when another renewal still runs after ``wait_seconds``."""
    deadline = time.monotonic() + wait_seconds
    got = _try_lock(_RUN_LOCK, 1800)
    while not got and time.monotonic() < deadline:
        time.sleep(2)
        got = _try_lock(_RUN_LOCK, 1800)
    try:
        yield got
    finally:
        if got:
            _unlock(_RUN_LOCK)
