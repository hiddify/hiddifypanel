"""Jinja ``get_nodes_configs(core)`` — fetch client configs from child nodes via ``download()``."""

from __future__ import annotations

from typing import Any

from jinja2 import pass_context
from loguru import logger

from hiddifypanel.models import Child, ConfigEnum, hconfig
from hiddifypanel.models.child import ChildMode
from hiddifypanel.proxy_v3.context_vars.ctx_client import ClientContextVar
from hiddifypanel.proxy_v3.context_vars.domain import DomainIPVar
from hiddifypanel.proxy_v3.jinja_download import download


def _caller_user_uuid(context: Any) -> str | None:
    if ctx := get_context(context):
        return str(ctx.user.uuid or "").strip() or None


def _caller_render_core(context: Any) -> str:
    if ctx := get_context(context):
        return (ctx.render_core or "").strip().lower()
    return ""


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


def _remote_children() -> list[Child]:
    return Child.query.filter(Child.id != 0, Child.mode == ChildMode.remote).order_by(Child.id).all()


def domains_for_child(available: list[DomainIPVar], child_id: int) -> list[str]:
    """Domain hostnames from the sub's available set that belong to ``child_id`` only."""
    names: list[str] = []
    seen: set[str] = set()
    for domain in available:
        if int(domain.child_id or 0) != int(child_id):
            continue
        name = str(domain.name or "").strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


@pass_context
def get_nodes_configs(context: Any, core: str, cache: str | int = "1h") -> list[Any]:
    """Fetch client configs from all child nodes via ``download()``.

    Jinja usage::

        {% set node_configs = get_nodes_configs("hiddify-core", "1h") %}
        {% set node_configs = get_nodes_configs("xray", "1h") %}
        {% set node_configs = get_nodes_configs("sublink", "1h") %}

    - ``core``: ``hiddify-core`` | ``singbox`` | ``xray`` | ``clash`` | ``sublink``; the core actually
      being rendered wins, so a sing-box sub (which reuses the hiddify-core template) asks for ``singbox``
    - ``cache``: TTL such as ``1h`` (default), ``30m``, ``0`` to disable
    - ``sublink`` uses ``txt``, ``clash`` uses ``yaml``; other cores use ``json``
    - POSTs JSON body with ``raw=true`` and ``Hiddify-API-Key`` header
    - No-ops on child panels / when serving another node (returns ``[]``)
    - Each node only receives domains with that node's ``child_id`` (never parent hosts)
    - Skips a node when that filtered list is empty (``domains=[]`` must not mean "all")
    """
    from hiddifypanel import g, hutils

    if hutils.node.is_child():
        return []
    if getattr(g, "node", None) is not None:
        return []

    core_name = _caller_render_core(context) or str(core or "").strip().lower()
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

    available = get_available_domains(context)
    # Children render clash as YAML (a JSON parse would hand back the raw text).
    content_type = {"sublink": "txt", "clash": "yaml"}.get(core_name, "json")
    merged: list[Any] = []

    for child in _remote_children():
        base_url = (child.node_base_url or "").strip()
        if not base_url:
            logger.debug(f"get_nodes_configs: skip child {child.name} (no node_base_url)")
            continue
        domains = domains_for_child(available, child.id)
        if not domains:
            logger.debug(f"get_nodes_configs: skip child {child.name} (no domains for this sub)")
            continue
        url = f"{base_url.rstrip('/')}/api/v2/child/client-configs/"
        chunk = download(
            context,
            content_type,
            cache,
            url,
            method="POST",
            headers={"Hiddify-API-Key": apikey},
            data={
                "core": core_name,
                "user_uuid": user_uuid,
                "user_agent": _caller_user_agent(context),
                "pretty": False,
                "raw": True,
                "domains": domains,
            },
        )
        merged.extend(item for item in chunk if item is not None)
    return merged


# Groups and utility outbounds every client shell already defines; merging a remote
# config's copies duplicates tags (fatal in sing-box/xray) or nests Select in Select.
_SINGBOX_SHELL_TYPES = frozenset({"selector", "urltest", "direct", "block", "dns"})
_XRAY_SHELL_TAGS = frozenset({"direct", "block", "fragment", "freedom", "blackhole", "dns-out"})
_XRAY_SHELL_PROTOCOLS = frozenset({"freedom", "blackhole", "dns", "loopback"})


def remote_proxy_outbounds(conf: Any, core: str = "hiddify-core") -> list[dict[str, Any]]:
    """Proxy outbounds of a downloaded client config, without its groups/utility outbounds.

    ``conf`` is a sing-box/hiddify-core object, or an xray config / list of configs.
    """
    xray = str(core or "").lower() == "xray"
    configs = conf if isinstance(conf, list) else [conf]
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for cfg in configs:
        if not isinstance(cfg, dict):
            continue
        for outbound in cfg.get("outbounds") or []:
            if not isinstance(outbound, dict):
                continue
            tag = outbound.get("tag")
            if xray:
                if tag in _XRAY_SHELL_TAGS or outbound.get("protocol") in _XRAY_SHELL_PROTOCOLS:
                    continue
            elif outbound.get("type") in _SINGBOX_SHELL_TYPES:
                continue
            # xray subs repeat each outbound in the Auto config and its own config.
            if isinstance(tag, str) and tag:
                if tag in seen:
                    continue
                seen.add(tag)
            out.append(outbound)
    return out


def remote_endpoints(conf: Any) -> list[dict[str, Any]]:
    if not isinstance(conf, dict):
        return []
    return [item for item in conf.get("endpoints") or [] if isinstance(item, dict)]


def get_available_domains(context: Any) -> list[DomainIPVar]:
    if ctx := get_context(context):
        return list(ctx.proxy.domains or [])
    return []


def get_domains(context: Any) -> list[str]:
    """Hostname list from the current proxy (legacy helper; prefer ``domains_for_child``)."""
    return [str(domain.name or "").strip() for domain in get_available_domains(context) if domain.name]
