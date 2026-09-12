from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.proxy_v3.config_builder.base_json_client_drivers import JsonClientOutboundDriver
from hiddifypanel.proxy_v3.config_builder.hiddify_core.common import client_selector_tags
from hiddifypanel.proxy_v3.config_builder.models import ProxyBlock
from hiddifypanel.proxy_v3.context_vars.ctx_client import ClientContextVar


class HiddifyCoreClientDriver(JsonClientOutboundDriver):
    core = TemplateCore.hiddify_core

    def _assign_generated_proxy_tags(self, ctx: ClientContextVar, blocks: list[ProxyBlock]) -> None:
        ctx.client_proxy_tags = client_selector_tags(blocks)
