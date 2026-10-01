from apiflask import APIBlueprint

from hiddifypanel import g
from hiddifypanel.models import AdminUser, User
from hiddifypanel.models.admin import AdminMode

bp = APIBlueprint("api_admin", __name__, url_prefix="/<proxy_path>/api/v2/admin/", enable_openapi=True)


def init_app(app):

    with app.app_context():
        from .admin_info_api import AdminInfoApi
        from .admin_log_api import AdminLogApi
        from .admin_user_api import AdminUserApi
        from .admin_users_api import AdminUsersApi
        from .dashboard_api import AdminDashboardApi, AdminDashboardDiskApi
        from .server_status_api import AdminServerStatusApi
        from .system_actions import AllConfigsApi, AllPublicPortsApi, DumpServerConfigsApi, ResetCacheApi, SyncTlsStoreApi, UpdateUserUsageApi

        bp.add_url_rule("/me/", view_func=AdminInfoApi)
        bp.add_url_rule("/server_status/", view_func=AdminServerStatusApi)
        bp.add_url_rule("/dashboard/", view_func=AdminDashboardApi)
        bp.add_url_rule("/dashboard/disk/", view_func=AdminDashboardDiskApi)
        bp.add_url_rule("/admin_user/<uuid:uuid>/", view_func=AdminUserApi)
        bp.add_url_rule("/admin_user/", view_func=AdminUsersApi)

        from .admins_api import AdminResetPasswordApi, AdminsTreeApi, AdminTreeItemApi, MyAdminAccountApi, MyAdminAliasApi, MyAdminOutboundApi, MyAdminConfigsApi, MyAdminPasswordApi

        bp.add_url_rule("/admins/", view_func=AdminsTreeApi)
        bp.add_url_rule("/admins/me/", view_func=MyAdminAccountApi)
        bp.add_url_rule("/admins/me/password/", view_func=MyAdminPasswordApi)
        bp.add_url_rule("/admins/me/additional-configs/", view_func=MyAdminConfigsApi)
        bp.add_url_rule("/admins/me/alias/", view_func=MyAdminAliasApi)
        bp.add_url_rule("/admins/me/default-outbound/", view_func=MyAdminOutboundApi)
        bp.add_url_rule("/admins/<uuid:uuid>/", view_func=AdminTreeItemApi)
        bp.add_url_rule("/admins/<uuid:uuid>/reset-password/", view_func=AdminResetPasswordApi)

        bp.add_url_rule("/log/", view_func=AdminLogApi)
        bp.add_url_rule("/update_user_usage/", view_func=UpdateUserUsageApi)
        bp.add_url_rule("/all-configs/", view_func=AllConfigsApi)
        bp.add_url_rule("/dump-server-configs/", view_func=DumpServerConfigsApi)
        bp.add_url_rule("/sync-tls-store/", view_func=SyncTlsStoreApi)
        bp.add_url_rule("/reset-cache/", view_func=ResetCacheApi)

        from .protocols_api import ProtocolSwitchesApi

        bp.add_url_rule("/protocols/", view_func=ProtocolSwitchesApi)

        from hiddifypanel.proxy_v3.outbounds import subscribe_events as subscribe_outbound_events

        from .outbounds_api import OutboundApi, OutboundDefaultApi, OutboundOrderApi, OutboundResetApi, OutboundsApi

        bp.add_url_rule("/outbounds/", view_func=OutboundsApi)
        bp.add_url_rule("/outbounds/order/", view_func=OutboundOrderApi)
        bp.add_url_rule("/outbounds/<int:outbound_id>/", view_func=OutboundApi)
        bp.add_url_rule("/outbounds/<int:outbound_id>/default/", view_func=OutboundDefaultApi)
        bp.add_url_rule("/outbounds/<int:outbound_id>/reset/", view_func=OutboundResetApi)
        # Settings → WARP mode "all"/"custom" keeps the default outbound in step.
        subscribe_outbound_events()

        from .settings_api import SettingsApi

        bp.add_url_rule("/settings/", view_func=SettingsApi)

        from .quick_setup_api import QuickSetupApi, QuickSetupDetectApi, QuickSetupDomainsApi, QuickSetupFinishApi, QuickSetupLanguageApi, QuickSetupPasswordApi

        bp.add_url_rule("/quick-setup/", view_func=QuickSetupApi)
        bp.add_url_rule("/quick-setup/language/", view_func=QuickSetupLanguageApi)
        bp.add_url_rule("/quick-setup/password/", view_func=QuickSetupPasswordApi)
        bp.add_url_rule("/quick-setup/detect/", view_func=QuickSetupDetectApi)
        bp.add_url_rule("/quick-setup/domains/", view_func=QuickSetupDomainsApi)
        bp.add_url_rule("/quick-setup/finish/", view_func=QuickSetupFinishApi)

        from .nodes_api import NodeApi, NodePingApi, NodesApi, NodeSyncApi

        bp.add_url_rule("/nodes/", view_func=NodesApi)
        bp.add_url_rule("/nodes/<int:node_id>/", view_func=NodeApi)
        bp.add_url_rule("/nodes/<int:node_id>/ping/", view_func=NodePingApi)
        bp.add_url_rule("/nodes/<int:node_id>/sync/", view_func=NodeSyncApi)

        bp.add_url_rule("/all-public-port/", view_func=AllPublicPortsApi)

        from .user_api import UserApi
        from .users_api import UsersApi

        bp.add_url_rule("/user/<uuid:uuid>/", view_func=UserApi)

        bp.add_url_rule("/user/", view_func=UsersApi)

        from .users_page_api import UserPageApi, UsersBulkApi, UsersPageApi

        bp.add_url_rule("/users/", view_func=UsersPageApi)
        bp.add_url_rule("/users/bulk/", view_func=UsersBulkApi)
        bp.add_url_rule("/users/<uuid:uuid>/", view_func=UserPageApi)

        from hiddifypanel.proxy_v3.api.custom_proxy_api import (
            CustomProxiesApi,
            CustomProxyApi,
            CustomProxyDuplicateApi,
            CustomProxyEnableApi,
            CustomProxyExportApi,
            CustomProxyGenerateBundleApi,
            CustomProxyGenerateExampleApi,
            CustomProxyGenerateExampleByIdApi,
            CustomProxyImportApi,
            CustomProxyMetaApi,
            CustomProxyPreviewApi,
            CustomProxyValidateApi,
            CustomProxyValidateByIdApi,
        )
        from hiddifypanel.proxy_v3.api.proxy_base_config_api import (
            ProxyBaseConfigApi,
            ProxyBaseConfigDuplicateApi,
            ProxyBaseConfigExportApi,
            ProxyBaseConfigImportApi,
            ProxyBaseConfigMetaApi,
            ProxyBaseConfigPreviewApi,
            ProxyBaseConfigsApi,
            ProxyBaseConfigValidateApi,
        )
        from hiddifypanel.proxy_v3.api.proxy_template_api import ProxyTemplateApi, ProxyTemplateDuplicateApi, ProxyTemplatesApi
        from hiddifypanel.proxy_v3.api.template_variables_api import TemplateVariablesApi

        from .domain_api import DomainsOptionsApi, DomainsQuickAddApi

        bp.add_url_rule("/custom-proxies/", view_func=CustomProxiesApi)
        bp.add_url_rule("/custom-proxies/meta/", view_func=CustomProxyMetaApi)
        bp.add_url_rule("/custom-proxies/validate/", view_func=CustomProxyValidateApi)
        bp.add_url_rule("/custom-proxies/preview/", view_func=CustomProxyPreviewApi)
        bp.add_url_rule("/custom-proxies/generate-example/", view_func=CustomProxyGenerateExampleApi)
        bp.add_url_rule("/custom-proxies/generate-bundle/", view_func=CustomProxyGenerateBundleApi)
        bp.add_url_rule("/custom-proxies/export/", view_func=CustomProxyExportApi)
        bp.add_url_rule("/custom-proxies/import/", view_func=CustomProxyImportApi)
        bp.add_url_rule("/custom-proxies/<int:proxy_id>/", view_func=CustomProxyApi)
        bp.add_url_rule("/custom-proxies/<int:proxy_id>/enable/", view_func=CustomProxyEnableApi)
        bp.add_url_rule("/custom-proxies/<int:proxy_id>/duplicate/", view_func=CustomProxyDuplicateApi)
        bp.add_url_rule("/custom-proxies/<int:proxy_id>/validate/", view_func=CustomProxyValidateByIdApi)
        bp.add_url_rule("/custom-proxies/<int:proxy_id>/generate-example/", view_func=CustomProxyGenerateExampleByIdApi)
        bp.add_url_rule("/proxy-templates/", view_func=ProxyTemplatesApi)
        bp.add_url_rule("/proxy-templates/<int:template_id>/", view_func=ProxyTemplateApi)
        bp.add_url_rule("/proxy-templates/<int:template_id>/duplicate/", view_func=ProxyTemplateDuplicateApi)
        bp.add_url_rule("/proxy-base-configs/meta/", view_func=ProxyBaseConfigMetaApi)
        bp.add_url_rule("/proxy-base-configs/validate/", view_func=ProxyBaseConfigValidateApi)
        bp.add_url_rule("/proxy-base-configs/preview/", view_func=ProxyBaseConfigPreviewApi)
        bp.add_url_rule("/proxy-base-configs/export/", view_func=ProxyBaseConfigExportApi)
        bp.add_url_rule("/proxy-base-configs/import/", view_func=ProxyBaseConfigImportApi)
        bp.add_url_rule("/proxy-base-configs/", view_func=ProxyBaseConfigsApi)
        bp.add_url_rule("/proxy-base-configs/<int:config_id>/", view_func=ProxyBaseConfigApi)
        bp.add_url_rule("/proxy-base-configs/<int:config_id>/duplicate/", view_func=ProxyBaseConfigDuplicateApi)
        bp.add_url_rule("/template-variables/", view_func=TemplateVariablesApi)
        bp.add_url_rule("/domains/options/", view_func=DomainsOptionsApi)
        bp.add_url_rule("/domains/", view_func=DomainsQuickAddApi)

        from .apply_api import ApplyActionApi, ApplyApi, ApplyLogApi, ApplyLogDownloadApi

        bp.add_url_rule("/apply/", view_func=ApplyApi)
        bp.add_url_rule("/apply/log/", view_func=ApplyLogApi)
        bp.add_url_rule("/apply/logs/<string:name>/download/", view_func=ApplyLogDownloadApi)
        bp.add_url_rule("/apply/<string:action>/", view_func=ApplyActionApi, methods=["POST"])

        from .backup_api import BackupApi, BackupDownloadApi, BackupFileApi, BackupFilesApi, BackupRestoreApi

        bp.add_url_rule("/backup/", view_func=BackupApi)
        bp.add_url_rule("/backup/download/", view_func=BackupDownloadApi)
        bp.add_url_rule("/backup/files/", view_func=BackupFilesApi)
        bp.add_url_rule("/backup/files/<string:name>/", view_func=BackupFileApi)
        bp.add_url_rule("/backup/restore/", view_func=BackupRestoreApi)

        from .domains_page_api import DomainsPageApi, DomainsPageCertificateApi, DomainsPageDetectApi, DomainsPageIpsApi, DomainsPageItemApi, DomainsPageOrderApi, DomainsPagePortCheckApi

        bp.add_url_rule("/domains-page/", view_func=DomainsPageApi)
        bp.add_url_rule("/domains-page/order/", view_func=DomainsPageOrderApi)
        bp.add_url_rule("/domains-page/detect/", view_func=DomainsPageDetectApi)
        bp.add_url_rule("/domains-page/port-check/", view_func=DomainsPagePortCheckApi)
        bp.add_url_rule("/domains-page/<int:domain_id>/", view_func=DomainsPageItemApi)
        bp.add_url_rule("/domains-page/<int:domain_id>/ips/", view_func=DomainsPageIpsApi)
        bp.add_url_rule("/domains-page/<int:domain_id>/certificate/", view_func=DomainsPageCertificateApi)

        from .server_ip_api import (
            DomainHealthCheckApi,
            ServerIpApi,
            ServerIpHealthCheckApi,
            ServerIpsApi,
        )

        bp.add_url_rule("/server-ips/", view_func=ServerIpsApi)
        bp.add_url_rule("/server-ips/<int:ip_id>/", view_func=ServerIpApi)
        bp.add_url_rule("/server-ips/<int:ip_id>/health-check/", view_func=ServerIpHealthCheckApi)
        bp.add_url_rule("/domains/<int:domain_id>/health-check/", view_func=DomainHealthCheckApi)

    app.register_blueprint(bp)


def has_permission(model) -> bool:
    """Check if the authenticated account has permission to do an action(get,insert,update,delete) on the another admin"""
    if g.account.uuid == AdminUser.get_super_admin_uuid():
        return True
    if isinstance(model, AdminUser) and model.id == g.account.id:
        return True
    if isinstance(model, AdminUser) and model.parent_admin_id == g.account.id:
        return True
    elif isinstance(model, User) and model.added_by == g.account.id:
        return True

    return False


_ADMIN_MODE_RANK = {
    AdminMode.agent: 1,
    AdminMode.admin: 2,
    AdminMode.super_admin: 3,
}


def _as_admin_mode(value) -> AdminMode:
    if isinstance(value, AdminMode):
        return value
    return AdminMode(str(value))


def assert_actor_can_create_admin() -> None:
    """POST /admin_user/ — only super_admin or admin with can_add_admin."""
    from apiflask import abort

    actor = g.account
    if actor is None or not hasattr(actor, "mode"):
        abort(403, "Admin account required")
    if actor.mode == AdminMode.super_admin:
        return
    if actor.mode == AdminMode.admin and actor.can_add_admin:
        return
    abort(403, "You don't have permission to create admins")


def validate_admin_write_payload(payload: dict, *, target: AdminUser | None = None) -> dict:
    """Reject privilege escalation on admin create/update payloads.

    - Assigned ``mode`` must not exceed the caller's mode.
    - Only ``super_admin`` may assign ``super_admin`` or grant ``can_add_admin``.
    - Callers cannot raise their own ``mode`` / ``can_add_admin``.
    - Non-super callers are parented under themselves.
    """
    from apiflask import abort

    actor = g.account
    if actor is None or not hasattr(actor, "mode"):
        abort(403, "Admin account required")

    actor_mode = _as_admin_mode(actor.mode)
    actor_rank = _ADMIN_MODE_RANK[actor_mode]
    out = dict(payload)

    if target is not None and getattr(target, "id", None) == getattr(actor, "id", None):
        if "mode" in out and out["mode"] is not None and _as_admin_mode(out["mode"]) != _as_admin_mode(target.mode):
            abort(403, "Cannot change your own mode")
        if "can_add_admin" in out and out["can_add_admin"] is not None and bool(out["can_add_admin"]) != bool(target.can_add_admin):
            abort(403, "Cannot change your own can_add_admin")
        out.pop("parent_admin_uuid", None)

    if "mode" in out and out["mode"] is not None:
        requested = _as_admin_mode(out["mode"])
        if _ADMIN_MODE_RANK[requested] > actor_rank:
            abort(403, "Cannot assign a mode higher than your own")
        if requested == AdminMode.super_admin and actor_mode != AdminMode.super_admin:
            abort(403, "Only super_admin can assign super_admin")
        out["mode"] = requested

    if "can_add_admin" in out and out["can_add_admin"] is not None:
        want = bool(out["can_add_admin"])
        if actor_mode != AdminMode.super_admin:
            if target is None:
                out["can_add_admin"] = False
            elif want and not bool(target.can_add_admin):
                abort(403, "Only super_admin can grant can_add_admin")
            else:
                out["can_add_admin"] = want

    if actor_mode != AdminMode.super_admin:
        out["parent_admin_uuid"] = actor.uuid

    return out


def resolve_added_by_uuid(requested_uuid: str | None) -> str:
    """Restrict added_by_uuid to the caller (or a sub-admin). Never invent admins."""
    from apiflask import abort

    actor = g.account
    if actor is None:
        abort(403, "Admin account required")
    if not requested_uuid:
        return actor.uuid
    target = AdminUser.by_uuid(requested_uuid, create=False)
    if not target:
        abort(400, "Invalid added_by_uuid")
    if getattr(actor, "mode", None) == AdminMode.super_admin:
        return requested_uuid
    allowed = set(actor.recursive_sub_admins_ids())
    if target.id not in allowed:
        abort(403, "Cannot assign added_by_uuid outside your admins")
    return requested_uuid
