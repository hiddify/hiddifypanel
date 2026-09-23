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


class SyncTlsStoreApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        """System: Import TLS certificates from data/ssl/ into tls_store (all, or one ?domain= / ?domain_id=)"""
        from hiddifypanel.proxy_v3.tls_store_sync import (
            sync_tls_store_all,
            sync_tls_store_for_domain,
            sync_tls_store_for_domain_id,
        )

        domain = request.args.get("domain") or None
        domain_id = request.args.get("domain_id", type=int)
        child_id = request.args.get("child_id", default=0, type=int)

        if domain_id is not None or domain:
            row = sync_tls_store_for_domain_id(domain_id) if domain_id is not None else sync_tls_store_for_domain(domain, child_id=child_id)
            if not row:
                payload = {"ok": False, "synced": 0, "message": f"no certificate files found for {domain_id if domain_id is not None else domain}"}
                return json.dumps(payload, indent=2)
            payload = {
                "ok": True,
                "synced": 1,
                "domain_id": row.domain_id,
                "domain": row.domain.domain if row.domain else domain,
                "issuer": row.issuer,
                "self_signed": bool(row.self_signed),
            }
            return json.dumps(payload, indent=2)

        count = sync_tls_store_all(child_id)
        return json.dumps({"ok": True, "synced": count}, indent=2)


class AllPublicPortsApi(MethodView):
    decorators = [login_required({Role.super_admin, Role.admin})]

    def get(self):
        """Public Ports"""
        return json.dumps(hutils.network.all_public_ports(), indent=2)
