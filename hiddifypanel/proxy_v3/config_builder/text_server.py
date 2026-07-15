from __future__ import annotations

from hiddifypanel.proxy_v3.config_builder.base import BaseConfigBuilderDriver
from hiddifypanel.proxy_v3.config_builder.base_config import extract_base_config_shell, resolve_base_config_content
from hiddifypanel.proxy_v3.config_builder.models import ConfigBuilderModel, MessageModel
from hiddifypanel.proxy_v3.config_builder.render import render_section
from hiddifypanel.proxy_v3.context_vars.builder.utils import make_jinja_context
from hiddifypanel.proxy_v3.context_vars.ctx_server import ServerContextVar
from hiddifypanel.proxy_v3.context_vars.version import TemplateVersion
from hiddifypanel.proxy_v3.template_catalog.base_configs import default_base_content


class TextServerDriver(BaseConfigBuilderDriver):
    """Render plain-text server base shells (HAProxy, nginx fallback, etc.)."""

    block_names = ()

    def build(self, child_id: int, ctx: ServerContextVar) -> ConfigBuilderModel:
        messages: list[MessageModel] = []
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
            as_json_object=False,
            parse_json=False,
        )
        if section.error:
            data: dict = {}
            if section.error_detail is not None:
                data["details"] = section.error_detail
            messages.append(MessageModel(level="error", message=str(section.error), data=data))

        return ConfigBuilderModel(
            core=self.core,
            side=self.side,
            config=section.rendered or "",
            messages=messages,
        )
