from __future__ import annotations

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide
from hiddifypanel.proxy_v3.config_builder.base import BaseConfigBuilderDriver
from hiddifypanel.proxy_v3.config_builder.client_selection import select_client_config
from hiddifypanel.proxy_v3.config_builder.models import ConfigBuilderModel, MessageModel, ProxyBlock
from hiddifypanel.proxy_v3.context_vars.builder.utils import make_jinja_context
from hiddifypanel.proxy_v3.context_vars.ctx_client import ClientContextVar
from hiddifypanel.proxy_v3.context_vars.proxy import ConfigVar

from .common import compose_config_from_blocks, render_template_blocks


class HiddifyCoreClientDriver(BaseConfigBuilderDriver):
    core = TemplateCore.hiddify_core
    side = BaseConfigSide.client
    block_names = ("outbounds", "endpoints")

    def build(self, child_id: int, ctx: ClientContextVar) -> ConfigBuilderModel:
        messages: list[MessageModel] = []
        client_config = self._select_client_config(ctx)
        if client_config is None:
            messages.append(MessageModel(level="error", message=f"No {self.core.value} client config for proxy {ctx.proxy.tag or ctx.proxy.id}"))
            return ConfigBuilderModel(core=self.core, side=self.side, config="", messages=messages)

        proxy_blocks = self.build_proxy_config(child_id, ctx, messages, client_config=client_config)
        return compose_config_from_blocks(
            child_id,
            ctx,
            proxy_blocks,
            core=self.core,
            side=self.side,
            block_names=self.block_names,
            min_version=ctx.platform.hiddify.version,
            messages=messages,
        )

    def build_proxy_config(self, child_id: int, ctx: ClientContextVar, messages: list[MessageModel], *, client_config: ConfigVar) -> list[ProxyBlock]:
        return render_template_blocks(
            child_id,
            make_jinja_context(ctx),
            client_config.content,
            self.block_names,
            ctx.proxy.tag or str(ctx.proxy.id),
            messages,
        )

    def _select_client_config(self, ctx: ClientContextVar) -> ConfigVar | None:
        return select_client_config(ctx.proxy.client_configs, self.core, ctx.platform.hiddify.version)
