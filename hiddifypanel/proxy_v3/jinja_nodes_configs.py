"""Jinja ``get_nodes_configs(core)`` — fetch client configs from child nodes via ``download()``."""

from __future__ import annotations

from typing import Any

from jinja2 import pass_context
from loguru import logger

from hiddifypanel.models import Child, ConfigEnum, Domain, hconfig
from hiddifypanel.models.child import ChildMode
from hiddifypanel.proxy_v3.context_vars.ctx_client import ClientContextVar
from hiddifypanel.proxy_v3.jinja_download import download


def _caller_user_uuid(context: Any) -> str | None:
    if ctx := get_context(context):
        return str(ctx.user.uuid or "").strip() or None


def _caller_user_agent(context: Any) -> str:
    if ctx := get_context(context):
        return (ctx.platform.useragent or "").strip()
    return ""


def get_context(context: Any) -> ClientContextVar | None:
    if context is None:
        return None
    ctx = context.get("ctx")
    if isinstance(ctx, ClientContextVar):
        return ctx
    return None


def _child_base_url(child: Child) -> str | None:
    domain = Domain.get_panel_link(child.id)
    if not domain:
        return None
    admin_path = hconfig(ConfigEnum.proxy_path_admin, child.id)
    if not admin_path:
        return None
    return f"https://{domain}/{admin_path}"


def _node_config_urls() -> list[str]:
    children = Child.query.filter(Child.id != 0, Child.mode.in_([ChildMode.remote, ChildMode.virtual])).order_by(Child.id).all()
    urls: list[str] = []
    for child in children:
        base_url = _child_base_url(child)
        if not base_url:
            logger.debug(f"get_nodes_configs: skip child {child.name} (no panel link)")
            continue
        urls.append(f"{base_url.rstrip('/')}/api/v2/child/client-configs/")
    return urls


@pass_context
def get_nodes_configs(context: Any, core: str, cache: str | int = "1h") -> list[Any]:
    """Fetch client configs from all child nodes via ``download()``.

    Jinja usage::

        {% set node_configs = get_nodes_configs("hiddify-core", "1h") %}
        {% set node_configs = get_nodes_configs("xray", "1h") %}
        {% set node_configs = get_nodes_configs("sublink", "1h") %}

    - ``core``: ``hiddify-core`` | ``singbox`` | ``xray`` | ``clash`` | ``sublink``
    - ``cache``: TTL such as ``1h`` (default), ``30m``, ``0`` to disable
    - ``sublink`` uses ``txt``; other cores use ``json``
    - POSTs JSON body with ``raw=true`` and ``Hiddify-API-Key`` header
    - No-ops on child panels / when serving another node (returns ``[]``)
    """
    from hiddifypanel import g, hutils

    if hutils.node.is_child():
        return []
    if getattr(g, "node", None) is not None:
        return []

    core_name = str(core or "").strip().lower()
    if not core_name:
        logger.warning("get_nodes_configs: missing core")
        return []

    user_uuid = _caller_user_uuid(context)
    if not user_uuid:
        logger.warning("get_nodes_configs: missing ctx.user.uuid")
        return []

    apikey = hconfig(ConfigEnum.unique_id) or ""
    if not apikey:
        logger.warning("get_nodes_configs: missing unique_id apikey")
        return []

    urls = _node_config_urls()
    if not urls:
        return []

    content_type = "txt" if core_name == "sublink" else "json"
    return download(
        context,
        content_type,
        cache,
        *urls,
        method="POST",
        headers={"Hiddify-API-Key": apikey},
        data={
            "core": core_name,
            "user_uuid": user_uuid,
            "user_agent": _caller_user_agent(context),
            "pretty": False,
            "raw": True,
        },
    )
