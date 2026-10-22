"""Config health (dashboard card): the last automatic test of every config, and "Check now"."""

from __future__ import annotations

from flask import current_app
from flask.views import MethodView

from hiddifypanel.auth import login_required
from hiddifypanel.models import Role
from hiddifypanel.proxy_v3 import config_health


class ConfigHealthApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        """Config health: the last check, and whether one is running"""
        return {"last": config_health.last(), "running": config_health.is_running()}

    def post(self):
        """Config health: check every config now (in the background; read the result with GET)"""
        started = config_health.start_in_background(current_app._get_current_object())
        return {"started": started, "running": True}
