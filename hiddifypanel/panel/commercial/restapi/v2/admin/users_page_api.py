"""Users page of the new dashboard: list with status, create/edit, quick actions and bulk actions.

Same rules as the classic user admin (UserAdmin.py): users of the signed-in admin and its sub-admins,
soft delete, at least one user kept, admin user limits, and apply after every change.
"""

from __future__ import annotations

import datetime
import json
import re
import uuid as uuid_lib
from typing import Any

from apiflask import abort
from flask import request
from flask.views import MethodView

from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.drivers import user_driver
from hiddifypanel.models import AdminUser, Child, ConfigEnum, User, UserDetail, UserMode, hconfig, set_hconfig
from hiddifypanel.models.outbound import Outbound
from hiddifypanel.models.role import Role
from hiddifypanel.models.tag import tags_of
from hiddifypanel.models.user import package_mode_dic
from hiddifypanel.panel import hiddify
from hiddifypanel.proxy_v3 import outbounds as ob
from hiddifypanel.proxy_v3 import user_configs

from .admins_api import _link_domains

ALL_ROLES = {Role.super_admin, Role.admin, Role.agent}
#: Extra-param keys the form manages itself (not shown in the JSON editor).
MANAGED_EXTRA = ("preferred_outbound", user_configs.EXTRA_KEY)
MAX_PACKAGE_DAYS = 10000
MAX_USAGE_GB = 1_000_000
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


# --------------------------------------------------------------------------- reading


def _visible_admin_ids() -> list[int]:
    return g.account.recursive_sub_admins_ids()


def _users_query():
    return User.query.filter(User.added_by.in_(_visible_admin_ids()), User.deleted.is_(False))


def _node_rows(user_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    """Per-node status per user (last connection + usage in the current period), one query for the batch.

    Only users that had traffic through a node have a row there; newest connection first.
    """
    if not user_ids:
        return {}
    rows = UserDetail.query.filter(UserDetail.user_id.in_(user_ids)).order_by(UserDetail.last_online.desc()).all()
    if not rows:
        return {}
    names = {c.id: (c.name or f"node-{c.id}") for c in Child.query.filter(Child.id.in_({r.child_id for r in rows})).all()}
    out: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        out.setdefault(row.user_id, []).append(
            {
                "child_id": row.child_id,
                "name": names.get(row.child_id) or f"node-{row.child_id}",
                "last_online": _iso(row.last_online),
                "usage": int(row.current_usage or 0),
            }
        )
    return out


def _status(user: User) -> str:
    """One clear state: disabled (turned off) > expired (no days left) > no_data (usage used up) > active."""
    if not user.enable:
        return "disabled"
    if user.remaining_days < 0:
        return "expired"
    if user.usage_limit < user.current_usage:
        return "no_data"
    return "active"


def _iso(value: datetime.date | datetime.datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return None if value.year < 1970 else value.isoformat()
    return value.isoformat()


def _row(user: User, admins: dict[int, AdminUser], tag_map: dict[str, list[int]] | None = None, nodes: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    owner = admins.get(user.added_by or 0)
    extra = user.extra_params_json()
    expires = user.start_date + datetime.timedelta(days=user.package_days or 0) if user.start_date else None
    periodic = user.mode in package_mode_dic
    return {
        "id": user.id,
        "uuid": user.uuid,
        "name": user.name,
        "comment": user.comment or "",
        "enable": bool(user.enable),
        "status": _status(user),
        "current_usage_GB": round(user.current_usage_GB, 3),
        "usage_limit_GB": round(user.usage_limit_GB, 3),
        "package_days": user.package_days,
        "remaining_days": user.remaining_days,
        # Not started: the package starts at the first connection.
        "start_date": _iso(user.start_date),
        "expire_date": _iso(expires),
        "mode": str(user.mode or UserMode.no_reset),
        "days_to_reset": user.days_to_reset() if periodic else None,
        "last_reset_time": _iso(user.last_reset_time),
        "last_online": _iso(user.last_online),
        # Per-node status (last connection + usage in the current period), newest first.
        "nodes": nodes or [],
        "owner_uuid": owner.uuid if owner else None,
        "owner_name": owner.name if owner else "",
        "preferred_outbound": ob.preferred_outbound_id(extra),
        "additional_configs": len(extra.get(user_configs.EXTRA_KEY) or []) if isinstance(extra.get(user_configs.EXTRA_KEY), list) else 0,
        "telegram_id": user.telegram_id or None,
        "tags": (tag_map if tag_map is not None else tags_of("user", [user.uuid])).get(user.uuid, []),
    }


def _detail(user: User, admins: dict[int, AdminUser]) -> dict[str, Any]:
    extra = user.extra_params_json()
    rows, _problems = user_configs.clean_rows(extra.get(user_configs.EXTRA_KEY))
    rest = {k: v for k, v in extra.items() if k not in MANAGED_EXTRA}
    return {
        **_row(user, admins, nodes=_node_rows([user.id]).get(user.id)),
        "additional_configs": rows,
        # Rows the user also gets from its admin and the admins above.
        "inherited_configs": len(user_configs.inherited_rows(user.uuid)),
        "extra_params": json.dumps(rest, indent=2, ensure_ascii=False) if rest else "{}",
    }


def _admins_map() -> dict[int, AdminUser]:
    ids = _visible_admin_ids()
    return {a.id: a for a in AdminUser.query.filter(AdminUser.id.in_(ids)).all()}


def _meta(admins: dict[int, AdminUser]) -> dict[str, Any]:
    actor: AdminUser = g.account
    outbounds = ob.ordered_rows(0)
    return {
        "me_uuid": actor.uuid,
        "link_domains": _link_domains(ConfigEnum.proxy_path_client),
        "admins": [
            {"uuid": a.uuid, "name": a.name, "parent_uuid": a.parent_admin.uuid if a.parent_admin and a.parent_admin.id in admins and a.id != actor.id else None}
            for a in sorted(admins.values(), key=lambda a: a.id)
        ],
        "outbounds": [{"id": o.id, "name": o.name, "mode": str(o.mode), "enabled": bool(o.enabled)} for o in outbounds],
        "can_add": actor.can_have_more_users(),
    }


# --------------------------------------------------------------------------- writing


def _number(body: dict, key: str, *, low: float, high: float, integer: bool) -> float | int:
    try:
        value = int(body[key]) if integer else float(body[key])
    except (TypeError, ValueError, KeyError):
        abort(400, f"{key} must be a number")
    if not low <= value <= high:
        abort(400, f"{key} must be between {low:g} and {high:g}")
    return value


def _apply_fields(user: User, body: dict[str, Any], *, creating: bool) -> None:
    if creating or "name" in body:
        name = str(body.get("name") or "").strip()[:512]
        if not name:
            abort(400, "Name is required")
        user.name = name
    if "comment" in body:
        user.comment = str(body.get("comment") or "")[:512]
    if "enable" in body:
        user.enable = bool(body.get("enable"))
    if "usage_limit_GB" in body:
        user.usage_limit_GB = _number(body, "usage_limit_GB", low=0, high=MAX_USAGE_GB, integer=False)
    if "package_days" in body:
        user.package_days = _number(body, "package_days", low=0, high=MAX_PACKAGE_DAYS, integer=True)
    if "mode" in body:
        try:
            user.mode = UserMode(str(body.get("mode")))
        except ValueError:
            abort(400, "Unknown reset mode")
    if "telegram_id" in body:
        raw = body.get("telegram_id")
        user.telegram_id = int(raw) if str(raw or "").strip().isdigit() else None

    if "owner_uuid" in body and body.get("owner_uuid"):
        owner = AdminUser.by_uuid(str(body["owner_uuid"]))
        if not owner or owner.id not in _visible_admin_ids():
            abort(403, "The owner must be you or one of your sub-admins")
        user.added_by = owner.id

    # Quick actions (classic "reset package days" / "reset usage" switches).
    if body.get("reset_days"):
        user.start_date = None
    if body.get("reset_usage"):
        user.reset_usage()

    # Extra params: the JSON editor's keys plus the ones the form manages.
    extra = user.extra_params_json()
    if "extra_params" in body:
        raw = body.get("extra_params")
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except ValueError:
            abort(400, "Extra params must be valid JSON")
        if not isinstance(parsed, dict):
            abort(400, "Extra params must be a JSON object")
        extra = {k: v for k, v in extra.items() if k in MANAGED_EXTRA} | {k: v for k, v in parsed.items() if k not in MANAGED_EXTRA}
    if "preferred_outbound" in body:
        oid = body.get("preferred_outbound")
        if oid in (None, "", 0):
            extra.pop("preferred_outbound", None)
            extra.pop("outbound", None)  # legacy key
        else:
            if not Outbound.query.filter(Outbound.id == int(oid)).first():
                abort(400, "Unknown outbound")
            extra["preferred_outbound"] = int(oid)
    if user_configs.EXTRA_KEY in body:
        rows, problems = user_configs.clean_rows(body.get(user_configs.EXTRA_KEY))
        if problems:
            abort(400, "Additional configs: " + "; ".join(problems[:5]))
        if rows:
            extra[user_configs.EXTRA_KEY] = rows
        else:
            extra.pop(user_configs.EXTRA_KEY, None)
    user.extra_params = json.dumps(extra, ensure_ascii=False) if extra else "{}"


def _after_change(users: list[User]) -> None:
    for user in users:
        if user.is_active:
            user_driver.add_client(user)
        else:
            user_driver.remove_client(user)
    hiddify.quick_apply_users()
    hutils.node.parent.notify_childs_users_changed()


def _get_user(uuid: str) -> User:
    user = User.by_uuid(str(uuid))
    if not user or user.added_by not in _visible_admin_ids():
        abort(404, "User not found")
    return user


class UsersPageApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def get(self):
        """Users page: users of the signed-in admin and its sub-admins, with what the page needs"""
        admins = _admins_map()
        users = _users_query().order_by(User.id.desc()).all()
        tag_map = tags_of("user")
        nodes_map = _node_rows([u.id for u in users])
        return {"users": [_row(u, admins, tag_map, nodes_map.get(u.id)) for u in users], **_meta(admins)}

    def post(self):
        """Users page: add a user"""
        body = request.get_json(silent=True) or {}
        actor: AdminUser = g.account
        if not actor.can_have_more_users():
            abort(400, "User limit reached: you (or an admin above you) reached the max users, active users or total traffic")
        new_uuid = str(body.get("uuid") or uuid_lib.uuid4()).strip().lower()
        if not _UUID_RE.match(new_uuid):
            abort(400, "UUID is not valid")
        existing = User.query.filter(User.uuid == new_uuid).first()
        if existing and not existing.deleted:
            abort(400, "A user with this UUID exists")
        if existing:
            existing.purge(commit=False)  # a deleted user still held the UUID
        user = User(uuid=new_uuid, added_by=actor.id, enable=True, mode=UserMode.no_reset, current_usage=0)
        body.setdefault("usage_limit_GB", 100)
        body.setdefault("package_days", 30)
        _apply_fields(user, body, creating=True)
        db.session.add(user)
        db.session.commit()
        if hconfig(ConfigEnum.first_setup):
            set_hconfig(ConfigEnum.first_setup, False)
        _after_change([user])
        return {"user": _detail(user, _admins_map())}


class UserPageApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def get(self, uuid):
        """Users page: one user, with extra params and additional configs"""
        return {"user": _detail(_get_user(uuid), _admins_map())}

    def patch(self, uuid):
        """Users page: update a user (also inline edits and quick resets)"""
        user = _get_user(uuid)
        body = request.get_json(silent=True) or {}
        if "uuid" in body and str(body["uuid"]).strip().lower() != user.uuid:
            new_uuid = str(body["uuid"]).strip().lower()
            if not _UUID_RE.match(new_uuid):
                abort(400, "UUID is not valid")
            other = User.query.filter(User.uuid == new_uuid).first()
            if other and not other.deleted:
                abort(400, "A user with this UUID exists")
            if other:
                other.purge(commit=False)
            user_driver.remove_client(user)
            user.uuid = new_uuid
        _apply_fields(user, body, creating=False)
        db.session.commit()
        _after_change([user])
        return {"user": _detail(user, _admins_map())}

    def delete(self, uuid):
        """Users page: delete a user (kept as deleted; the UUID is freed when reused)"""
        user = _get_user(uuid)
        if User.query.filter(User.deleted.is_(False)).count() <= 1:
            abort(400, "At least one user must exist")
        user.remove(commit=False)
        db.session.commit()
        hiddify.quick_apply_users()
        hutils.node.parent.notify_childs_users_changed()
        return {"status": 200, "msg": "ok"}


BULK_ACTIONS = ("enable", "disable", "delete", "reset_usage", "reset_days", "add_days", "add_limits")


class UsersBulkApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def post(self):
        """Users page: one action on many users (enable, disable, delete, reset usage, reset days, add days, add limits)"""
        body = request.get_json(silent=True) or {}
        action = str(body.get("action") or "")
        if action not in BULK_ACTIONS:
            abort(400, "Unknown action")
        uuids = [str(u) for u in body.get("uuids") or []]
        users = _users_query().filter(User.uuid.in_(uuids)).all() if uuids else []
        if not users:
            abort(400, "No users selected")
        if action == "delete":
            if User.query.filter(User.deleted.is_(False)).count() - len(users) < 1:
                abort(400, "At least one user must exist")
            for user in users:
                user.remove(commit=False)
            db.session.commit()
            hiddify.quick_apply_users()
            hutils.node.parent.notify_childs_users_changed()
            return {"count": len(users)}
        days = _number(body, "days", low=1, high=3650, integer=True) if action == "add_days" else 0
        add_gb = 0.0
        if action == "add_limits":
            # Data and / or days on top of what each user has; at least one of them.
            add_gb = _number({"gb": body.get("gb") or 0}, "gb", low=0, high=MAX_USAGE_GB, integer=False)
            days = _number({"days": body.get("days") or 0}, "days", low=0, high=3650, integer=True)
            if not add_gb and not days:
                abort(400, "Give some data (GB) or days to add")
        for user in users:
            if action in ("enable", "disable"):
                user.enable = action == "enable"
            elif action == "reset_usage":
                user.reset_usage()
            elif action == "reset_days":
                user.start_date = None
            elif action == "add_days":
                user.package_days = min(MAX_PACKAGE_DAYS, (user.package_days or 0) + days)
            elif action == "add_limits":
                # "Unlimited" (the highest value) stays unlimited.
                if add_gb and user.usage_limit_GB < MAX_USAGE_GB:
                    user.usage_limit_GB = min(MAX_USAGE_GB, user.usage_limit_GB + add_gb)
                if days and (user.package_days or 0) < MAX_PACKAGE_DAYS:
                    user.package_days = min(MAX_PACKAGE_DAYS, (user.package_days or 0) + days)
        db.session.commit()
        _after_change(users)
        return {"count": len(users)}
