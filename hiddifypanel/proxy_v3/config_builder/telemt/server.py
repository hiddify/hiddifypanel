from __future__ import annotations

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide
from hiddifypanel.proxy_v3.config_builder.text_server import TextServerDriver


class TelemtServerDriver(TextServerDriver):
    """Telegram MTProxy config written to generated/telemt.toml."""

    core = TemplateCore.telemt
    side = BaseConfigSide.server
