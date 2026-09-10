from __future__ import annotations

from typing import Any

from flask import request
from flask.views import MethodView
from pydantic import Field

from hiddifypanel import current_app as app
from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.models import Role
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
        admin_id = request.args.get("admin_id") or g.account.id
        dto.usage_history = DailyUsage.get_daily_usage_stats(admin_id)
        return dto
