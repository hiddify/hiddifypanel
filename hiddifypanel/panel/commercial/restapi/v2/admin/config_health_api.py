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
        """Config health: the last check, whether one is running, and the failed configs left out of the users' configs"""
        from hiddifypanel.models import ConfigEnum, hconfig

        hidden = config_health.hidden_configs()
        return {
            "last": config_health.last(),
            "running": config_health.is_running(),
            "hide_failed": bool(hconfig(ConfigEnum.config_health_hide_failed)),
            # app → names of the failed configs the users do not get (empty when the check can not be trusted)
            "hidden": {app: sorted(names) for app, names in hidden.items()},
        }

    def post(self):
        """Config health: check every config now (in the background; read the result with GET)"""
        started = config_health.start_in_background(current_app._get_current_object())
        return {"started": started, "running": True}
