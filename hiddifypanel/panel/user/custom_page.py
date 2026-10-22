"""Custom user page: an admin's own build of the user page, served from the panel's own domain.

``user_page_url`` (Settings › Customizing User Page) points to any static site, e.g. a fork of hiddify-user-front
deployed to GitHub Pages (https://<you>.github.io/hiddify-user-front/). The panel downloads it (the server is abroad,
so a site that is filtered in Iran still works) and serves it on the user's own link:

* ``/<proxy>/<uuid>/`` in a browser: the site's ``index.html``, with ``<base href>`` set to the asset route below and
  ``window.__HIDDIFY__`` (the contract: where the user API is, the user's links, the language) put first in <head>;
* ``/<proxy>/<uuid>/user-page/<path>``: the site's other files (scripts, styles, fonts, images, translations).

Files are cached in redis for an hour, per URL (changing the URL takes effect at once). Empty ``user_page_url``: the
built-in page (static/user-front).
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import posixpath
import re
from urllib.parse import urljoin, urlsplit

import requests
from loguru import logger

from hiddifypanel.cache import redis_client
from hiddifypanel.models import ConfigEnum, hconfig

CACHE_TTL = 3600
MAX_FILE = 8_000_000
FETCH_TIMEOUT = 15
_KEY = "hiddify:user-page:{}"


_GITHUB_TREE = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)(/.*)?$")


def base_url() -> str:
    """The configured site, ending with "/"; empty when not set (or not an http(s) URL).

    A GitHub folder link (``https://github.com/<owner>/<repo>/tree/<branch>[/<dir>]``, e.g. a gh-pages branch) is read
    from raw.githubusercontent.com, so the repository does not need GitHub Pages turned on.
    """
    url = str(hconfig(ConfigEnum.user_page_url) or "").strip()
    tree = _GITHUB_TREE.match(url.rstrip("/"))
    if tree:
        owner, repo, branch, sub = tree.groups()
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}{sub or ''}"
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return ""
    return url if url.endswith("/") else url + "/"


def _safe(path: str) -> str | None:
    """A relative path inside the site (no scheme, no host, no climbing out with "..")."""
    path = (path or "").split("?", 1)[0].split("#", 1)[0].lstrip("/")
    if not path:
        return "index.html"
    clean = posixpath.normpath(path)
    if clean.startswith("..") or "://" in path or clean.startswith("/"):
        return None
    return clean


def fetch(path: str) -> tuple[bytes, str] | None:
    """One file of the site: (content, content type), or None when it is not there."""
    base = base_url()
    rel = _safe(path)
    if not base or rel is None:
        return None
    key = _KEY.format(hashlib.sha256(f"{base}|{rel}".encode()).hexdigest()[:32])
    cached = redis_client.hgetall(key)
    if cached and b"body" in cached:
        return cached[b"body"], cached.get(b"type", b"application/octet-stream").decode()
    try:
        with requests.get(urljoin(base, rel), timeout=FETCH_TIMEOUT, stream=True, headers={"User-Agent": "HiddifyPanel"}) as r:
            if r.status_code != 200:
                return None
            body = r.raw.read(MAX_FILE + 1, decode_content=True)
            if len(body) > MAX_FILE:
                logger.warning("custom user page: {} is too large", rel)
                return None
            # raw.githubusercontent.com sends every file as text/plain: the file name decides there
            ctype = (r.headers.get("Content-Type") or "").split(";")[0]
            if not ctype or ctype in ("text/plain", "application/octet-stream"):
                ctype = mimetypes.guess_type(rel)[0] or ctype or "application/octet-stream"
    except requests.RequestException as e:
        logger.warning("custom user page: {} not fetched: {}", rel, e)
        return None
    if ctype.startswith("text/") or ctype in ("application/javascript", "application/json", "image/svg+xml"):
        ctype += "; charset=utf-8"
    redis_client.hset(key, mapping={"body": body, "type": ctype})
    redis_client.expire(key, CACHE_TTL)
    return body, ctype


def page(context: dict, assets_base: str) -> str | None:
    """The site's index.html for one user: assets through the panel, the contract in ``window.__HIDDIFY__``."""
    got = fetch("index.html")
    if got is None:
        return None
    html = got[0].decode("utf-8", errors="replace")
    contract = json.dumps(context, ensure_ascii=False).replace("</", "<\\/")
    head = (
        f'<base href="{assets_base}">'
        f"<script>window.__HIDDIFY__={contract};"
        # what hiddify-user-front reads already (kept for builds that do not read __HIDDIFY__ yet)
        f"window.appVersion={json.dumps(context['version'])};window.deepLink={json.dumps(context['deep_link'])};"
        f"window.__USER_FRONT_STATIC__={json.dumps(assets_base.rstrip('/'))};</script>"
    )
    match = re.search(r"<head[^>]*>", html, re.IGNORECASE)
    return html[: match.end()] + head + html[match.end():] if match else head + html
