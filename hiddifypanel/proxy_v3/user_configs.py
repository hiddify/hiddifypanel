"""Per-user additional configs (Users → edit → Additional configs), merged into the user's subscription.

Stored in the user's extra params as ``additional_configs``: a JSON list of ``[kind, target, value]``:

* ``kind``    ``offline`` (``value`` is the config itself) or ``subscription`` (``value`` is a URL to fetch)
* ``target``  the client format it is for: ``sublink`` | ``xray`` | ``hiddify-core`` | ``clash`` | ``auto`` (every format)
* ``value``   share links / JSON / YAML, or the URL

Admins can have the same list (``AdminUser.additional_configs``): it goes to every user of the admin and of
its sub-admins. A user gets, in order, the rows of the top admin down to its own admin, then its own rows;
identical rows count once.

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


def admin_chain(admin: Any) -> list[Any]:
    """``admin`` and its parents, top admin first (stops on loops)."""
    chain: list[Any] = []
    seen: set[int] = set()
    while admin is not None and admin.id not in seen:
        seen.add(admin.id)
        chain.append(admin)
        parent = admin.parent_admin
        admin = parent if parent is not None and parent.id != admin.id else None
    return list(reversed(chain))


def inherited_rows(user_uuid: str | None) -> list[list[str]]:
    """Rows the user gets from its admin and every admin above (top first)."""
    if not user_uuid:
        return []
    from hiddifypanel.models import AdminUser, User

    user = User.query.filter(User.uuid == str(user_uuid)).first()
    owner = AdminUser.by_id(user.added_by) if user and user.added_by else None
    return merge_rows(*[clean_rows(admin.additional_configs or [])[0] for admin in admin_chain(owner)])


def merge_rows(*groups: list[list[str]]) -> list[list[str]]:
    """All rows in order; identical rows once."""
    out: list[list[str]] = []
    seen: set[tuple[str, str, str]] = set()
    for group in groups:
        for row in group:
            key = (row[0], row[1], row[2])
            if key not in seen:
                seen.add(key)
                out.append(list(row))
    return out


def _own_rows(extra: Any) -> list[list[str]]:
    getter = getattr(extra, "get", None)
    raw = getter(EXTRA_KEY) if callable(getter) else None
    rows, _problems = clean_rows(list(raw) if isinstance(raw, (list, tuple)) else raw)
    return rows


def _rows_for(user: Any, core: str) -> list[list[str]]:
    try:
        inherited = inherited_rows(getattr(user, "uuid", None))
    except Exception:  # no database (e.g. a template preview without a user row)
        inherited = []
    rows = merge_rows(inherited, _own_rows(getattr(user, "extra_params", None) or {}))
    want = "hiddify-core" if core == "singbox" else core
    return [r for r in rows if r[1] in (want, "auto")]


@pass_context
def user_additional_configs(context: Any, core: str, cache: str = "1h") -> list[Any]:
    """The current user's additional configs for ``core``: one parsed config per row (text for sublink)."""
    ctx = context.get("ctx")
    user = getattr(ctx, "user", None)
    if user is None:
        return []
    rows = _rows_for(user, core)
    out: list[Any] = [_parse_offline(r[2], core) for r in rows if r[0] == "offline"]
    urls = [r[2] for r in rows if r[0] == "subscription"]
    if urls:
        fetched = download(context, _FETCH_TYPE.get(core, "json"), cache, *urls)
        if core == "sublink":
            fetched = [_maybe_base64(f) if isinstance(f, str) else f for f in fetched]
        out.extend(fetched)
    return [c for c in out if c]
