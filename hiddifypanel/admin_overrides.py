"""Settings an admin sets for its own users (and its sub-admins' users): ``AdminUser.override_settings``.

``{ConfigEnum key: value}``; only the settings marked ``admin_overridable`` in ConfigEnum (the user page's customization). A user sees the value of
the nearest admin above it that set one, else the panel's setting (``user_hconfig``).
"""

from __future__ import annotations

import re
from typing import Any

from flask import g, has_request_context

from hiddifypanel.models import ConfigEnum, hconfig
from hiddifypanel.models.config_enum import Lang, config_enum_members
from hiddifypanel.models.role import Role

#: The settings marked ``admin_overridable`` in ConfigEnum.
OVERRIDABLE: tuple[ConfigEnum, ...] = tuple(c for c in config_enum_members() if c.admin_overridable)
_URL_KEYS = {str(ConfigEnum.branding_site), str(ConfigEnum.user_page_url)}
_URL = re.compile(r"^https?://[^\s/]+\.[^\s/]+(/\S*)?$", re.IGNORECASE)
_MAX_LENGTH = 10000


def clean(value: Any) -> tuple[dict[str, str], list[str]]:
    """``value`` as stored: known keys with non-empty text only (empty: the panel's / the parent admin's setting), and
    the problems found (keys of bad values)."""
    out: dict[str, str] = {}
    problems: list[str] = []
    allowed = {str(k) for k in OVERRIDABLE}
    for key, raw in (value or {}).items() if isinstance(value, dict) else []:
        text = str(raw if raw is not None else "").strip()
        if key not in allowed or not text:
            continue
        if len(text) > _MAX_LENGTH or (key == str(ConfigEnum.lang) and text not in {lang.value for lang in Lang}) or (key in _URL_KEYS and not _URL.match(text)):
            problems.append(key)
            continue
        if key == str(ConfigEnum.branding_freetext):  # shown as HTML on the users' page
            from hiddifypanel.hutils.user_html import clean_user_html

            text = clean_user_html(text)
        out[key] = text
    return out, problems


def admin_value(admin: Any, key: ConfigEnum) -> str | None:
    """The value ``admin`` or the nearest admin above it set for ``key`` (None: none did)."""
    from hiddifypanel.proxy_v3.user_configs import admin_chain

    for a in reversed(admin_chain(admin)) if admin is not None else []:
        value = (a.override_settings or {}).get(str(key))
        if value not in (None, ""):
            return value
    return None


def user_hconfig(key: ConfigEnum, user: Any = None) -> Any:
    """``hconfig(key)`` as ``user`` (default: the signed-in user) sees it: its admins' value first."""
    if user is None and has_request_context():
        account = g.get("account")
        user = account if getattr(account, "role", None) == Role.user else None
    if user is not None and key in OVERRIDABLE:
        value = admin_value(getattr(user, "admin", None), key)
        if value is not None:
            return value
    return hconfig(key)
