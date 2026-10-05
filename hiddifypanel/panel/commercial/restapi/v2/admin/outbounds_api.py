"""Outbound manager API (super admins): where server traffic leaves (WARP, direct, block, SOCKS, Tor, Psiphon, and the admin's own
hiddify-core outbound / endpoint and xray outbound JSON).

Outbounds are rules in order; the last enabled one is the default (everything else goes there).
"""

from __future__ import annotations

from typing import Any

from apiflask import abort
from flask import request
from flask.views import MethodView

from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, ConfigEnum, hconfig
from hiddifypanel.models.child import Child
from hiddifypanel.models.outbound import BUILTIN_MODES, CONFIGURABLE_ENDPOINT_MODES, CUSTOM_CONFIG_MODES, ENDPOINT_MODES, LIST_FIELDS, MULTI_MODES, Outbound, OutboundMode
from hiddifypanel.models.role import Role
from hiddifypanel.proxy_v3 import outbound_custom as custom_config
from hiddifypanel.proxy_v3 import outbounds as ob

#: Every change needs the server configs regenerated.
APPLY = "apply_config"


def _parent_only() -> None:
    """Outbounds are defined on the parent panel and copied to its nodes."""
    from hiddifypanel import hutils

    if hutils.node.is_child():
        abort(403, "Outbounds are managed by the parent panel")


def _changed() -> None:
    """Commit is done: ask the nodes to take the new outbounds (users and admins refer to their ids)."""
    from hiddifypanel import hutils

    hutils.node.parent.notify_childs_users_changed()


def _child_id() -> int:
    return Child.current().id


def _custom_out(row: Outbound) -> dict[str, Any]:
    """Custom JSON outbounds: the text, the tag the panel gave it (its slug) and the local SOCKS bridge port the other core connects to."""
    if row.mode not in CUSTOM_CONFIG_MODES:
        return {}
    return {"config": row.config or "", "tag": custom_config.custom_tag(row), "bridge_port": custom_config.bridge_port(row.id), "runs_in": "xray" if row.mode == OutboundMode.xray_outbound else "hiddify-core"}


def _row_out(row: Outbound, default: Outbound | None) -> dict[str, Any]:
    builtin = row.builtin_lists or {}
    endpoint = ob.default_endpoint(row.mode)
    configurable = row.mode in CONFIGURABLE_ENDPOINT_MODES
    is_default = row is default
    return {
        "id": row.id,
        "slug": row.slug,
        "name": row.name,
        "mode": str(row.mode),
        "position": row.position,
        "enabled": bool(row.enabled),
        "is_default": is_default,
        "has_rules": ob.has_rules(row),
        # Routes something: the default, or an enabled outbound with sites / geosites / rule-sets.
        "active": bool(row.enabled) and (is_default or ob.has_rules(row)),
        "domestic": bool(row.domestic),
        "sites": list(row.sites or []),
        "geosites": list(row.geosites or []),
        "rule_sets": list(row.rule_sets or []),
        # SOCKS: the admin's endpoint. Tor / Psiphon: the fixed local port (read only).
        "host": (row.host or "") if configurable else str(endpoint.get("host") or ""),
        "port": row.port if configurable else endpoint.get("port"),
        "username": (row.username or "") if configurable else "",
        # The password is never sent back; `has_password` tells whether one is set.
        "has_password": bool(row.password) and configurable,
        **_custom_out(row),
        "is_builtin": bool(row.is_builtin),
        "lists_override": bool(row.lists_override),
        "builtin_lists": {field: list(builtin.get(field) or []) for field in LIST_FIELDS} | {"domestic": bool(builtin.get("domestic"))},
    }


def _list_out(child_id: int) -> dict[str, Any]:
    rows = ob.ordered_rows(child_id)
    default = ob.default_row(rows)
    used_single = {str(r.mode) for r in rows if r.mode not in MULTI_MODES}
    var = ob.build_outbounds_var(child_id)
    domestic = (ob.load_defaults().get("domestic") or {}).get(var.region) or {}
    from hiddifypanel import hutils

    return {
        # A node only shows the parent's outbounds.
        "managed_by_parent": hutils.node.is_child(),
        "outbounds": [_row_out(r, default) for r in rows],
        "region": var.region,
        "domestic": {k: list(domestic.get(k) or []) for k in ("sites", "geosites", "rule_sets")},
        "warp_mode": str(hconfig(ConfigEnum.warp_mode, child_id) or "disable"),
        # Modes that can still be added (single-instance ones only once).
        "addable_modes": [str(m) for m in OutboundMode if m not in BUILTIN_MODES and (m in MULTI_MODES or str(m) not in used_single)],
        "endpoints": {str(m): ob.default_endpoint(m) for m in ENDPOINT_MODES},
    }


def _finalize_or_400(child_id: int, rows: list[Outbound]) -> None:
    try:
        ob.finalize(child_id, rows)
    except ob.OutboundOrderError as e:
        db.session.rollback()
        abort(400, str(e))


def _clean_lists(body: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for field in LIST_FIELDS:
        if field not in body:
            continue
        values = ob.clean_list(field, body.get(field) or [])
        bad = ob.invalid_entries(field, values)
        if bad:
            abort(400, f"{field}: invalid entries: {', '.join(bad[:5])}")
        if len(values) > 5000:
            abort(400, f"{field}: too many entries")
        out[field] = values
    return out


def _apply_body(row: Outbound, body: dict[str, Any], *, creating: bool) -> None:
    if creating or "name" in body:
        name = str(body.get("name") or "").strip()[:100]
        if not name:
            abort(400, "Name is required")
        clash = Outbound.query.filter(Outbound.name == name, Outbound.id != (row.id or 0)).first()
        if clash:
            abort(400, "Another outbound has this name")
        row.name = name

    # The admin's own JSON: it must pass the checks (and the real core) or nothing is stored.
    if row.mode in CUSTOM_CONFIG_MODES and (creating or "config" in body):
        try:
            cfg = custom_config.validate(row.mode, body.get("config"))
        except custom_config.CustomOutboundError as e:
            abort(400, str(e))
        row.config = custom_config.normalized(cfg)

    if "enabled" in body:
        row.enabled = bool(body.get("enabled"))

    lists = _clean_lists(body)
    touched_lists = bool(lists) or "domestic" in body
    for field, values in lists.items():
        setattr(row, field, values)
    if "domestic" in body:
        row.domestic = bool(body.get("domestic"))
    if row.is_builtin and touched_lists and not creating:
        # Edited by the admin: upgrades keep these lists (unless they match the defaults file again).
        row.lists_override = ob.current_lists(row) != (row.builtin_lists or {})

    # Only SOCKS has an editable endpoint; Tor and Psiphon use their local port from the defaults file.
    if row.mode in CONFIGURABLE_ENDPOINT_MODES:
        endpoint = ob.default_endpoint(row.mode)
        if creating or "host" in body:
            row.host = str(body.get("host") or endpoint.get("host") or "").strip()[:255]
        if creating or "port" in body:
            raw = body.get("port") if body.get("port") not in (None, "") else endpoint.get("port")
            try:
                row.port = int(raw)
            except (TypeError, ValueError):
                abort(400, "Port must be a number")
        if not row.host:
            abort(400, "Host is required")
        if not row.port or not 1 <= int(row.port) <= 65535:
            abort(400, "Port must be between 1 and 65535")
        if "username" in body:
            row.username = str(body.get("username") or "").strip()[:255]
        # An empty or missing password keeps the current one; `clear_password` removes it.
        if body.get("password"):
            row.password = str(body["password"])[:255]
        if body.get("clear_password"):
            row.password = ""


class OutboundsApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        """Outbounds: list in rule order (the last enabled one is the default)"""
        child_id = _child_id()
        ob.sync_builtin_outbounds(child_id)
        return _list_out(child_id)

    def post(self):
        """Outbounds: add a SOCKS, Tor or Psiphon outbound (placed just before the default)"""
        _parent_only()
        child_id = _child_id()
        body = request.get_json(silent=True) or {}
        try:
            mode = OutboundMode(str(body.get("mode") or ""))
        except ValueError:
            abort(400, "Unknown outbound mode")
        if mode in BUILTIN_MODES:
            abort(400, "WARP, Direct and Block exist already")
        if mode not in MULTI_MODES and Outbound.query.filter(Outbound.mode == mode).first():
            abort(400, f"There can be only one {mode} outbound")
        row = Outbound(mode=mode, is_builtin=False, enabled=True)
        _apply_body(row, body, creating=True)
        row.slug = Outbound.make_slug(row.name, mode)
        db.session.add(row)
        db.session.flush()
        rows = ob.move_before_default(ob.ordered_rows(child_id), row)
        _finalize_or_400(child_id, rows)
        db.session.commit()
        _changed()
        return {"created_id": row.id, "restart_mode": APPLY, **_list_out(child_id)}


def _get_row(outbound_id: int) -> Outbound:
    row = Outbound.query.filter(Outbound.id == outbound_id).first()
    return row or abort(404, "Outbound not found")


class OutboundApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def patch(self, outbound_id: int):
        """Outbounds: update one"""
        _parent_only()
        row = _get_row(outbound_id)
        _apply_body(row, request.get_json(silent=True) or {}, creating=False)
        _finalize_or_400(_child_id(), ob.ordered_rows(_child_id()))
        db.session.commit()
        _changed()
        return {"restart_mode": APPLY, **_list_out(_child_id())}

    def delete(self, outbound_id: int):
        """Outbounds: delete a SOCKS, Tor or Psiphon outbound"""
        _parent_only()
        row = _get_row(outbound_id)
        if row.is_builtin or row.mode in BUILTIN_MODES:
            abort(400, "WARP, Direct and Block can not be deleted")
        child_id = _child_id()
        # Admins whose default it was go back to automatic.
        AdminUser.query.filter(AdminUser.default_outbound_id == row.id).update({"default_outbound_id": None})
        db.session.delete(row)
        db.session.flush()
        _finalize_or_400(child_id, ob.ordered_rows(child_id))
        db.session.commit()
        _changed()
        return {"restart_mode": APPLY, **_list_out(child_id)}


class OutboundOrderApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def put(self):
        """Outbounds: set the order (ids, first checked first; the last enabled one is the default)"""
        _parent_only()
        child_id = _child_id()
        ids = (request.get_json(silent=True) or {}).get("ids")
        rows = ob.ordered_rows(child_id)
        by_id = {r.id: r for r in rows}
        if not isinstance(ids, list) or sorted(ids) != sorted(by_id):
            abort(400, "The order must list every outbound once")
        ordered = [by_id[i] for i in ids]
        ob.renumber(ordered)
        _finalize_or_400(child_id, ordered)
        db.session.commit()
        _changed()
        return {"restart_mode": APPLY, **_list_out(child_id)}


class OutboundDefaultApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def post(self, outbound_id: int):
        """Outbounds: make one the default (turns it on and moves it to the end)"""
        _parent_only()
        row = _get_row(outbound_id)
        if row.mode == OutboundMode.block:
            abort(400, "Block can not be the default: it would block everything")
        row.enabled = True
        _finalize_or_400(_child_id(), ob.move_to_end(ob.ordered_rows(_child_id()), row))
        db.session.commit()
        _changed()
        return {"restart_mode": APPLY, **_list_out(_child_id())}


class OutboundResetApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def post(self, outbound_id: int):
        """Outbounds: put a built-in outbound's lists back to the defaults file (upgrades update them again)"""
        _parent_only()
        row = _get_row(outbound_id)
        if not row.is_builtin:
            abort(400, "Only built-in outbounds have default lists")
        ob.reset_builtin_lists(row)
        db.session.commit()
        _changed()
        return {"restart_mode": APPLY, **_list_out(_child_id())}
