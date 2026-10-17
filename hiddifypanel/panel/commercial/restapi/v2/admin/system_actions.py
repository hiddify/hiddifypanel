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
        """System: Dump Server Configs (xray/hiddify-core/haproxy/dns_proxy) to generated/"""
        from hiddifypanel.proxy_v3.config_builder.dump import dump_all_server_configs
        from hiddifypanel.proxy_v3.jinja_context import HIDDIFY_MANAGER_ROOT

        # Caches are cleared when settings / domains / proxies change; ?invalidate_cache=1 forces it (no_invalidate_cache
        # is still accepted and is the default now).
        invalidate_cache = request.args.get("invalidate_cache") in ("1", "true", "True")
        raw_cores = request.args.get("cores") or ""
        cores = [core.strip() for core in raw_cores.split(",") if core.strip()] or None
        try:
            result = dump_all_server_configs(
                f"{HIDDIFY_MANAGER_ROOT}/generated",
                invalidate_cache=invalidate_cache,
                cores=cores,
            )
        except ValueError as exc:
            return json.dumps({"ok": False, "message": str(exc)}), 400
        payload = {"ok": result.ok, "written": result.written, "messages": result.messages}
        return json.dumps(payload, indent=2), (200 if result.ok else 500)


class ResetCacheApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def post(self):
        """System: Reset panel cache (redis cached functions and jinja template caches)"""
        from hiddifypanel.cache import cache
        from hiddifypanel.proxy_v3.config_builder.jinja_render import clear_jinja_template_caches

        ok = cache.invalidate_all_cached_functions()
        clear_jinja_template_caches()
        return json.dumps({"ok": bool(ok)}, indent=2), (200 if ok else 500)


class AllPublicPortsApi(MethodView):
    decorators = [login_required({Role.super_admin, Role.admin})]

    def get(self):
        """Public Ports"""
        data = hutils.network.all_public_ports()
        # Lets the UI open the custom proxy behind a port; not part of all_public_ports() (the firewall reads that).
        data["proxies"] = hutils.network.public_port_proxy_ids()
        return json.dumps(data, indent=2)
