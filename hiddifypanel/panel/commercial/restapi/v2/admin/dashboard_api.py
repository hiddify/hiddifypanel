from __future__ import annotations

import datetime
from typing import Any

from flask import request
from flask.views import MethodView
from pydantic import Field

import hiddifypanel
from hiddifypanel import current_app as app
from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.models import Role
from hiddifypanel.models.usage import DailyUsage
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel

DEFAULT_RANGE_DAYS = 30
ALLOWED_RANGE_DAYS = (7, 14, 30, 90, 180, 365)
DEFAULT_PROCESS_LIMIT = 8
MAX_PROCESS_LIMIT = 25


class DashboardOutputSchema(ApiModel):
    generated_at: str = Field(default="", description="ISO timestamp of this snapshot")
    range_days: int = Field(default=DEFAULT_RANGE_DAYS, description="Number of days in the usage series")
    series: list[dict[str, Any]] = Field(default_factory=list, description="Daily usage/online history (oldest first)")
    usage: dict[str, Any] = Field(default_factory=dict, description="Usage totals, averages, previous periods and trends")
    users: dict[str, Any] = Field(default_factory=dict, description="User counts and online buckets")
    system: dict[str, Any] = Field(default_factory=dict, description="CPU, memory, disk, network and host metrics")
    processes: dict[str, Any] = Field(default_factory=dict, description="Top processes by CPU and memory")


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

    `?include=system` returns only the live server metrics, so the dashboard can
    poll them every few seconds without re-running the usage aggregation.
    """

    decorators = [login_required({Role.super_admin, Role.admin, Role.agent})]

    @app.output(DashboardOutputSchema)
    def get(self):
        """System: Dashboard"""
        range_days = _range_days()
        system_only = request.args.get("include") == "system"

        metrics = hutils.system_metrics.snapshot(process_limit=_process_limit())
        host = {**metrics.pop("host"), "panel_version": hiddifypanel.__version__}

        dto = DashboardOutputSchema()
        dto.generated_at = datetime.datetime.now(datetime.UTC).isoformat()
        dto.range_days = range_days
        dto.processes = metrics.pop("processes")
        dto.system = {**metrics, "host": host}

        if system_only:
            return dto

        admin_id = _int_arg("admin_id") or g.account.id
        if admin_id not in g.account.recursive_sub_admins_ids():
            admin_id = g.account.id

        stats = DailyUsage.get_dashboard_stats(admin_id=admin_id, child_id=_int_arg("child_id"), series_days=range_days)
        dto.series = stats["series"]
        dto.usage = stats["usage"]
        dto.users = stats["users"]
        return dto
