"""Is there a newer panel? The latest hiddifypanel release on GitHub against this panel's version.

The answer is kept 24 hours (so the panel asks GitHub at most once a day, whoever opens it); ``?force=1`` (the
"Check for updates" button) asks again at once. A release install looks only at releases; a beta install also at
pre-releases.
"""

from __future__ import annotations

import json
import time

from flask import request
from flask.views import MethodView
from packaging.version import InvalidVersion, Version

from hiddifypanel import __version__ as current_version
from hiddifypanel.auth import login_required
from hiddifypanel.cache import redis_client
from hiddifypanel.hutils import LazyLoader
from hiddifypanel.models import Role
from hiddifypanel.models.config import ConfigEnum, hconfig

requests = LazyLoader("requests")

CHECK_EVERY_S = 24 * 3600
#: a failed look is tried again sooner than a day
RETRY_AFTER_ERROR_S = 3600
REDIS_KEY = "hiddify:panel_update_check"
RELEASES_URL = "https://api.github.com/repos/hiddify/hiddifypanel/releases?per_page=30"


def _version(text: str) -> Version | None:
    try:
        return Version(text.lstrip("vV"))
    except InvalidVersion:
        return None


def _channel() -> str:
    return "release" if (hconfig(ConfigEnum.package_mode) or "release") == "release" else "beta"


def _fetch_latest(channel: str) -> str:
    """The highest version on the channel; raises when GitHub cannot be asked."""
    response = requests.get(RELEASES_URL, timeout=10, headers={"Accept": "application/vnd.github+json", "User-Agent": "hiddify-panel"})
    response.raise_for_status()
    best: Version | None = None
    for release in response.json():
        if release.get("draft"):
            continue
        version = _version(str(release.get("tag_name", "")))
        if not version or (channel == "release" and (release.get("prerelease") or version.is_prerelease)):
            continue
        if best is None or version > best:
            best = version
    if best is None:
        raise ValueError("no release found")
    return str(best)


def panel_update_status(force: bool = False) -> dict:
    """``current``, ``latest``, ``outdated``, ``channel``, ``checked_at`` (unix seconds) and ``error`` (a failed look)."""
    channel = _channel()
    stored: dict = {}
    try:
        stored = json.loads(redis_client.get(REDIS_KEY) or "{}")
    except Exception:
        stored = {}
    age = time.time() - float(stored.get("checked_at") or 0)
    fresh = stored.get("channel") == channel and age < (RETRY_AFTER_ERROR_S if stored.get("error") else CHECK_EVERY_S)
    if force or not fresh:
        try:
            stored = {"latest": _fetch_latest(channel), "error": None}
        except Exception as e:
            # a failed look keeps the last answer it had
            stored = {"latest": stored.get("latest") if stored.get("channel") == channel else None, "error": str(e)[:200]}
        stored.update(channel=channel, checked_at=int(time.time()))
        try:
            redis_client.set(REDIS_KEY, json.dumps(stored), ex=CHECK_EVERY_S * 2)
        except Exception:
            pass
    latest = stored.get("latest")
    now, new = _version(current_version), _version(latest or "")
    return {
        "current": current_version,
        "latest": latest,
        "outdated": bool(now and new and new > now),
        "channel": channel,
        "checked_at": stored.get("checked_at"),
        "error": stored.get("error"),
    }


class PanelVersionApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        """System: Panel version and the latest release"""
        return panel_update_status(force=request.args.get("force") in ("1", "true", "yes"))
