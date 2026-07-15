from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide

from .models import ConfigBuilderModel


class BaseConfigBuilderDriver(ABC):
    """Compose a core base config by filling named Jinja blocks with active proxies."""

    core: TemplateCore
    side: BaseConfigSide
    block_names: tuple[str, ...]

    @abstractmethod
    def build(self, child_id: int, ctx: Any) -> ConfigBuilderModel:
        """Render base shell and inject all active proxy fragments into ``block_names``."""
