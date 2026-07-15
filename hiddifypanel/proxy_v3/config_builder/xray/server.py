from __future__ import annotations

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide
from hiddifypanel.proxy_v3.config_builder.base import BaseConfigBuilderDriver
from hiddifypanel.proxy_v3.config_builder.hiddify_core.common import compose_config_from_blocks, render_template_blocks
from hiddifypanel.proxy_v3.config_builder.models import ConfigBuilderModel, MessageModel, ProxyBlock
from hiddifypanel.proxy_v3.context_vars.builder.utils import make_jinja_context
from hiddifypanel.proxy_v3.context_vars.ctx_server import ServerContextProxyVar, ServerContextVar
from hiddifypanel.proxy_v3.context_vars.version import TemplateVersion


class XrayServerDriver(BaseConfigBuilderDriver):
    core = TemplateCore.xray
    side = BaseConfigSide.server
    block_names = ("inbounds",)

    def build(self, child_id: int, ctx: ServerContextVar) -> ConfigBuilderModel:
        messages: list[MessageModel] = []
        proxy_blocks: list[ProxyBlock] = []
        for proxy_var in ctx.proxies:
            proxy_ctx = ctx.use_proxy(proxy_var)
            proxy_blocks.extend(self.build_proxy_config(child_id, proxy_ctx, messages))

        return compose_config_from_blocks(
            child_id,
            ctx,
            proxy_blocks,
            core=self.core,
            side=self.side,
            block_names=self.block_names,
            messages=messages,
            min_version=TemplateVersion("0.0.0"),
        )

    def build_proxy_config(self, child_id: int, ctx: ServerContextProxyVar, messages: list[MessageModel]) -> list[ProxyBlock]:
        proxy_row = ctx.proxy
        if not proxy_row:
            return []
        if proxy_row.server_config.core != self.core:
            return []

        return render_template_blocks(
            child_id,
            make_jinja_context(ctx),
            proxy_row.server_config.content,
            self.block_names,
            proxy_row.tag,
            messages,
        )
