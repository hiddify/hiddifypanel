from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from typing import Any

from flask import copy_current_request_context
from loguru import logger

from hiddifypanel.models import ConfigEnum, PanelMode, hconfig
from hiddifypanel.panel.commercial.restapi.v2.panel.schema import PanelInfoOutputSchema, PongOutputSchema
from hiddifypanel.panel.commercial.restapi.v2.parent.schema import UsageInputOutputSchema

from .api_client import NodeApiClient, NodeApiErrorSchema


def is_child() -> bool:
    return hconfig(ConfigEnum.panel_mode) == PanelMode.child


def is_parent() -> bool:
    return hconfig(ConfigEnum.panel_mode) == PanelMode.parent


# region usage


def convert_usage_api_response_to_dict(
    data: UsageInputOutputSchema | Mapping[str, Any] | dict[str, Any],
) -> dict[str, dict[str, int | str]]:
    """Legacy {uuid: {usage, upload, download, devices}} map for callers that still expect a plain dict."""
    schema = data if isinstance(data, UsageInputOutputSchema) else UsageInputOutputSchema.model_validate(data)
    converted: dict[str, dict[str, int | str]] = {}
    for item in schema.usages:
        converted[item.uuid] = {
            "usage": int(item.usage or 0),
            "upload": int(item.upload or 0),
            "download": int(item.download or 0),
            "devices": ",".join(item.devices),
        }
    return converted


# endregion


def is_panel_active(domain: str, proxy_path: str, apikey: str | None = None) -> bool:
    base_url = f"https://{domain}/{proxy_path}"

    res = NodeApiClient(base_url, apikey).get("/api/v2/panel/ping/", PongOutputSchema)
    if isinstance(res, NodeApiErrorSchema):
        logger.error(f"Error while checking if panel is active: {res.msg}")
        return False
    if isinstance(res, PongOutputSchema) and "PONG" in str(res.msg):
        logger.debug(f"Panel is active: {res.msg}")
        return True
    logger.debug("Panel is not active")
    return False


def get_panel_info(domain: str, proxy_path: str, apikey: str | None = None) -> dict | PanelInfoOutputSchema | None:
    base_url = f"https://{domain}/{proxy_path}"
    res = NodeApiClient(base_url, apikey).get("/api/v2/panel/info/", PanelInfoOutputSchema)
    if isinstance(res, NodeApiErrorSchema):
        logger.error(f"Error while getting panel info from {domain}: {res.msg}")
        return None
    return res


def run_node_op_in_bg(op: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    @copy_current_request_context
    def wrapped_op() -> None:
        op(*args, **kwargs)

    threading.Thread(target=wrapped_op).start()
