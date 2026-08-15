from __future__ import annotations

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.proxy_v3.config_builder.base_json_client_drivers import JsonClientOutboundDriver


class XrayClientDriver(JsonClientOutboundDriver):
    core = TemplateCore.xray
    block_names = ("outbounds",)
