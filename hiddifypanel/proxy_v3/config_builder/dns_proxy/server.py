from __future__ import annotations

import json

from hiddifypanel.models.custom_proxy import CustomProxyMode, TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide
from hiddifypanel.proxy_v3.config_builder.base import BaseConfigBuilderDriver
from hiddifypanel.proxy_v3.config_builder.base_config import extract_base_config_shell, resolve_base_config_content
from hiddifypanel.proxy_v3.config_builder.jinja_render import render_template_text
from hiddifypanel.proxy_v3.config_builder.models import ConfigBuilderModel, MessageModel
from hiddifypanel.proxy_v3.config_builder.render import render_section
from hiddifypanel.proxy_v3.context_vars.builder.utils import make_jinja_context
from hiddifypanel.proxy_v3.context_vars.ctx_server import ServerContextProxyVar, ServerContextVar
from hiddifypanel.proxy_v3.context_vars.version import TemplateVersion
from hiddifypanel.proxy_v3.template_catalog.base_configs import default_base_content


class DnsProxyServerDriver(BaseConfigBuilderDriver):
    """Render DNS-gateway proxy sidecars + DNSTM base config (→ dnstm.json)."""

    core = TemplateCore.dns_proxy
    side = BaseConfigSide.server
    block_names: tuple[str, ...] = ()

    def build(self, child_id: int, ctx: ServerContextVar) -> ConfigBuilderModel:
        messages: list[MessageModel] = []
        for proxy_var in ctx.proxies:
            self._render_proxy(child_id, ctx.use_proxy(proxy_var), messages)

        return self._build_dnstm_base(child_id, ctx, messages)

    def _build_dnstm_base(
        self,
        child_id: int,
        ctx: ServerContextVar,
        messages: list[MessageModel],
    ) -> ConfigBuilderModel:
        base = resolve_base_config_content(child_id, self.side, self.core, TemplateVersion("0.0.0"))
        if not (base or "").strip():
            try:
                base = default_base_content(self.side.value, self.core.value)
            except FileNotFoundError:
                base = ""
        base = extract_base_config_shell(base) or base

        if not (base or "").strip():
            messages.append(
                MessageModel(
                    level="warning",
                    message=f"No server base template found for {self.core.value}",
                )
            )
            return ConfigBuilderModel(core=self.core, side=self.side, config="", messages=messages)

        section = render_section(
            base,
            child_id,
            make_jinja_context(ctx),
            as_json_object=True,
            parse_json=True,
        )
        if section.error:
            data: dict = {}
            if section.error_detail is not None:
                data["details"] = section.error_detail
            messages.append(MessageModel(level="error", message=str(section.error), data=data))
            return ConfigBuilderModel(core=self.core, side=self.side, config="", messages=messages)

        rendered = section.rendered or ""
        if section.parsed is not None:
            rendered = json.dumps(section.parsed, indent=2, ensure_ascii=False)

        return ConfigBuilderModel(
            core=self.core,
            side=self.side,
            config=rendered,
            messages=messages,
        )

    def _render_proxy(self, child_id: int, ctx: ServerContextProxyVar, messages: list[MessageModel]) -> None:
        proxy_row = ctx.proxy
        if not proxy_row:
            return
        if proxy_row.mode != CustomProxyMode.domains_dns_gateway:
            return
        if str(proxy_row.server_config.core) != str(self.core):
            return
        content = str(proxy_row.server_config.content or "")
        if not content.strip():
            return
        try:
            render_template_text(content, child_id, make_jinja_context(ctx))
        except Exception as exc:
            messages.append(
                MessageModel(
                    level="error",
                    message=f"dns_proxy render failed for {proxy_row.tag or proxy_row.slug}: {exc}",
                    data={"proxy": proxy_row.tag or proxy_row.slug, "error": str(exc)},
                )
            )
