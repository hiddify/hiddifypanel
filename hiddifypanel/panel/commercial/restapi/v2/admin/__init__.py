from apiflask import APIBlueprint
from flask import g
from hiddifypanel.models import AdminUser, User

bp = APIBlueprint("api_admin", __name__, url_prefix="/<proxy_path>/api/v2/admin/", enable_openapi=True)


def init_app(app):
    
    with app.app_context():
        from .admin_info_api import AdminInfoApi
        from .server_status_api import AdminServerStatusApi
        from .admin_user_api import AdminUserApi
        from .admin_users_api import AdminUsersApi
        from .admin_log_api import AdminLogApi
        from .system_actions import AllPublicPortsApi
        from .system_actions import UpdateUserUsageApi, AllConfigsApi
        bp.add_url_rule('/me/', view_func=AdminInfoApi)  # type: ignore
        bp.add_url_rule('/server_status/', view_func=AdminServerStatusApi)  # type: ignore
        bp.add_url_rule('/admin_user/<uuid:uuid>/', view_func=AdminUserApi)  # type: ignore
        bp.add_url_rule('/admin_user/', view_func=AdminUsersApi)  # type: ignore
        
        bp.add_url_rule('/log/', view_func=AdminLogApi)  # type: ignore
        bp.add_url_rule('/update_user_usage/', view_func=UpdateUserUsageApi)  # type: ignore
        bp.add_url_rule('/all-configs/', view_func=AllConfigsApi)  # type: ignore
        
        bp.add_url_rule('/all-public-port/', view_func=AllPublicPortsApi)  # type: ignore
        
        from .user_api import UserApi
        from .users_api import UsersApi

        bp.add_url_rule('/user/<uuid:uuid>/', view_func=UserApi)  # type: ignore
        
        bp.add_url_rule('/user/', view_func=UsersApi)  # type: ignore

        from .custom_proxy_api import (
            CustomProxiesApi,
            CustomProxyApi,
            CustomProxyEnableApi,
            CustomProxyDuplicateApi,
            CustomProxyValidateApi,
            CustomProxyValidateByIdApi,
            CustomProxyGenerateExampleApi,
            CustomProxyGenerateExampleByIdApi,
            CustomProxyGenerateBundleApi,
            CustomProxyMetaApi,
            CustomProxyExportApi,
            CustomProxyImportApi,
        )
        from .proxy_template_api import ProxyTemplatesApi, ProxyTemplateApi, ProxyTemplateDuplicateApi
        from .proxy_base_config_api import (
            ProxyBaseConfigsApi,
            ProxyBaseConfigApi,
            ProxyBaseConfigDuplicateApi,
            ProxyBaseConfigMetaApi,
            ProxyBaseConfigValidateApi,
            ProxyBaseConfigExportApi,
            ProxyBaseConfigImportApi,
        )
        from .template_variables_api import TemplateVariablesApi
        from .domain_api import DomainsOptionsApi, DomainsQuickAddApi

        bp.add_url_rule('/custom-proxies/', view_func=CustomProxiesApi)  # type: ignore
        bp.add_url_rule('/custom-proxies/meta/', view_func=CustomProxyMetaApi)  # type: ignore
        bp.add_url_rule('/custom-proxies/validate/', view_func=CustomProxyValidateApi)  # type: ignore
        bp.add_url_rule('/custom-proxies/generate-example/', view_func=CustomProxyGenerateExampleApi)  # type: ignore
        bp.add_url_rule('/custom-proxies/generate-bundle/', view_func=CustomProxyGenerateBundleApi)  # type: ignore
        bp.add_url_rule('/custom-proxies/export/', view_func=CustomProxyExportApi)  # type: ignore
        bp.add_url_rule('/custom-proxies/import/', view_func=CustomProxyImportApi)  # type: ignore
        bp.add_url_rule('/custom-proxies/<int:proxy_id>/', view_func=CustomProxyApi)  # type: ignore
        bp.add_url_rule('/custom-proxies/<int:proxy_id>/enable/', view_func=CustomProxyEnableApi)  # type: ignore
        bp.add_url_rule('/custom-proxies/<int:proxy_id>/duplicate/', view_func=CustomProxyDuplicateApi)  # type: ignore
        bp.add_url_rule('/custom-proxies/<int:proxy_id>/validate/', view_func=CustomProxyValidateByIdApi)  # type: ignore
        bp.add_url_rule('/custom-proxies/<int:proxy_id>/generate-example/', view_func=CustomProxyGenerateExampleByIdApi)  # type: ignore
        bp.add_url_rule('/proxy-templates/', view_func=ProxyTemplatesApi)  # type: ignore
        bp.add_url_rule('/proxy-templates/<int:template_id>/', view_func=ProxyTemplateApi)  # type: ignore
        bp.add_url_rule('/proxy-templates/<int:template_id>/duplicate/', view_func=ProxyTemplateDuplicateApi)  # type: ignore
        bp.add_url_rule('/proxy-base-configs/meta/', view_func=ProxyBaseConfigMetaApi)  # type: ignore
        bp.add_url_rule('/proxy-base-configs/validate/', view_func=ProxyBaseConfigValidateApi)  # type: ignore
        bp.add_url_rule('/proxy-base-configs/export/', view_func=ProxyBaseConfigExportApi)  # type: ignore
        bp.add_url_rule('/proxy-base-configs/import/', view_func=ProxyBaseConfigImportApi)  # type: ignore
        bp.add_url_rule('/proxy-base-configs/', view_func=ProxyBaseConfigsApi)  # type: ignore
        bp.add_url_rule('/proxy-base-configs/<int:config_id>/', view_func=ProxyBaseConfigApi)  # type: ignore
        bp.add_url_rule('/proxy-base-configs/<int:config_id>/duplicate/', view_func=ProxyBaseConfigDuplicateApi)  # type: ignore
        bp.add_url_rule('/template-variables/', view_func=TemplateVariablesApi)  # type: ignore
        bp.add_url_rule('/domains/options/', view_func=DomainsOptionsApi)  # type: ignore
        bp.add_url_rule('/domains/', view_func=DomainsQuickAddApi)  # type: ignore

        from .server_ip_api import (
            DomainHealthCheckApi,
            ServerIpApi,
            ServerIpHealthCheckApi,
            ServerIpsApi,
        )

        bp.add_url_rule('/server-ips/', view_func=ServerIpsApi)  # type: ignore
        bp.add_url_rule('/server-ips/<int:ip_id>/', view_func=ServerIpApi)  # type: ignore
        bp.add_url_rule('/server-ips/<int:ip_id>/health-check/', view_func=ServerIpHealthCheckApi)  # type: ignore
        bp.add_url_rule('/domains/<int:domain_id>/health-check/', view_func=DomainHealthCheckApi)  # type: ignore
        
    app.register_blueprint(bp)


def has_permission(model) -> bool:
    '''Check if the authenticated account has permission to do an action(get,insert,update,delete) on the another admin'''
    if g.account.uuid == AdminUser.get_super_admin_uuid():
        return True
    if isinstance(model, AdminUser) and model.parent_admin_id == g.account.id:
        return True
    elif isinstance(model, User) and model.added_by == g.account.id:
        return True

    return False
