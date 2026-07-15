from __future__ import annotations

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide
from hiddifypanel.proxy_v3.config_builder.text_server import TextServerDriver


class RustRpxyL4ServerDriver(TextServerDriver):
    core = TemplateCore.rust_rpxy_l4
    side = BaseConfigSide.server
