from __future__ import annotations

from packaging.version import Version

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide, ProxyBaseConfig
from hiddifypanel.proxy_v3.context_vars.version import TemplateVersion

from .template_blocks import extract_block_body


def resolve_base_config_content(child_id: int, side: BaseConfigSide, core: TemplateCore, min_version: TemplateVersion) -> str:

    all_rows: list[ProxyBaseConfig] = ProxyBaseConfig.query.filter(
        ProxyBaseConfig.enable.is_(True),
        ProxyBaseConfig.side == side,
        ProxyBaseConfig.core == core,
        (ProxyBaseConfig.child_id == child_id) | (ProxyBaseConfig.child_id == 0),
    ).all()
    filtered_rows = [(TemplateVersion(x.version), x) for x in all_rows]
    filtered_rows = [x for x in filtered_rows if x[0] >= min_version]
    if not filtered_rows:
        return ""
    return max(filtered_rows, key=lambda x: x[0])[1].effective_content()


def extract_base_config_shell(content: str) -> str:
    return extract_block_body(content, "base_config") or content
