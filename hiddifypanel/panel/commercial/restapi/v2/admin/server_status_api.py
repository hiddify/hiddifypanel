from __future__ import annotations

from typing import Any

from apiflask import abort
from flask import request
from flask.views import MethodView
from pydantic import Field

from hiddifypanel import current_app as app
from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.models import AdminUser, Role
from hiddifypanel.models.usage import DailyUsage
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel


class ServerStatusOutputSchema(ApiModel):
    stats: dict[str, Any] = Field(default_factory=dict, description="System stats")
    usage_history: dict[str, Any] = Field(default_factory=dict, description="System usage history")


class AdminServerStatusApi(MethodView):
    decorators = [login_required({Role.super_admin, Role.admin, Role.agent})]

    @app.output(ServerStatusOutputSchema)
    def get(self):
        """System: ServerStatus"""
        dto = ServerStatusOutputSchema()
        dto.stats = {"system": hutils.system.system_stats(), "top5": hutils.system.top_processes()}

        raw_admin_id = request.args.get("admin_id")
        if raw_admin_id in (None, ""):
            admin_id = g.account.id
        else:
            try:
                admin_id = int(raw_admin_id)
            except (TypeError, ValueError):
                abort(400, "Invalid admin_id")
            allowed = set(g.account.recursive_sub_admins_ids())
            if admin_id not in allowed:
                abort(403, "You don't have permission to view this admin's stats")
            if not AdminUser.by_id(admin_id):
                abort(404, "Admin not found")

        dto.usage_history = DailyUsage.get_daily_usage_stats(admin_id)
        return dto
