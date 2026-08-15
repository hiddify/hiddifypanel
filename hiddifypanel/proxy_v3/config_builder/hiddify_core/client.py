from hiddifypanel.proxy_v3.config_builder.base_json_client_drivers import JsonClientOutboundDriver
from hiddifypanel.models.custom_proxy import TemplateCore


class HiddifyCoreClientDriver(JsonClientOutboundDriver):
    core = TemplateCore.hiddify_core
