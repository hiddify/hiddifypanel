"""Per-user additional configs (Users → edit → Additional configs), merged into the user's subscription.

Stored in the user's extra params as ``additional_configs``: a JSON list of ``[kind, target, value]``:

* ``kind``    ``offline`` (``value`` is the config itself) or ``subscription`` (``value`` is a URL to fetch)
* ``target``  the client format it is for: ``sublink`` | ``xray`` | ``hiddify-core`` | ``clash`` | ``auto`` (every format)
* ``value``   share links / JSON / YAML, or the URL

The built-in "User Configs" custom proxy (enabled by default) renders them via ``user_additional_configs(core)``.
"""

from __future__ import annotations

import base64
import binascii
from typing import Any

import json5
import yaml
from jinja2 import pass_context

from .jinja_download import download

KINDS = ("offline", "subscription")
TARGETS = ("sublink", "xray", "hiddify-core", "clash", "auto")
EXTRA_KEY = "additional_configs"
MAX_ROWS = 50
MAX_VALUE = 200_000

#: How a subscription URL is fetched for each client format.
_FETCH_TYPE = {"sublink": "txt", "xray": "json", "hiddify-core": "json", "singbox": "json", "clash": "yaml"}


def clean_rows(value: Any) -> tuple[list[list[str]], list[str]]:
    """Valid rows and the problems found (the API rejects a save with problems)."""
    rows: list[list[str]] = []
    problems: list[str] = []
    if value in (None, ""):
        return rows, problems
    if not isinstance(value, list):
        return rows, ["additional configs must be a list"]
    if len(value) > MAX_ROWS:
        problems.append(f"at most {MAX_ROWS} additional configs")
    for i, item in enumerate(value[:MAX_ROWS], start=1):
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            problems.append(f"row {i}: expected [kind, target, value]")
            continue
        kind, target, content = (str(x if x is not None else "").strip() for x in item)
        if kind not in KINDS:
            problems.append(f"row {i}: kind must be offline or subscription")
        elif target not in TARGETS:
            problems.append(f"row {i}: target must be one of {', '.join(TARGETS)}")
        elif not content:
            problems.append(f"row {i}: empty")
        elif len(content) > MAX_VALUE:
            problems.append(f"row {i}: too long")
        elif kind == "subscription" and not content.lower().startswith(("http://", "https://")):
            problems.append(f"row {i}: a subscription must be an http(s) URL")
        else:
            rows.append([kind, target, content])
    return rows, problems


def _maybe_base64(text: str) -> str:
    """Subscriptions often serve base64-encoded share links."""
    compact = "".join(text.split())
    if not compact or "://" in compact:
        return text
    try:
        decoded = base64.b64decode(compact + "=" * (-len(compact) % 4), validate=False).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return text
    return decoded if "://" in decoded else text


def _parse_offline(content: str, core: str) -> Any:
    text = content.strip()
    if core == "sublink":
        # Share links (or base64 of them); JSON documents are for the JSON formats.
        return None if text.startswith(("{", "[")) else _maybe_base64(text)
    if core == "clash":
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError:
            return None
        # Only Clash documents (a "proxies" list); other formats' JSON is not for Clash.
        return data if isinstance(data, dict) and isinstance(data.get("proxies"), list) else None
    try:
        data = json5.loads(text)
    except ValueError:
        return None
    return data if isinstance(data, (dict, list)) else None


def _rows_for(extra: Any, core: str) -> list[list[str]]:
    getter = getattr(extra, "get", None)
    raw = getter(EXTRA_KEY) if callable(getter) else None
    if hasattr(raw, "to_python"):
        raw = raw.to_python()
    rows, _problems = clean_rows(list(raw) if isinstance(raw, (list, tuple)) else raw)
    want = "hiddify-core" if core == "singbox" else core
    return [r for r in rows if r[1] in (want, "auto")]


@pass_context
def user_additional_configs(context: Any, core: str, cache: str = "1h") -> list[Any]:
    """The current user's additional configs for ``core``: one parsed config per row (text for sublink)."""
    ctx = context.get("ctx")
    user = getattr(ctx, "user", None)
    if user is None:
        return []
    rows = _rows_for(getattr(user, "extra_params", None) or {}, core)
    out: list[Any] = [_parse_offline(r[2], core) for r in rows if r[0] == "offline"]
    urls = [r[2] for r in rows if r[0] == "subscription"]
    if urls:
        fetched = download(context, _FETCH_TYPE.get(core, "json"), cache, *urls)
        if core == "sublink":
            fetched = [_maybe_base64(f) if isinstance(f, str) else f for f in fetched]
        out.extend(fetched)
    return [c for c in out if c]
