"""Config health (dashboard card): the last automatic test of every config, "Check now", and turning off the proxies
that fail in every app (and Restore)."""

from __future__ import annotations

from flask import current_app
from flask.views import MethodView

from hiddifypanel.auth import login_required
from hiddifypanel.models import Role
from hiddifypanel.proxy_v3 import config_health, config_tester_proxies


def _disabled() -> list[dict]:
    """What Restore turns back on: the proxies turned off here or by the config tester, still off."""
    return [p for p in config_tester_proxies.disabled() if p["off"]]


class ConfigHealthApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        """Config health: the last check, whether one is running, the proxies failing in both apps, what Restore brings back"""
        result = config_health.last()
        return {
            "last": result,
            "running": config_health.is_running(),
            "dead": config_health.dead_proxies(result),
            "dead_known": config_health.proxies_known(result),
            "disabled": _disabled(),
        }

    def post(self):
        """Config health: check every config now (in the background; read the result with GET)"""
        started = config_health.start_in_background(current_app._get_current_object())
        return {"started": started, "running": True}


class ConfigHealthDisableApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def post(self):
        """Config health: turn off the custom proxies whose every config failed in both Xray and Hiddify (last check)"""
        dead = config_health.dead_proxies()
        if dead:
            config_tester_proxies.disable([p["id"] for p in dead])
        return {"turned_off": dead, "dead": config_health.dead_proxies(), "disabled": _disabled(), "restart_mode": "apply_config" if dead else "nothing"}


class ConfigHealthRestoreApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def post(self):
        """Config health: turn back on every custom proxy turned off here (or by the config tester)"""
        restored = config_tester_proxies.restore()
        return {"restored": restored, "dead": config_health.dead_proxies(), "disabled": _disabled(), "restart_mode": "apply_config" if restored else "nothing"}
