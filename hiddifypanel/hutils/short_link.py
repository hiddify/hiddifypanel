"""Temporary short links, served by HAProxy (no nginx).

A short link is ``https://<host>/<slug>``: HAProxy answers it with a 302 to the real address from an in-memory map
(``virt@short_links``, ``haproxy/server/fronts/in_httpmode.j2``). The panel owns the links: they live in redis with a
10 minute TTL, and are added to / removed from HAProxy's map at runtime through its API socket (no reload, no file).
``sync()`` (every minute, ``scheduler.py``) makes HAProxy's map match redis: it drops the expired links and puts the
live ones back after an HAProxy restart (an in-memory map starts empty).
"""

from __future__ import annotations

import hashlib
import re

from loguru import logger

from hiddifypanel import hutils
from hiddifypanel.hutils import haproxy_api

MAP = "virt@short_links"
DEFAULT_MINUTES = 10
_SLUG_KEY = "hiddify:short_link:slug:"  # slug -> url
_URL_KEY = "hiddify:short_link:url:"  # sha1(url) -> slug, to give the same link again while it lives
_SLUG = re.compile(r"^[a-z0-9]{6,12}$")


def _redis():
    from hiddifypanel.cache import redis_client

    return redis_client


def _keys(slug: str) -> tuple[str, str]:
    """The map keys of a link: with and without a trailing slash (HAProxy looks the path up as it is)."""
    return f"/{slug}", f"/{slug}/"


def add(url: str, minutes: int = DEFAULT_MINUTES) -> tuple[str, int]:
    """A short link to ``url`` for ``minutes``: (slug, seconds left). A live link to the same address is given again."""
    if not url or any(c in url for c in " \n\r"):
        raise ValueError("Invalid address for a short link")
    r = _redis()
    url_key = _URL_KEY + hashlib.sha1(url.encode()).hexdigest()
    if (slug := r.get(url_key)) and (ttl := r.ttl(_SLUG_KEY + slug.decode())) > 0:
        return slug.decode(), int(ttl)
    seconds = max(1, int(minutes)) * 60
    while True:
        slug = hutils.random.get_random_string(6, 10).lower()
        if _SLUG.match(slug) and r.set(_SLUG_KEY + slug, url, ex=seconds, nx=True):
            break
    r.set(url_key, slug, ex=seconds)
    for key in _keys(slug):
        if not haproxy_api.add_map(MAP, key, url):
            logger.debug(f"short links: {key} not in HAProxy yet; the next sync adds it")
    return slug, seconds


def _live() -> dict[str, str]:
    """slug -> url of the links redis still has."""
    r = _redis()
    keys = list(r.scan_iter(match=_SLUG_KEY + "*", count=1000))
    if not keys:
        return {}
    values = r.mget(keys)
    return {k.decode()[len(_SLUG_KEY) :]: v.decode() for k, v in zip(keys, values) if v is not None}


def sync() -> None:
    """Make HAProxy's map match redis: drop expired links, add the live ones it lacks (after an HAProxy restart)."""
    haproxy_api.sync_map(MAP, {key: url for slug, url in _live().items() for key in _keys(slug)})
