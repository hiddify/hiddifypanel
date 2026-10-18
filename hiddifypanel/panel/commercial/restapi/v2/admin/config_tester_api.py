"""Config tester (super admins): run every config of a subscription through xray / hiddify-core and time requests through each.

A test is a job (config_tester_jobs): POST starts it, the page reads its events with GET and can stop it with DELETE.
GET ``/config-tester/user-link/?q=…`` searches users by name/uuid and returns their subscription URLs for the typeahead.
"""

from __future__ import annotations

from typing import Any, NoReturn

from apiflask import abort
from flask import request
from flask.views import MethodView
from sqlalchemy import case, func, or_

from hiddifypanel.auth import login_required
from hiddifypanel.cache import redis_client
from hiddifypanel.models import ConfigEnum, User, hconfig
from hiddifypanel.models.role import Role
from hiddifypanel.proxy_v3 import config_tester, config_tester_jobs
from hiddifypanel.proxy_v3.config_tester_types import Event, JobPage, TesterError

PAGE_SIZE = 100
USER_SEARCH_LIMIT = 30


def _bad(message: str) -> NoReturn:
    """Answer 400 (``abort`` raises, but is not typed as never returning)."""
    abort(400, message)
    raise AssertionError("abort returns")  # pragma: no cover


def _body() -> dict[str, object]:
    raw = request.get_json(silent=True)
    return raw if isinstance(raw, dict) else {}


def _text(body: dict[str, object], key: str) -> str:
    value = body.get(key)
    return value.strip() if isinstance(value, str) else ""


def _number(body: dict[str, object], key: str, default: int, low: int, high: int) -> int:
    """A whole number between ``low`` and ``high``; ``default`` when it is missing."""
    value = body.get(key)
    if value is None or value == "" or value == 0:
        return default
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        _bad(f"{key} must be a number")
    try:
        number = int(value)
    except ValueError:
        _bad(f"{key} must be a number")
    return max(low, min(number, high))


def _user_subscription_url(user: User) -> str:
    """Full subscription URL on this panel's host (same shape as the Users page share link, without the #name)."""
    from hiddifypanel.panel.commercial.restapi.v2.admin.admins_api import _link_domains

    domains = _link_domains(ConfigEnum.proxy_path_client)
    base = domains[0]["base"] if domains else f"https://{request.host}/{hconfig(ConfigEnum.proxy_path_client)}/"
    return f"{base}{user.uuid}/"


def _user_status(user: User) -> str:
    """disabled > expired > no_data > active (same idea as the Users page)."""
    if not user.enable:
        return "disabled"
    if user.remaining_days < 0:
        return "expired"
    if (user.usage_limit or 0) < (user.current_usage or 0):
        return "no_data"
    return "active"


def _user_hit(user: User) -> dict[str, Any]:
    return {
        "name": user.name or "",
        "comment": user.comment or "",
        "uuid": user.uuid,
        "url": _user_subscription_url(user),
        "status": _user_status(user),
        "remaining_days": user.remaining_days,
        "package_days": user.package_days or 0,
        "current_usage_GB": round(user.current_usage_GB, 3),
        "usage_limit_GB": round(user.usage_limit_GB, 3),
    }


def _search_users(q: str, *, limit: int = USER_SEARCH_LIMIT) -> list[User]:
    """Users for the typeahead: empty ``q`` = recent list; else match name, note (comment) or uuid."""
    needle = q.strip()
    if needle.lower().startswith(("http://", "https://")):
        return []
    base = User.query.filter(User.deleted.is_(False))
    if not needle:
        return base.order_by(User.enable.desc(), User.id.desc()).limit(limit).all()
    lowered = needle.lower().removeprefix("uuid:")
    name_l = func.lower(User.name)
    comment_l = func.lower(func.coalesce(User.comment, ""))
    uuid_l = func.lower(User.uuid)
    rank = case(
        (name_l == lowered, 0),
        (name_l.like(f"{lowered}%"), 1),
        (uuid_l.like(f"{lowered}%"), 2),
        (comment_l.like(f"{lowered}%"), 3),
        else_=4,
    )
    return (
        base.filter(or_(name_l.like(f"%{lowered}%"), comment_l.like(f"%{lowered}%"), uuid_l.like(f"%{lowered}%")))
        .order_by(rank, User.enable.desc(), User.id.desc())
        .limit(limit)
        .all()
    )


class ConfigTesterUserLinkApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self) -> dict[str, Any]:
        """Config tester: users for the link typeahead (name / note / uuid); empty ``q`` lists recent users"""
        users = _search_users(str(request.args.get("q") or ""))
        return {"users": [_user_hit(u) for u in users]}


class ConfigTesterApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def post(self) -> dict[str, str]:
        """Config tester: start a test of a subscription link, contents or configs; answers with the job to read"""
        body = _body()
        url = _text(body, "url")
        pasted = body.get("content")
        content = pasted if isinstance(pasted, str) and pasted.strip() else None
        items = body.get("items")
        again = items if isinstance(items, list) and items else None
        if again is None and content is None and not url.startswith(("http://", "https://")):
            _bad("Give the subscription link (http or https) or the contents to test")
        test_url = _text(body, "test_url") or config_tester.DEFAULT_TEST_URL
        if not test_url.startswith(("http://", "https://")):
            _bad("The test URL must be http or https")
        workers = _number(body, "workers", 8, 1, 32)
        timeout = _number(body, "timeout", 10, 2, 60)
        repeats = _number(body, "repeats", config_tester.DEFAULT_REPEATS, 1, 10)
        app = _text(body, "app") or None
        if app not in (None, "hiddify", "xray", "clash"):
            _bad("app must be hiddify, xray or clash")

        job = config_tester_jobs.new_id()

        def stop() -> bool:
            return config_tester_jobs.is_cancelled(job, redis_client)

        if again is not None:  # test given configs again (no link needed)
            events = config_tester.rerun(again, app=app, test_url=test_url, workers=workers, timeout=timeout, repeats=repeats, should_stop=stop)
        else:
            events = config_tester.run(url, _text(body, "user_agent"), content=content, app=app, test_url=test_url, workers=workers, timeout=timeout, repeats=repeats, should_stop=stop)
        first: Event
        try:
            first = next(events)  # fetch and parse errors are a normal HTTP error
        except TesterError as e:
            _bad(str(e))
        except StopIteration:
            _bad("Nothing to test")
        return {"job": config_tester_jobs.create(job, first, events, redis_client)}


class ConfigTesterJobApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self, job_id: str) -> JobPage:
        """Config tester: the events of a test from place `after` (the page asks again and again until it is done)"""
        try:
            after = max(0, int(request.args.get("after", "0")))
        except ValueError:
            after = 0
        page = config_tester_jobs.read(job_id, after, PAGE_SIZE, redis_client)
        if page is None:
            abort(404, "This test is gone (it is kept for an hour)")
            raise AssertionError("abort returns")  # pragma: no cover
        return page

    def delete(self, job_id: str) -> dict[str, str]:
        """Config tester: stop a test"""
        config_tester_jobs.cancel(job_id, redis_client)
        return {"status": "stopping"}
