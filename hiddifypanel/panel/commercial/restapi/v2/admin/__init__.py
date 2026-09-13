from apiflask import APIBlueprint

from hiddifypanel import g
from hiddifypanel.models import AdminUser, User

bp = APIBlueprint("api_admin", __name__, url_prefix="/<proxy_path>/api/v2/admin/", enable_openapi=True)


def init_app(app):

    with app.app_context():
        from .admin_info_api import AdminInfoApi
        from .admin_log_api import AdminLogApi
        from .admin_user_api import AdminUserApi
        from .admin_users_api import AdminUsersApi
        from .server_status_api import AdminServerStatusApi
        from .system_actions import AllConfigsApi, AllPublicPortsApi, UpdateUserUsageApi

        bp.add_url_rule("/me/", view_func=AdminInfoApi)
        bp.add_url_rule("/server_status/", view_func=AdminServerStatusApi)
        bp.add_url_rule("/admin_user/<uuid:uuid>/", view_func=AdminUserApi)
        bp.add_url_rule("/admin_user/", view_func=AdminUsersApi)

        bp.add_url_rule("/log/", view_func=AdminLogApi)
        bp.add_url_rule("/update_user_usage/", view_func=UpdateUserUsageApi)
        bp.add_url_rule("/all-configs/", view_func=AllConfigsApi)

        bp.add_url_rule("/all-public-port/", view_func=AllPublicPortsApi)

        from .user_api import UserApi
        from .users_api import UsersApi

        bp.add_url_rule("/user/<uuid:uuid>/", view_func=UserApi)

        bp.add_url_rule("/user/", view_func=UsersApi)

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
    if isinstance(model, AdminUser) and model.parent_admin_id == g.account.id:
        return True
    elif isinstance(model, User) and model.added_by == g.account.id:
        return True

    return False
