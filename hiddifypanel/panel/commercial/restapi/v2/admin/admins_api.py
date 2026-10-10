"""Admins page of the new dashboard: the admin tree with usage, create/edit/delete, passwords."""

from __future__ import annotations

import datetime
import secrets
import string
import uuid as uuid_lib

from apiflask import abort
from flask import request
from flask.views import MethodView

from hiddifypanel import admin_credentials as creds
from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, ConfigEnum, Domain, DomainType, User, hconfig
from hiddifypanel.models.admin import AdminMode
from hiddifypanel.models.config_enum import Lang
from hiddifypanel.models.role import Role
from hiddifypanel.panel import hiddify
from hiddifypanel.proxy_v3 import user_configs

PASSWORD_LENGTH = 16
# Same window as the classic admin list: online = seen in the last 24 hours.
ONLINE_WINDOW = datetime.timedelta(days=1)
REQUIRED_LIMITS = ("max_users", "max_active_users")
OPTIONAL_LIMITS = ("max_online_users", "max_total_usage_GB")
ALL_ROLES = {Role.super_admin, Role.admin, Role.agent}


def _new_password() -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(PASSWORD_LENGTH))
        if any(c.islower() for c in password) and any(c.isupper() for c in password) and sum(c.isdigit() for c in password) >= 2:
            return password


def _is_super(admin: AdminUser) -> bool:
    return admin.mode == AdminMode.super_admin


def _can_create(actor: AdminUser) -> bool:
    return _is_super(actor) or bool(actor.can_add_admin)


def _admin_link(admin: AdminUser) -> str:
    return hiddify.get_account_panel_link(admin, request.host)


def _login_link(admin: AdminUser) -> str:
    """With an alias: the sign-in page (username filled in), no UUID in it. Without: the UUID link."""
    if admin.alias:
        from urllib.parse import quote

        return f"https://{request.host}/{hconfig(ConfigEnum.proxy_path_admin)}/?user={quote(admin.alias)}"
    return _admin_link(admin)


def _outbound_options() -> list[dict]:
    """Outbounds an admin can make the default for its users (the Outbounds page's order)."""
    from hiddifypanel.proxy_v3 import outbounds as ob

    return [{"id": o.id, "name": o.name, "mode": str(o.mode), "enabled": bool(o.enabled)} for o in ob.ordered_rows(0)]


def _apply_default_outbound(admin: AdminUser, value) -> None:
    """Set (or clear, with null / 0 / "") the outbound this admin's users leave through by default."""
    from hiddifypanel.models.outbound import Outbound

    if value in (None, "", 0, False):
        admin.default_outbound_id = None
        return
    try:
        oid = int(value)
    except (TypeError, ValueError):
        abort(400, "Unknown outbound")
    if not Outbound.query.filter(Outbound.id == oid).first():
        abort(400, "Unknown outbound")
    admin.default_outbound_id = oid


def _inherited_outbound(admin: AdminUser) -> int | None:
    """The default the admin gets from the admins above (None: automatic)."""
    for parent in reversed(user_configs.admin_chain(admin)[:-1]):
        if parent.default_outbound_id:
            return int(parent.default_outbound_id)
    return None


def _apply_alias(admin: AdminUser, value) -> None:
    """Set (or clear, with an empty value) ``admin.alias``; 400 when it is not allowed."""
    alias = creds.normalize_alias(value)
    problem = creds.alias_problem(alias, admin)
    if problem:
        db.session.rollback()
        abort(400, creds.ALIAS_MESSAGES.get(problem, "This alias can not be used"))
    admin.alias = alias or None


def _link_domains(path_key: ConfigEnum = ConfigEnum.proxy_path_admin) -> list[dict]:
    """Domains a panel link can use: this panel's address first, then the panel's domains (as the classic user list).

    ``path_key``: ``proxy_path_admin`` for admin links, ``proxy_path_client`` for user links.
    """
    current = request.host
    out = [{"domain": current, "label": current, "kind": "current", "base": f"https://{current}/{hconfig(path_key)}/"}]
    seen = {current}
    for d in Domain.get_domains():
        name = d.domain.replace("*", hutils.random.get_random_string(5, 15)) if "*" in d.domain else d.domain
        if not name or name in seen:
            continue
        seen.add(name)
        kind = "direct"
        if d.mode == DomainType.cdn and not d.is_sub_link_only():
            kind = "auto" if bool(d.resolve_ip) or (d.cdn_ip and "MTN" in d.cdn_ip) else "cdn"
        # A node's domain opens that node's panel, which has its own admin path.
        out.append({"domain": name, "label": d.alias or name, "kind": kind, "base": f"https://{name}/{hconfig(path_key, d.child_id)}/"})
    return out


def _limits(admin: AdminUser) -> dict | None:
    """None for a super admin: no limits."""
    if _is_super(admin):
        return None
    return {
        "max_users": admin.max_users,
        "max_active_users": admin.max_active_users,
        "max_online_users": admin.max_online_users,
        "max_total_usage_GB": admin.max_total_usage_GB,
    }


def _tree_stats(admins: list[AdminUser]) -> dict[int, dict]:
    """Users of each admin and all its sub-admins: total, active, online, traffic used."""
    ids = [a.id for a in admins]
    since = datetime.datetime.now() - ONLINE_WINDOW
    direct = {i: {"total": 0, "active": 0, "online": 0, "usage_GB": 0.0} for i in ids}
    for user in User.query.filter(User.added_by.in_(ids), User.deleted.is_(False)).all():
        row = direct.get(user.added_by)
        if row is None:
            continue
        row["total"] += 1
        row["active"] += 1 if user.is_active else 0
        row["online"] += 1 if user.last_online and user.last_online >= since else 0
        row["usage_GB"] += user.current_usage_GB or 0

    children: dict[int, list[int]] = {}
    for a in admins:
        if a.parent_admin_id in direct and a.parent_admin_id != a.id:
            children.setdefault(a.parent_admin_id, []).append(a.id)

    totals: dict[int, dict] = {}

    def walk(admin_id: int, seen: set[int]) -> dict:
        if admin_id in totals:
            return totals[admin_id]
        seen.add(admin_id)
        out = dict(direct[admin_id])
        for child in children.get(admin_id, []):
            if child in seen:
                continue
            sub = walk(child, seen)
            for key in out:
                out[key] += sub[key]
        totals[admin_id] = out
        return out

    for admin_id in ids:
        walk(admin_id, set())
    for row in totals.values():
        row["usage_GB"] = round(row["usage_GB"], 3)
    return totals


def _sub_admin_counts(admins: list[AdminUser]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for a in admins:
        if a.parent_admin_id and a.parent_admin_id != a.id:
            counts[a.parent_admin_id] = counts.get(a.parent_admin_id, 0) + 1
    return counts


def _row(admin: AdminUser, actor: AdminUser, stats: dict, sub_admins: int, visible_ids: set[int]) -> dict:
    is_me = admin.id == actor.id
    manageable = not is_me and admin.id != 1 and admin.id in visible_ids
    parent = admin.parent_admin
    return {
        "uuid": admin.uuid,
        "name": admin.name,
        "comment": admin.comment or "",
        "mode": str(admin.mode),
        "can_add_admin": bool(admin.can_add_admin),
        # The tree root (the signed-in admin) has no parent in this view.
        "parent_uuid": parent.uuid if parent and not is_me and parent.id in visible_ids else None,
        "parent_name": parent.name if parent else None,
        "is_me": is_me,
        "has_password": bool(admin.password),
        "alias": admin.alias or "",
        "admin_link": _admin_link(admin),
        "limits": _limits(admin),
        "stats": stats,
        "sub_admins": sub_admins,
        # Added to the subscription of every user of this admin and its sub-admins.
        "additional_configs": user_configs.clean_rows(admin.additional_configs or [])[0],
        # Outbound id this admin's users use unless they choose another (null: automatic / inherited).
        "default_outbound": admin.default_outbound_id,
        "inherited_outbound": _inherited_outbound(admin),
        "can_edit": manageable and (not _is_super(admin) or _is_super(actor)),
        "can_delete": manageable and (not _is_super(admin) or _is_super(actor)),
    }


def _visible_admins(actor: AdminUser) -> list[AdminUser]:
    ids = actor.recursive_sub_admins_ids()
    return AdminUser.query.filter(AdminUser.id.in_(ids)).order_by(AdminUser.id).all()


def _managed_target(uuid) -> AdminUser:
    actor: AdminUser = g.account
    admin = AdminUser.by_uuid(str(uuid)) or abort(404, "Admin not found")
    if admin.id == actor.id:
        abort(403, "Your own account can not be changed here")
    if admin.id == 1 or admin.id not in actor.recursive_sub_admins_ids():
        abort(403, "You don't have permission to manage this admin")
    if _is_super(admin) and not _is_super(actor):
        abort(403, "Only a super admin can manage a super admin")
    return admin


def _number(body: dict, key: str, *, integer: bool) -> float | int | None:
    value = body.get(key)
    if value is None or value == "":
        return None
    try:
        number = int(value) if integer else float(value)
    except (TypeError, ValueError):
        abort(400, f"{key} must be a number")
    if number < 0:
        abort(400, f"{key} can not be negative")
    return number


def _clean_payload(body: dict, *, target: AdminUser | None) -> dict:
    """Validated fields for create (target None) or edit. Never raises the caller's own power."""
    actor: AdminUser = g.account
    creating = target is None
    out: dict = {}

    if creating or "name" in body:
        name = str(body.get("name") or "").strip()
        if not name:
            abort(400, "Name is required")
        out["name"] = name[:512]
    if "comment" in body:
        out["comment"] = str(body.get("comment") or "")[:512]

    if creating and body.get("uuid"):
        value = str(body["uuid"]).strip().lower()
        if not hutils.auth.is_uuid_valid(value):
            abort(400, "UUID is not valid")
        if AdminUser.by_uuid(value) or User.by_uuid(value):
            abort(400, "This UUID is already used")
        out["uuid"] = value

    if "can_add_admin" in body:
        want = bool(body.get("can_add_admin"))
        if want and not _can_create(actor):
            abort(403, "You can not allow adding sub-admins")
        out["can_add_admin"] = want

    if not (target is not None and _is_super(target)):
        for key in (*REQUIRED_LIMITS, *OPTIONAL_LIMITS):
            if not creating and key not in body:
                continue
            value = _number(body, key, integer=key != "max_total_usage_GB")
            mine = None if _is_super(actor) else getattr(actor, key)
            if key in REQUIRED_LIMITS:
                if value is None:
                    if not creating:
                        abort(400, f"{key} is required")
                    value = min(100, mine) if mine is not None else 100
            elif not value:
                value = 0  # 0 = no limit
            if mine and (value > mine or (key in OPTIONAL_LIMITS and value == 0)):
                abort(400, f"{key} can be at most {mine:g} (your own limit)")
            out[key] = value

    if creating or "parent_uuid" in body:
        parent_uuid = body.get("parent_uuid") or actor.uuid
        parent = AdminUser.by_uuid(str(parent_uuid)) or abort(400, "Parent admin not found")
        if parent.id not in actor.recursive_sub_admins_ids():
            abort(403, "The parent must be you or one of your sub-admins")
        if target is not None and parent.id in target.recursive_sub_admins_ids():
            abort(400, "An admin can not be moved under itself or its sub-admins")
        if not (_is_super(parent) or parent.can_add_admin) and parent.id != actor.id:
            abort(400, "The parent admin is not allowed to have sub-admins")
        out["parent_admin_uuid"] = parent.uuid
    return out


def _configs_or_400(body: dict) -> list[list[str]]:
    rows, problems = user_configs.clean_rows(body.get("additional_configs"))
    if problems:
        abort(400, "Additional configs: " + "; ".join(problems[:5]))
    return rows


def _credentials(admin: AdminUser, password: str) -> dict:
    # With an alias the admin signs in with username + password: the link carries no UUID.
    return {"password": password, "admin_link": _login_link(admin), "alias": admin.alias or ""}


class AdminsTreeApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def get(self):
        """Admins page: the signed-in admin and all its sub-admins with their users' usage"""
        actor: AdminUser = g.account
        admins = _visible_admins(actor)
        stats = _tree_stats(admins)
        subs = _sub_admin_counts(admins)
        visible = {a.id for a in admins}
        return {
            "me_uuid": actor.uuid,
            "can_create": _can_create(actor),
            "my_limits": _limits(actor),
            "link_domains": _link_domains(),
            "outbounds": _outbound_options(),
            "admins": [_row(a, actor, stats[a.id], subs.get(a.id, 0), visible) for a in admins],
        }

    def post(self):
        """Admins page: create an agent with a generated password"""
        actor: AdminUser = g.account
        if not _can_create(actor):
            abort(403, "You don't have permission to add admins")
        body = request.get_json(silent=True) or {}
        payload = _clean_payload(body, target=None)
        configs = _configs_or_400(body) if "additional_configs" in body else []
        payload.setdefault("uuid", str(uuid_lib.uuid4()))
        payload["mode"] = AdminMode.agent
        admin = AdminUser.add_or_update(commit=False, **payload)
        admin.additional_configs = configs
        if "default_outbound" in body:
            _apply_default_outbound(admin, body.get("default_outbound"))
        password = _new_password()
        admin.password = password
        if body.get("alias"):
            db.session.flush()
            _apply_alias(admin, body.get("alias"))
        db.session.commit()
        hutils.node.parent.notify_childs_users_changed()
        return {"uuid": admin.uuid, "name": admin.name, **_credentials(admin, password)}


class AdminTreeItemApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def patch(self, uuid):
        """Admins page: update a sub-admin"""
        admin = _managed_target(uuid)
        body = request.get_json(silent=True) or {}
        payload = _clean_payload(body, target=admin)
        if "additional_configs" in body:
            admin.additional_configs = _configs_or_400(body)
        if "alias" in body:
            _apply_alias(admin, body.get("alias"))
        if "default_outbound" in body:
            _apply_default_outbound(admin, body.get("default_outbound"))
        if "comment" in payload:
            admin.comment = payload.pop("comment")  # upsert skips empty text
        AdminUser.add_or_update(commit=False, old_uuid=admin.uuid, uuid=admin.uuid, **payload)
        db.session.commit()
        hutils.node.parent.notify_childs_users_changed()
        # The server's routing follows the users' (and admins') outbounds.
        return {"status": 200, "msg": "ok", **({"restart_mode": "apply_config"} if "default_outbound" in body else {})}

    def delete(self, uuid):
        """Admins page: delete a sub-admin (its sub-admins too; their users move to you)"""
        admin = _managed_target(uuid)
        admin.remove()
        hutils.node.parent.notify_childs_users_changed()
        return {"status": 200, "msg": "ok"}


class AdminResetPasswordApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def post(self, uuid):
        """Admins page: give a sub-admin a new generated password"""
        admin = _managed_target(uuid)
        password = _new_password()
        admin.update_password(password)
        return _credentials(admin, password)


class MyAdminAccountApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def get(self):
        """My account: limits, usage and login of the signed-in admin"""
        actor: AdminUser = g.account
        admins = _visible_admins(actor)
        stats = _tree_stats(admins)
        parent = actor.parent_admin if actor.id != 1 else None
        return {
            "uuid": actor.uuid,
            "name": actor.name,
            "mode": str(actor.mode),
            "can_add_admin": _can_create(actor),
            "parent_name": parent.name if parent and parent.id != actor.id else None,
            "has_password": bool(actor.password),
            "strong_password": creds.is_strong(actor.password, avoid=creds.admin_avoid(actor)),
            "telegram_connected": bool(actor.telegram_id),
            "alias": actor.alias or "",
            # My own interface language ("" = the panel's default admin language).
            "lang": str(getattr(actor.lang, "value", actor.lang)) if actor.lang else "",
            "default_lang": str(hconfig(ConfigEnum.admin_lang) or "en"),
            "languages": [lang.value for lang in Lang],
            "can_alias": actor.mode != AdminMode.super_admin,
            "login_link": _login_link(actor),
            "admin_link": _admin_link(actor),
            "limits": _limits(actor),
            "stats": stats[actor.id],
            "sub_admins": len(admins) - 1,
            "additional_configs": user_configs.clean_rows(actor.additional_configs or [])[0],
            "default_outbound": actor.default_outbound_id,
            "inherited_outbound": _inherited_outbound(actor),
            "outbounds": _outbound_options(),
            # From the admins above: also added to this admin's users (read only here).
            "inherited_configs": len(user_configs.merge_rows(*[user_configs.clean_rows(a.additional_configs or [])[0] for a in user_configs.admin_chain(actor)[:-1]])),
        }


class MyAdminConfigsApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def put(self):
        """My account: additional configs for all users of the signed-in admin and its sub-admins"""
        actor: AdminUser = g.account
        actor.additional_configs = _configs_or_400(request.get_json(silent=True) or {})
        db.session.commit()
        hutils.node.parent.notify_childs_users_changed()
        return {"additional_configs": actor.additional_configs}


class MyAdminOutboundApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def put(self):
        """My account: the default outbound of my users (and my sub-admins' users)"""
        actor: AdminUser = g.account
        _apply_default_outbound(actor, (request.get_json(silent=True) or {}).get("default_outbound"))
        db.session.commit()
        hutils.node.parent.notify_childs_users_changed()
        return {"default_outbound": actor.default_outbound_id, "restart_mode": "apply_config"}


class MyAdminAliasApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def put(self):
        """My account: set or clear my alias (sign-in username); needs a strong password, not for super admins"""
        actor: AdminUser = g.account
        _apply_alias(actor, (request.get_json(silent=True) or {}).get("alias"))
        db.session.commit()
        return {"alias": actor.alias or "", "login_link": _login_link(actor)}


class MyAdminLanguageApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def put(self):
        """My account: the language of my admin interface (empty: the panel's default)"""
        actor: AdminUser = g.account
        value = str((request.get_json(silent=True) or {}).get("lang") or "").strip()
        if value and value not in {lang.value for lang in Lang}:
            abort(400, "Unknown language")
        actor.lang = Lang(value) if value else None
        db.session.commit()
        return {"lang": value}


class MyAdminPasswordApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def put(self):
        """My account: change the signed-in admin's password"""
        actor: AdminUser = g.account
        body = request.get_json(silent=True) or {}
        current = str(body.get("current_password") or "")
        new = str(body.get("new_password") or "")
        if actor.password and not secrets.compare_digest(current, actor.password):
            return {"message": "The current password is wrong", "code": "wrong_current"}, 400
        problems = creds.password_problems(new, avoid=creds.admin_avoid(actor))
        if problems:
            return {"message": creds.PASSWORD_MESSAGE, "code": "weak", "problems": problems}, 400
        actor.update_password(new)
        return {"status": 200, "msg": "ok"}
