from __future__ import annotations

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.proxy_v3.context_vars.proxy import ConfigVar
from hiddifypanel.proxy_v3.context_vars.version import TemplateVersion
from packaging.version import Version


def select_client_config(configs: list[ConfigVar], core: TemplateCore, platform_version: TemplateVersion) -> ConfigVar | None:
    """Pick a client template for ``core`` using platform version or an exact bundle version."""
    candidates = [cfg for cfg in configs if cfg.core == core]
    if not candidates:
        return None

    compatible = [cfg for cfg in candidates if cfg.version <= platform_version]
    if not compatible:
        # Prefer any available template over skipping the proxy entirely.
        return max(candidates, key=lambda cfg: cfg.version, default=None)
    return max(compatible, key=lambda cfg: cfg.version, default=None)
