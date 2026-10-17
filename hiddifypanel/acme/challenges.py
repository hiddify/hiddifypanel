"""HTTP-01 challenges, answered by HAProxy itself from an in-memory map (``virt@acme_challenges``).

``haproxy/server/fronts/in_httpmode.j2`` returns the map's value for a request whose path is a key of the map, before
any other routing (port 80 and 443, every domain and IP). A challenge is in the map only while its order is pending.
Redis keeps them too (10 minutes): ``sync()`` (every minute, ``scheduler.py``) puts them back after an HAProxy restart
or reload (an in-memory map starts empty).
"""

from __future__ import annotations

import json
import re

from loguru import logger

from hiddifypanel.hutils import haproxy_api

MAP = "virt@acme_challenges"
PREFIX = "/.well-known/acme-challenge/"
TTL = 600
_KEY = "hiddify:acme:challenge:"
# RFC 8555: the token is base64url; the key authorization is "<token>.<base64url thumbprint>". Nothing else reaches the map.
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{16,256}$")
_KEY_AUTH = re.compile(r"^[A-Za-z0-9_-]{16,256}\.[A-Za-z0-9_-]{16,128}$")


def _redis():
    from hiddifypanel.cache import redis_client

    return redis_client


def add(token: str, key_authorization: str) -> bool:
    """Serve ``key_authorization`` at ``/.well-known/acme-challenge/<token>``. False when HAProxy did not take it now
    (the minute sync retries; the order would then likely fail and be retried later)."""
    if not _TOKEN.match(token or "") or not _KEY_AUTH.match(key_authorization or ""):
        raise ValueError(f"unexpected ACME challenge token: {token!r}")
    path = PREFIX + token
    try:
        _redis().set(_KEY + token, json.dumps({"path": path, "value": key_authorization}), ex=TTL)
    except Exception as e:
        logger.warning(f"ACME: challenge {token} not kept in redis ({e}); it is lost if HAProxy restarts now")
    ok = haproxy_api.add_map(MAP, path, key_authorization)
    logger.debug(f"ACME: challenge {path} {'added to' if ok else 'NOT added to'} HAProxy")
    return ok


def remove(token: str) -> None:
    try:
        _redis().delete(_KEY + token)
    except Exception as e:
        logger.debug(f"ACME: challenge {token} not removed from redis: {e}")
    haproxy_api.del_map(MAP, PREFIX + token)
    logger.debug(f"ACME: challenge {PREFIX + token} removed")


def _live() -> dict[str, str]:
    r = _redis()
    keys = list(r.scan_iter(match=_KEY + "*", count=1000))
    if not keys:
        return {}
    out: dict[str, str] = {}
    for raw in r.mget(keys):
        if not raw:
            continue
        try:
            item = json.loads(raw)
            out[item["path"]] = item["value"]
        except (ValueError, KeyError, TypeError):
            continue
    return out


def sync() -> None:
    """Make HAProxy's map match redis: drop finished challenges, put the pending ones back after an HAProxy restart."""
    try:
        wanted = _live()
    except Exception as e:
        logger.debug(f"ACME: challenges sync skipped, redis not reachable: {e}")
        return
    haproxy_api.sync_map(MAP, wanted)
