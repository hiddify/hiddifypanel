from __future__ import annotations

import json
import re
import threading
from collections.abc import Callable, Mapping
from typing import Any

from flask import copy_current_request_context
from loguru import logger

from hiddifypanel.models import ConfigEnum, hconfig
from hiddifypanel.panel.commercial.restapi.v2.panel.schema import PanelInfoOutputSchema, PongOutputSchema
from hiddifypanel.panel.commercial.restapi.v2.parent.schema import UsageInputOutputSchema

from .api_client import GATEWAY_STATUSES, NOT_THE_PANEL, NodeApiClient, NodeApiErrorSchema


def is_child() -> bool:
    """A node: it has a parent panel."""
    return bool(hconfig(ConfigEnum.parent_panel))


def is_parent() -> bool:
    """A parent: it has nodes of its own."""
    from hiddifypanel.models import Child, ChildMode

    return not is_child() and Child.query.filter(Child.id != 0, Child.mode != ChildMode.parent).first() is not None


def panel_mode() -> str:
    """`child`, `parent` or `standalone`, as the admin UI reads it."""
    return "child" if is_child() else "parent" if is_parent() else "standalone"


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


def is_panel_active(base_url: str, apikey: str | None = None) -> tuple[bool, str]:

    res = NodeApiClient(base_url, apikey).get("/api/v2/panel/ping/", PongOutputSchema)
    if isinstance(res, NodeApiErrorSchema):
        logger.error(f"Error while checking if panel is active: {res.msg}")
        return False, res.msg
    if isinstance(res, PongOutputSchema) and "PONG" in str(res.msg):
        logger.debug(f"Panel is active: {res.msg}")
        return True, ""
    logger.debug("Panel is not active")
    return False, f"Panel is not active: {res.msg}"


#: A node's address with its secret admin path: the path is cut from what the Nodes page shows.
_URL_PATH = re.compile(r"(https?://[^/\s'\"]+)/[^\s'\"]*")


def contact_error(res: NodeApiErrorSchema | str) -> tuple[str, str]:
    """Why this panel could not talk to a node: ``(code, detail)``.

    The Nodes page explains each code (what happened, why, how to fix it); ``detail`` is the technical text for
    "Copy technical details", without the node's secret path.
    """
    if isinstance(res, str):
        code = res if res in ("no_url", "auth", "not_found", "timeout", "refused", "dns", "tls", "gateway", "not_panel", "server_error") else "unknown"
        return code, "" if code != "unknown" else " ".join(_URL_PATH.sub(r"\1/…", res).split())[:400]
    head, _, body = res.msg.partition(" | body=")
    try:
        said = json.loads(body) if body else None
    except ValueError:
        said = None
    message = str((said.get("message") or said.get("msg") or "") if isinstance(said, dict) else "") or head
    reason, msg = res.reason or "", res.msg or ""
    if res.code:
        detail = f"HTTP {res.code} {reason}".strip() + (f": {message}" if message and message != reason else "")
    else:
        detail = f"{reason}: {msg}" if reason else msg
    detail = " ".join(_URL_PATH.sub(r"\1/…", detail).split())[:400]
    if res.code in (401, 403):
        code = "auth"
    elif res.code in (404, 405):
        code = "not_found"
    elif res.code in GATEWAY_STATUSES:
        code = "gateway"
    elif NOT_THE_PANEL in msg or reason == "bad_response":
        code = "not_panel"
    elif 500 <= res.code < 600:
        code = "server_error"
    elif res.code:
        code = "unknown"
    elif "Timeout" in reason:
        code = "timeout"
    elif "SSL" in reason or "SSL" in msg or "certificate" in msg.lower():
        code = "tls"
    elif "NameResolution" in msg or "Name or service not known" in msg or "getaddrinfo" in msg:
        code = "dns"
    else:
        code = "refused"
    return code, detail


def panel_contact(base_url: str, apikey: str | None = None) -> tuple[bool, str, str]:
    """Ask a node whether its panel answers: ``(online, error code, detail)`` (see ``contact_error``)."""
    res = NodeApiClient(base_url, apikey).get("/api/v2/panel/ping/", PongOutputSchema)
    if isinstance(res, NodeApiErrorSchema):
        logger.error(f"Error while checking if panel is active: {res.msg}")
        return (False, *contact_error(res))
    if "PONG" in str(res.msg):
        return True, "", ""
    return False, "not_panel", f"unexpected answer: {str(res.msg)[:200]}"


def get_panel_info(domain: str, proxy_path: str, apikey: str | None = None) -> dict | PanelInfoOutputSchema | None:
    return get_panel_info_by_url(f"https://{domain}/{proxy_path}", apikey)


def get_panel_info_by_url(base_url: str, apikey: str | None = None) -> PanelInfoOutputSchema | None:
    res = NodeApiClient(base_url, apikey, max_retry=1).get("/api/v2/panel/info/", PanelInfoOutputSchema)
    if isinstance(res, NodeApiErrorSchema):
        logger.error(f"Error while getting panel info from {base_url}: {res.msg}")
        return None
    return res


def run_node_op_in_bg(op: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    @copy_current_request_context
    def wrapped_op() -> None:
        op(*args, **kwargs)

    threading.Thread(target=wrapped_op).start()
