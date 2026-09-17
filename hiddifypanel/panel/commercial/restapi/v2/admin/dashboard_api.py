from __future__ import annotations

import datetime

from flask import request
from flask.views import MethodView

from hiddifypanel import current_app as app
from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.models import Role
from hiddifypanel.models.usage import DailyUsage
from hiddifypanel.panel.commercial.restapi.v2.admin.dashboard_schema import DEFAULT_RANGE_DAYS, DashboardOutputSchema

ALLOWED_RANGE_DAYS = (7, 14, 30, 90, 180, 365)
DEFAULT_PROCESS_LIMIT = 16
MAX_PROCESS_LIMIT = 32


def _range_days() -> int:
    try:
        days = int(request.args.get("days", DEFAULT_RANGE_DAYS))
    except (TypeError, ValueError):
        return DEFAULT_RANGE_DAYS
    return days if days in ALLOWED_RANGE_DAYS else DEFAULT_RANGE_DAYS


def _process_limit() -> int:
    try:
        limit = int(request.args.get("processes", DEFAULT_PROCESS_LIMIT))
    except (TypeError, ValueError):
        return DEFAULT_PROCESS_LIMIT
    return max(1, min(limit, MAX_PROCESS_LIMIT))


def _int_arg(name: str) -> int | None:
    value = request.args.get(name)
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


class AdminDashboardApi(MethodView):
    """Everything the Admin V2 dashboard renders, in a single snapshot.

    `?include=system` returns only live server metrics (this host and/or child
    nodes). Usage aggregation always comes from the parent DB and is cached
    day-by-day so polls do not re-sum the whole history.
    """

    decorators = [login_required({Role.super_admin, Role.admin, Role.agent})]

    @app.output(DashboardOutputSchema)
    def get(self) -> DashboardOutputSchema:
        """System: Dashboard"""
        from hiddifypanel.hutils import node_system

        range_days = _range_days()
        system_only = request.args.get("include") == "system"
        child_id = _int_arg("child_id")

        live = node_system.collect_system_stats(child_id, process_limit=_process_limit())

        dto = DashboardOutputSchema(
            generated_at=datetime.datetime.now(datetime.UTC).isoformat(),
            range_days=range_days,
            child_id=child_id,
            processes=live.processes,
            system=live.system,
            node_stats=live.node_stats,
        )

        if system_only:
            return dto

        admin_id = _int_arg("admin_id") or g.account.id
        if admin_id not in g.account.recursive_sub_admins_ids():
            admin_id = g.account.id

        stats = DailyUsage.get_dashboard_stats(admin_id=admin_id, child_id=child_id, series_days=range_days)
        dto.series = stats.series
        dto.usage = stats.usage
        dto.users = stats.users
        dto.nodes = stats.nodes
        return dto
