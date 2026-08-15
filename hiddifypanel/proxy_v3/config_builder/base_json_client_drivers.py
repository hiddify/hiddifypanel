from __future__ import annotations

import re

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide
from hiddifypanel.proxy_v3.config_builder.base import BaseConfigBuilderDriver
from hiddifypanel.proxy_v3.config_builder.client_selection import select_client_config
from hiddifypanel.proxy_v3.config_builder.hiddify_core.common import compose_config_from_blocks, render_template_blocks
from hiddifypanel.proxy_v3.config_builder.models import ConfigBuilderModel, MessageModel, ProxyBlock
from hiddifypanel.proxy_v3.context_vars.builder.utils import make_jinja_context
from hiddifypanel.proxy_v3.context_vars.ctx_client import ClientContextVar
from hiddifypanel.proxy_v3.context_vars.proxy import ConfigVar
from hiddifypanel.proxy_v3.context_vars.version import TemplateVersion
from hiddifypanel.proxy_v3.template_catalog.client_builder import USE_HIDDIFY_CORE_PLACEHOLDER

_USE_HIDDIFY_CORE_RE = re.compile(r"\{#\s*use_hiddify_core\s*\(\s*\)\s*#\}")


class JsonClientOutboundDriver(BaseConfigBuilderDriver):
    """Render one proxy's client outbound/endpoint blocks into the core's base shell."""

    side = BaseConfigSide.client
    block_names = ("outbounds", "endpoints")

    def build(self, child_id: int, ctx: ClientContextVar) -> ConfigBuilderModel:
        messages: list[MessageModel] = []
        client_config = self._select_client_config(ctx)
        if client_config is None:
            messages.append(
                MessageModel(
                    level="warning",
                    message=f"No {self.core.value} client config for proxy {ctx.proxy.tag or ctx.proxy.id}",
                )
            )
            return ConfigBuilderModel(core=self.core, side=self.side, config="", messages=messages)

        proxy_blocks = self.build_proxy_config(child_id, ctx, messages, client_config=client_config)
        return compose_config_from_blocks(
            child_id,
            ctx,
            proxy_blocks,
            core=self.core,
            side=self.side,
            block_names=self.block_names,
            min_version=self._min_version(ctx),
            messages=messages,
        )

    def build_proxy_config(
        self,
        child_id: int,
        ctx: ClientContextVar,
        messages: list[MessageModel],
        *,
        client_config: ConfigVar,
    ) -> list[ProxyBlock]:
        content = self._resolve_client_template(ctx, client_config, messages)
        if content is None:
            return []
        return render_template_blocks(
            child_id,
            make_jinja_context(ctx),
            content,
            self.block_names,
            ctx.proxy.tag or str(ctx.proxy.id),
            messages,
        )

    def _resolve_client_template(
        self,
        ctx: ClientContextVar,
        client_config: ConfigVar,
        messages: list[MessageModel],
    ) -> str | None:
        return client_config.content

    def _select_client_config(self, ctx: ClientContextVar) -> ConfigVar | None:
        return select_client_config(ctx.proxy.client_configs, self.core, self._min_version(ctx))

    def _min_version(self, ctx: ClientContextVar) -> TemplateVersion:
        if self.core == TemplateCore.hiddify_core:
            ver = ctx.platform.hiddify.version
        elif self.core == TemplateCore.singbox:
            ver = ctx.platform.singbox.version
        else:
            return ctx.platform.app_version
        # Fall back to app version when the UA did not advertise a core-specific build.
        if str(ver) in ("", "0.0.0"):
            return ctx.platform.app_version
        return ver
