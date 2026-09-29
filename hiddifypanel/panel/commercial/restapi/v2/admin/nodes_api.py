"""Remote nodes of this panel for the Admin V2 "Nodes" page (super admin only)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from apiflask import abort
from flask import request
from flask.views import MethodView

import hiddifypanel
from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.models import Child, ChildMode, Role

# A node reports usage every few minutes; past these it is shown as late / offline.
_ONLINE_WINDOW = timedelta(minutes=15)
_LATE_WINDOW = timedelta(hours=24)


def _last_seen(child: Child) -> datetime | None:
    times = [t for t in (child.last_node_to_parent_time, child.last_parent_to_node_time) if t and t.year > 2000]
    return max(times) if times else None


def _status(last_seen: datetime | None) -> str:
    if not last_seen:
        return "never"
    age = datetime.now() - last_seen
    if age <= _ONLINE_WINDOW:
        return "online"
    return "late" if age <= _LATE_WINDOW else "offline"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value and value.year > 2000 else None


def _node_details(child: Child) -> dict:
    """The card's "more information" section."""
    from sqlalchemy import func

    from hiddifypanel.hutils.node.usage_report import last_usage_report
    from hiddifypanel.models import DailyUsage

    today = DailyUsage.query.with_entities(func.coalesce(func.sum(DailyUsage.usage), 0), func.coalesce(func.sum(DailyUsage.online), 0)).filter(DailyUsage.child_id == child.id, DailyUsage.date == date.today()).one()
    return {
        "last_usage_report": last_usage_report(child.id),
        "today_usage": int(today[0] or 0),
        "today_online": int(today[1] or 0),
        "last_from_node": _iso(child.last_node_to_parent_time),
        "last_to_node": _iso(child.last_parent_to_node_time),
    }


def _node_row(child: Child) -> dict:
    base = (child.node_base_url or "").strip()
    base = base if base.endswith("/") or not base else base + "/"
    last_seen = _last_seen(child)
    return {
        "id": child.id,
        "name": child.name or f"node-{child.id}",
        "host": base.split("://", 1)[-1].split("/", 1)[0] if base else "",
        # Same account on the node (admins are synced), so this signs the admin in there.
        "admin_url": f"{base}{g.account.uuid}/" if base else "",
        "last_seen": last_seen.isoformat() if last_seen else None,
        "status": _status(last_seen),
        "domains": sorted(d.domain for d in child.domains),
        "details": _node_details(child),
    }


def _remote_or_404(node_id: int) -> Child:
    child = Child.query.filter(Child.id == node_id, Child.mode == ChildMode.remote).first()
    return child or abort(404, "Node not found")


def _only_on_parent_or_standalone() -> None:
    if hutils.node.is_child():
        abort(400, "This panel is a node; manage nodes on its parent panel")


class NodesApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        """Nodes: List remote nodes"""
        _only_on_parent_or_standalone()
        nodes = Child.query.filter(Child.mode == ChildMode.remote).order_by(Child.id).all()
        return {"nodes": [_node_row(c) for c in nodes], "panel_version": hiddifypanel.__version__}

    def post(self):
        """Nodes: Register a node from its full admin link (`{"admin_link": ..., "name": ...}`)"""
        _only_on_parent_or_standalone()
        body = request.get_json(silent=True) or {}
        link = str(body.get("admin_link") or "").strip()
        if not link:
            abort(400, "admin_link is required")
        try:
            child = hutils.node.parent.register_node(link, str(body.get("name") or ""))
        except hutils.node.parent.NodeRegisterError as err:
            return {"code": err.code, "message": err.detail or err.code}, 400
        return {"node": _node_row(child) if child else None}


class NodeApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def patch(self, node_id: int):
        """Nodes: Rename a node (`{"name": ...}`), here and on the node"""
        _only_on_parent_or_standalone()
        child = _remote_or_404(node_id)
        name = str((request.get_json(silent=True) or {}).get("name") or "").strip()
        if not name or len(name) > 100:
            abort(400, "name must be 1-100 characters")
        synced = hutils.node.parent.rename_node(child, name)
        return {"node": _node_row(child), "synced_to_node": synced}

    def delete(self, node_id: int):
        """Nodes: Remove a node from this panel (the node itself is not changed)"""
        _only_on_parent_or_standalone()
        hutils.node.parent.remove_node(_remote_or_404(node_id))
        return {"status": 200, "msg": "ok"}


class NodePingApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self, node_id: int):
        """Nodes: Check live that a node answers, and its version"""
        child = _remote_or_404(node_id)
        base = (child.node_base_url or "").strip()
        if not base:
            return {"online": False, "version": "", "error": "no_url"}
        online, error = hutils.node.is_panel_active(base)
        info = hutils.node.get_panel_info_by_url(base) if online else None
        return {"online": online, "version": getattr(info, "version", "") or "", "error": "" if online else error}


class NodeSyncApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def post(self, node_id: int):
        """Nodes: Ask a node to sync (users, admins and its domains) now"""
        _only_on_parent_or_standalone()
        if not hutils.node.parent.request_child_to_sync(_remote_or_404(node_id)):
            abort(502, "The node did not answer the sync request")
        return {"status": 200, "msg": "ok"}
