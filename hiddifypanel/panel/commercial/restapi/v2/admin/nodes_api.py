"""Remote nodes of this panel for the Admin V2 "Nodes" page (super admin only)."""

from __future__ import annotations

import ipaddress
from datetime import date, datetime, timedelta

from apiflask import abort
from flask import jsonify, request
from flask.views import MethodView

import hiddifypanel
from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.hutils.node import async_job, ws_server
from hiddifypanel.hutils.node.sync_report import NodeSyncReport
from hiddifypanel.models import Child, ChildMode, Role
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel

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


def _host_ip(host: str) -> str:
    """The address of a node's host ("203.0.113.10", "[2001:db8::1]:443", a name): itself, or what its name resolves to."""
    if host.startswith("["):  # "[IPv6]" or "[IPv6]:port"
        name = host[1:].split("]", 1)[0]
    elif host.count(":") == 1:  # "name:port" (a bare IPv6 has more colons)
        name = host.split(":", 1)[0]
    else:
        name = host
    try:
        return str(ipaddress.ip_address(name))
    except ValueError:
        pass
    ip = hutils.network.get_domain_ip(name, version=4) or hutils.network.get_domain_ip(name)
    return str(ip) if ip else ""


def node_country(host: str) -> str:
    """The node's country (ISO code, e.g. "DE") from its address, by the panel's own MaxMind data; "" when unknown.
    Kept a day: the server does not move, and the Nodes page lists every node each minute."""
    from hiddifypanel.cache import redis_client
    from hiddifypanel.hutils.network import maxmind

    if not host:
        return ""
    key = f"nodes:country:{host}"
    cached = redis_client.get(key)
    if cached is not None:
        return cached.decode() if isinstance(cached, bytes) else str(cached)
    try:
        ip = _host_ip(host)
        code = maxmind.get_ip_info(ip).country if ip else ""
    except Exception:
        code = ""
    code = code if len(code) == 2 and code.isalpha() else ""
    redis_client.set(key, code, ex=86400 if code else 3600)
    return code


def _node_row(child: Child) -> dict:
    base = (child.node_base_url or "").strip()
    base = base if base.endswith("/") or not base else base + "/"
    last_seen = _last_seen(child)
    return {
        "id": child.id,
        "name": child.name or f"node-{child.id}",
        "host": base.split("://", 1)[-1].split("/", 1)[0] if base else "",
        "country": node_country(base.split("://", 1)[-1].split("/", 1)[0]) if base else "",
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
        name = str(body.get("name") or "")
        if not link:
            abort(400, "admin_link is required")
        if async_job.wants_job():  # it can take minutes: answer now, the page asks for the result (nothing cuts a short request)
            return jsonify({"job": async_job.start(lambda: _register_result(link, name))}), 202
        result = _register_result(link, name)
        if result["ok"]:
            return {"node": result["node"]}
        return result["error"], 400


def _register_result(link: str, name: str) -> dict[str, object]:
    """``{"ok": True, "node": ...}`` or ``{"ok": False, "error": {code, message, side, reg}}``: both are answers, not exceptions."""
    try:
        child = hutils.node.parent.register_node(link, name)
    except hutils.node.parent.NodeRegisterError as err:
        return {"ok": False, "error": {"code": err.code, "message": err.detail or err.code, "side": err.side, "reg": err.reg}}
    return {"ok": True, "node": _node_row(child) if child else None}


class NodeJobApi(MethodView):
    """The result of a registration started with ``X-Async-Job``: `{"state": "running" | "done" | "failed", "result": {ok, node | error}}`."""

    decorators = [login_required({Role.super_admin})]

    def get(self, job_id: str):
        _only_on_parent_or_standalone()
        state = async_job.read(job_id)
        if state is None:
            abort(404, "This registration is gone (results are kept for 15 minutes)")
        return jsonify(state)


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
        unlinked = hutils.node.parent.remove_node(_remote_or_404(node_id))
        # unlinked=False: the node was offline or too old; it still has this panel as parent.
        return {"status": 200, "msg": "ok", "node_unlinked": unlinked}


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


def _ping_target(child: Child) -> tuple[str, int]:
    """The node's address and port from its link (a name is resolved, IPv4 first)."""
    import ipaddress
    from urllib.parse import urlparse

    url = urlparse((child.node_base_url or "").strip())
    host, port = url.hostname or "", url.port or (80 if url.scheme == "http" else 443)
    try:
        return str(ipaddress.ip_address(host)), port
    except ValueError:
        ip = hutils.network.get_domain_ip(host, version=4) or hutils.network.get_domain_ip(host) if host else None
        return (str(ip) if ip else ""), port


def ping_once(ip: str, port: int) -> dict:
    """One ICMP echo from this server (round trip in ms); when ICMP is not allowed here or is blocked on the way,
    the time a TCP connection to the node's panel port takes instead (``method`` says which)."""
    import re
    import socket
    import subprocess
    import time

    try:
        res = subprocess.run(["ping", "-c", "1", "-W", "2", "-n", ip], capture_output=True, text=True, timeout=4)
        found = re.search(r"time[=<]([\d.]+)\s*ms", res.stdout)
        if res.returncode == 0 and found:
            return {"ok": True, "ms": round(float(found.group(1)), 1), "method": "icmp", "error": ""}
    except (OSError, subprocess.SubprocessError):
        pass
    start = time.perf_counter()
    try:
        with socket.create_connection((ip, port), timeout=3):
            return {"ok": True, "ms": round((time.perf_counter() - start) * 1000, 1), "method": "tcp", "error": ""}
    except OSError as e:
        return {"ok": False, "ms": None, "method": "tcp", "error": e.strerror or type(e).__name__}


class NodeIcmpPingApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self, node_id: int):
        """Nodes: Ping the node's server once from this panel (the page asks again every second)"""
        ip, port = _ping_target(_remote_or_404(node_id))
        if not ip:
            return {"ip": "", "ok": False, "ms": None, "method": "", "error": "no_address"}
        return {"ip": ip, **ping_once(ip, port)}


class NodeSyncApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def post(self, node_id: int):
        """Nodes: Ask a node to sync (users, admins and its domains) now"""
        _only_on_parent_or_standalone()
        if not hutils.node.parent.request_child_to_sync(_remote_or_404(node_id)):
            abort(502, "The node did not answer the sync request")
        return {"status": 200, "msg": "ok"}


class NodeSyncStatusOut(ApiModel):
    #: None when the node could not be asked (offline, too old for this call)
    report: NodeSyncReport | None = None
    error: str = ""
    #: the parent's side of the link
    websocket_connected: bool
    last_seen: str | None = None


class NodeSyncReportApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @hiddifypanel.current_app.output(NodeSyncStatusOut)
    def get(self, node_id: int) -> NodeSyncStatusOut:
        """Nodes: Ask a node how its sync with this panel is going (read only)"""
        _only_on_parent_or_standalone()
        child = _remote_or_404(node_id)
        last_seen = _last_seen(child)
        report = hutils.node.parent.node_sync_report(child)
        return NodeSyncStatusOut(
            report=report if isinstance(report, NodeSyncReport) else None,
            error=report if isinstance(report, str) else "",
            websocket_connected=ws_server.is_connected(child.unique_id),
            last_seen=last_seen.isoformat() if last_seen else None,
        )
