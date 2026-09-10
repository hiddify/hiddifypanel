import json

from flask.views import MethodView

from hiddifypanel import hutils
from hiddifypanel.auth import login_required
from hiddifypanel.models import Role
from hiddifypanel.panel import hiddify, usage


class UpdateUserUsageApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        """System: Update User Usage"""
        # time.sleep(5)

        return json.dumps(usage.update_local_usage_not_lock(), indent=2)


class AllConfigsApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        """System: All Configs for configuration"""
        return json.dumps(hiddify.all_configs_for_cli(), indent=2)


class AllPublicPortsApi(MethodView):
    decorators = [login_required({Role.admin})]

    def get(self):
        """Public Ports"""
        return json.dumps(hutils.network.all_public_ports(), indent=2)
