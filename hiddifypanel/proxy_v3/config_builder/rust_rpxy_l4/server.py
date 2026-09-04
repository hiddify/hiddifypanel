from __future__ import annotations

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide
from hiddifypanel.proxy_v3.config_builder.models import ConfigBuilderModel, MessageModel
from hiddifypanel.proxy_v3.config_builder.render import render_section
from hiddifypanel.proxy_v3.config_builder.text_server import TextServerDriver
from hiddifypanel.proxy_v3.context_vars.builder.utils import make_jinja_context
from hiddifypanel.proxy_v3.context_vars.ctx_server import ServerContextVar
from hiddifypanel.proxy_v3.template_catalog.paths import TEMPLATES_ROOT


class RustRpxyL4ServerDriver(TextServerDriver):
    core = TemplateCore.rust_rpxy_l4
    side = BaseConfigSide.server


class RustRpxyL4HttpServerDriver(TextServerDriver):
    """Companion HTTP listener (port 80) using rust-rpxy-l4/server/http.j2."""

    core = TemplateCore.rust_rpxy_l4
    side = BaseConfigSide.server
    template_relpath = "rust-rpxy-l4/server/http.j2"

    def build(self, child_id: int, ctx: ServerContextVar) -> ConfigBuilderModel:
        messages: list[MessageModel] = []
        path = TEMPLATES_ROOT / self.template_relpath
        base = path.read_text(encoding="utf-8") if path.is_file() else ""
        if not base.strip():
            messages.append(MessageModel(level="warning", message=f"Missing {self.template_relpath}"))
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
