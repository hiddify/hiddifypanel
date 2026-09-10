"""Jinja ``download()`` helper for parallel URL fetches with TTL cache."""

from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import urlparse

import requests
from jinja2 import pass_context
from jinja2.runtime import Context

from hiddifypanel.cache import redis_client
from hiddifypanel.proxy_v3.context_vars.ctx_client import ClientContextVar

_CACHE_RE = re.compile(r"^(\d+)\s*([smhdSMHD])?$")
_DEFAULT_TIMEOUT = 8
_MAX_WORKERS = 8
_REDIS_PREFIX = "h:jinja_download:"
_ALLOWED_METHODS = frozenset({"GET", "POST"})


def parse_cache_ttl(cache: str | int | None) -> int:
    """Parse cache duration like ``1h``, ``30m``, ``90s``, ``2d``, or bare seconds."""
    if cache is None:
        return 0
    if isinstance(cache, (int, float)):
        return max(0, int(cache))
    raw = str(cache).strip().lower()
    if not raw or raw in {"0", "no", "false", "none", "off"}:
        return 0
    match = _CACHE_RE.match(raw)
    if not match:
        return 300
    amount = int(match.group(1))
    unit = (match.group(2) or "s").lower()
    return amount * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]


def _normalize_content_type(content_type: str) -> str:
    raw = (content_type or "txt").strip().lower()
    if raw in {"json", "application/json"}:
        return "json"
    if raw in {"yaml", "yml", "text/yaml", "application/yaml", "application/x-yaml"}:
        return "yaml"
    return "txt"


def _normalize_method(method: str | None) -> str:
    raw = str(method or "GET").strip().upper()
    return raw if raw in _ALLOWED_METHODS else "GET"


def _caller_user_agent(context: Context | None) -> str:
    if context is None:
        return "HiddifyPanel/download"
    ctx = context.get("ctx")
    if isinstance(ctx, ClientContextVar):
        ua = ctx.platform.useragent
        if ua.strip():
            return ua.strip()
    return "HiddifyPanel/download"


def _normalize_headers(headers: dict[str, Any] | None) -> dict[str, str]:
    if not headers:
        return {}
    return {str(k): str(v) for k, v in headers.items() if k is not None and v is not None}


def _normalize_json_data(data: Any) -> Any | None:
    if data is None:
        return None
    if isinstance(data, (dict, list)):
        return data
    return None


def _cache_key(
    content_type: str,
    user_agent: str,
    url: str,
    headers: dict[str, str],
    method: str,
    data: Any | None,
) -> str:
    header_part = "\0".join(f"{k}={headers[k]}" for k in sorted(headers))
    data_part = json.dumps(data, ensure_ascii=False, sort_keys=True, default=str) if data is not None else ""
    digest = hashlib.sha256(f"{content_type}\0{user_agent}\0{method}\0{url}\0{header_part}\0{data_part}".encode()).hexdigest()
    return f"{_REDIS_PREFIX}{digest}"


def _is_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _parse_body(content_type: str, body: str) -> Any:
    text = body if isinstance(body, str) else str(body or "")
    if content_type == "json":
        return json.loads(text)
    if content_type == "yaml":
        import yaml

        return yaml.safe_load(text)
    return text


def _fetch_url(
    url: str,
    *,
    user_agent: str,
    content_type: str,
    ttl: int,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    data: Any | None = None,
) -> Any:
    if not url or not _is_http_url(url):
        return None

    method_name = _normalize_method(method)
    extra_headers = _normalize_headers(headers)
    json_data = _normalize_json_data(data)
    key = _cache_key(content_type, user_agent, url, extra_headers, method_name, json_data)
    if ttl > 0:
        try:
            cached = redis_client.get(key)
            if cached is not None:
                return json.loads(cached)
        except Exception:
            pass

    request_headers = {"User-Agent": user_agent, **extra_headers}
    try:
        response = requests.request(
            method_name,
            url,
            timeout=_DEFAULT_TIMEOUT,
            headers=request_headers,
            json=json_data if method_name == "POST" else None,
        )
        response.raise_for_status()
        parsed = _parse_body(content_type, response.text)
    except Exception:
        return None

    if ttl > 0:
        try:
            redis_client.setex(key, ttl, json.dumps(parsed, ensure_ascii=False, default=str))
        except Exception:
            pass
    return parsed


@pass_context
def download(
    context: Any,
    content_type: str,
    cache: str | int,
    *urls: str,
    headers: dict[str, Any] | None = None,
    method: str = "GET",
    data: dict[str, Any] | list[Any] | None = None,
) -> list[Any]:
    """Fetch URLs in parallel and return one parsed response per URL.

    Jinja usage::

        {% set additional_configs = download(
             "json",
             "1h",
             "https://sublink1/" ~ ctx.user.uuid,
             "https://sublink2/" ~ ctx.user.uuid,
        ) %}

        {% set node_configs = download(
             "json",
             "1h",
             url1,
             url2,
             method="POST",
             headers={"Hiddify-API-Key": apikey},
             data={"core": "xray", "user_uuid": ctx.user.uuid, "raw": true},
        ) %}

    - ``content_type``: ``json`` | ``yaml`` | ``txt``
    - ``cache``: TTL such as ``1h``, ``30m``, ``90s`` (``0`` / ``none`` disables cache)
    - ``method``: ``GET`` (default) or ``POST``
    - ``headers``: optional extra request headers (merged with User-Agent)
    - ``data``: optional JSON body (sent only for ``POST``)
    - Uses the caller's ``ctx.platform.useragent`` as the request User-Agent
    - Failed URLs yield ``None`` so list length always matches ``urls``
    """
    normalized_type = _normalize_content_type(content_type)
    ttl = parse_cache_ttl(cache)
    user_agent = _caller_user_agent(context)
    extra_headers = _normalize_headers(headers)
    method_name = _normalize_method(method)
    json_data = _normalize_json_data(data)
    ordered_urls = [str(url or "").strip() for url in urls]
    if not ordered_urls:
        return []

    results: list[Any] = [None] * len(ordered_urls)
    workers = min(_MAX_WORKERS, len(ordered_urls))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(
                _fetch_url,
                url,
                user_agent=user_agent,
                content_type=normalized_type,
                ttl=ttl,
                headers=extra_headers,
                method=method_name,
                data=json_data,
            ): index
            for index, url in enumerate(ordered_urls)
        }
        for future in as_completed(future_map):
            index = future_map[future]
            try:
                results[index] = future.result()
            except Exception:
                results[index] = None
    return results
