import threading
from collections.abc import Callable

from flask import copy_current_request_context
from loguru import logger

from hiddifypanel.models import ConfigEnum, PanelMode, User, hconfig
from hiddifypanel.panel.commercial.restapi.v2.panel.schema import PanelInfoOutputSchema
from hiddifypanel.panel.commercial.restapi.v2.parent.schema import UsageData, UsageInputOutputSchema

from .api_client import NodeApiClient, NodeApiErrorSchema


def is_child() -> bool:
    return hconfig(ConfigEnum.panel_mode) == PanelMode.child


def is_parent() -> bool:
    return hconfig(ConfigEnum.panel_mode) == PanelMode.parent


# region usage


def get_users_usage_data_for_api() -> UsageInputOutputSchema:
    res = UsageInputOutputSchema()
    res.usages = []
    for u in User.query.all():
        usage_data = UsageData()
        usage_data.uuid = u.uuid
        usage_data.usage = u.current_usage
        usage_data.devices = u.devices
        res.usages.append(usage_data)
    return res


def convert_usage_api_response_to_dict(data: dict | UsageInputOutputSchema) -> dict:
    if isinstance(data, UsageInputOutputSchema):
        data = data.model_dump(mode="json")
    converted = {}
    for i in data["usages"]:
        devices = i.get("devices") or []
        if isinstance(devices, str):
            devices_str = devices
        else:
            devices_str = ",".join(devices)
        converted[str(i["uuid"])] = {
            "usage": i["usage"],
            "devices": devices_str,
        }
    return converted


# endregion

# TODO: use cache for these functions in release
# @cache.cache(ttl=150)


def is_panel_active(domain: str, proxy_path: str, apikey: str | None = None) -> bool:
    base_url = f"https://{domain}/{proxy_path}"
    res = NodeApiClient(base_url, apikey).get("/api/v2/panel/ping/", dict)
    if isinstance(res, NodeApiErrorSchema):
        logger.error(f"Error while checking if panel is active: {res.msg}")
        return False
    if "PONG" in res["msg"]:
        logger.debug(f"Panel is active: {res['msg']}")
        return True
    logger.debug("Panel is not active")
    return False


# @cache.cache(300)
def get_panel_info(domain: str, proxy_path: str, apikey: str | None = None) -> dict | None:
    base_url = f"https://{domain}/{proxy_path}"
    res = NodeApiClient(base_url, apikey).get("/api/v2/panel/info/", PanelInfoOutputSchema)
    if isinstance(res, NodeApiErrorSchema):
        logger.error(f"Error while getting panel info from {domain}: {res.msg}")
        return None
    return res


def run_node_op_in_bg(op: Callable, *args, **kwargs):
    @copy_current_request_context
    def wrapped_op():
        op(*args, **kwargs)

    threading.Thread(target=wrapped_op).start()
