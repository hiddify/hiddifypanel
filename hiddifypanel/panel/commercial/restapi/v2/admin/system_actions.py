import json

from flask import request
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


class DumpServerConfigsApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        """System: Dump Server Configs (xray/hiddify-core/haproxy/nginx/dns_proxy) to generated/"""
        from hiddifypanel.proxy_v3.config_builder.dump import dump_all_server_configs
        from hiddifypanel.proxy_v3.jinja_context import HIDDIFY_MANAGER_ROOT

        no_invalidate_cache = request.args.get("no_invalidate_cache") in ("1", "true", "True")
        result = dump_all_server_configs(
            f"{HIDDIFY_MANAGER_ROOT}/generated",
            invalidate_cache=not no_invalidate_cache,
        )
        payload = {"ok": result.ok, "written": result.written, "messages": result.messages}
        return json.dumps(payload, indent=2), (200 if result.ok else 500)


class AllPublicPortsApi(MethodView):
    decorators = [login_required({Role.super_admin, Role.admin})]

    def get(self):
        """Public Ports"""
        return json.dumps(hutils.network.all_public_ports(), indent=2)
