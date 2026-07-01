from __future__ import annotations

import datetime
from typing import Any

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.nodes import ContextReference

from hiddifypanel.models import ConfigEnum, get_hconfigs
from hiddifypanel.models.custom_proxy import normalize_custom_path
from hiddifypanel.proxy_v3.proxy_render_matrix import ProxyRenderCache, client_domain_vars_for_proxy

from .custom_proxy_ports import ports_dict_for_proxy_row
from hiddifypanel.proxy_v3.context_vars import build_client_context, build_server_context


class TemplateSkip(Exception):
    """Raised when a template intentionally skips rendering (outputs SKIP)."""

    def __init__(self, reason: str = "") -> None:
        self.reason = reason or ""
        super().__init__(self.reason or "SKIP")


class SkipExtension(Extension):
    """Jinja tag for {% skip() if condition %} or {% skip("reason") if condition %}."""

    tags = {"skip"}

    def parse(self, parser):
        next(parser.stream)
        reason = nodes.Const("")
        if parser.stream.current.test("lparen"):
            parser.stream.expect("lparen")
            if not parser.stream.current.test("rparen"):
                reason = parser.parse_expression()
            parser.stream.expect("rparen")
        if parser.stream.skip_if("name:if"):
            cond = parser.parse_expression()
        else:
            cond = nodes.Const(True)
        return nodes.If(cond, [nodes.ExprStmt(self.call_method("_do_skip", [ContextReference(), reason]))], [], [])

    def _do_skip(self, context, reason=""):
        if context.get("ignore_skip"):
            return ""
        message = str(reason).strip() if reason is not None else ""
        raise TemplateSkip(message)


class HconfigsAccessor(dict):
    """Legacy hconfigs accessor — prefer hconfig in new templates."""

    def __init__(self, hconfigs: dict | None = None):
        super().__init__()
        for key, value in (hconfigs or {}).items():
            name = getattr(key, "name", None) or str(key)
            super().__setitem__(name, value)

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, ConfigEnum):
            key = key.name
        return super().get(str(key))

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_") or name in ("get", "keys", "items", "values"):
            raise AttributeError(name)
        return self.get(name)

    def get(self, key: Any, default: Any = None) -> Any:  # type: ignore[override]
        if isinstance(key, ConfigEnum):
            key = key.name
        return super().get(str(key), default)


def wrap_hconfigs(hconfigs: dict | None) -> HconfigsAccessor:
    return HconfigsAccessor(hconfigs)


HIDDIFY_MANAGER_ROOT = "/opt/hiddify-manager"


def include_path(slug: str, prefix: str = ".cache/") -> str:
    """Return deployed path for a rendered sidecar file referenced by template slug.

    Usage in templates:
        path,map_beg({{ include_path('haproxy/server/maps/path_v10') }})
        req.ssl_sni,map_str({{ include_path('haproxy/server/maps/sni') }})

    HAProxy map slugs (haproxy/server/maps/*) resolve under haproxy/maps/.
    Other slugs resolve under /opt/hiddify-manager/{prefix}/{slug}.
    """
    rel = (slug or "").strip().lstrip("/")
    if not rel:
        raise ValueError("slug is required")

    rel_prefix = (prefix or ".cache/").strip().strip("/")
    rel = f"{rel_prefix}/{rel}" if rel_prefix else rel
    return f"{HIDDIFY_MANAGER_ROOT}/{rel}"


def skip_proxy() -> str:
    """Jinja callable fallback — templates should use {% skip() if cond %}."""
    raise TemplateSkip()


def _load_raw_hconfigs(child_id: int = 0) -> dict[str, Any]:
    try:
        raw = get_hconfigs(child_id)
        return {(getattr(k, "name", None) or str(k)): v for k, v in raw.items()}
    except RuntimeError:
        return {}


def build_hconfigs_context(child_id: int = 0) -> HconfigsAccessor:
    return wrap_hconfigs(_load_raw_hconfigs(child_id))


def _load_panel_domains(child_id: int) -> list[dict[str, Any]]:
    from hiddifypanel import hutils
    from hiddifypanel.models import Domain, get_hconfigs

    hconfigs = get_hconfigs(child_id)
    result: list[dict[str, Any]] = []
    for domain_db in Domain.query.filter(Domain.child_id == child_id).order_by(Domain.id).all():
        extracted = hutils.proxy.sni_host_server_extractor(domain_db, hconfigs)
        base = domain_db.to_dict(dump_ports=True, dump_child_id=True)
        base.update(
            {
                "sni": extracted.get("sni"),
                "host": extracted.get("host"),
                "server": extracted.get("server") or domain_db.domain,
            }
        )
        if domain_db.download_domain:
            base["download"] = hutils.proxy.sni_host_server_extractor(domain_db.download_domain, hconfigs)
        hutils.proxy.attach_domain_ech(base, hconfigs)
        result.append(base)
    return result


def _load_custom_proxies(child_id: int) -> list[dict[str, Any]]:
    from hiddifypanel.models.custom_proxy import CustomProxy

    rows = CustomProxy.query.filter(CustomProxy.child_id == child_id).order_by(CustomProxy.sort_order, CustomProxy.id).all()
    return [
        {
            "id": row.id,
            "enable": bool(row.enable),
            "mode": row.mode.value if row.mode else "",
            "l7_proto": row.l7_proto.value if row.l7_proto else None,
            "custom_path": row.custom_path or "",
            "server_core": row.server_core.value if row.server_core else "",
            "server_tag": row.server_tag or "",
            "server_config": row.effective_server_config_text(),
            **ports_dict_for_proxy_row(row),
        }
        for row in rows
    ]


def _user_mapping_for_template(entry: Any) -> dict[str, Any] | None:
    if entry is None:
        return None
    if isinstance(entry, dict):
        result = entry
    elif hasattr(entry, "to_dict"):
        try:
            result = entry.to_dict()
        except TypeError:
            result = None
    else:
        data = getattr(entry, "_data", None)
        if isinstance(data, dict):
            result = dict(data)
        else:
            uuid = getattr(entry, "uuid", None)
            result = {"uuid": uuid} if uuid else None
    if not isinstance(result, dict):
        return result
    if "uuid_hex" not in result and result.get("uuid"):
        result = dict(result)
        result["uuid_hex"] = str(result["uuid"]).replace("-", "")
    return result


def _normalize_template_users(users: Any, user: Any) -> list[dict[str, Any]]:
    if users is None:
        raw: list[Any] = [user] if user else []
    elif isinstance(users, dict):
        raw = [users]
    elif isinstance(users, (list, tuple)):
        raw = list(users)
    else:
        raw = [users]
    normalized: list[dict[str, Any]] = []
    for entry in raw:
        mapped = _user_mapping_for_template(entry)
        if mapped and mapped.get("uuid"):
            normalized.append(mapped)
    return normalized


def build_template_context(
    child_id: int = 0,
    *,
    user: User | dict[str, Any] | None = None,
    domain: Domain | DomainVar | dict[str, Any] | None = None,
    domain_data: dict[str, Any] | None = None,
    proxy: CustomProxy | ProxyVar | None = None,
    proxy_data: dict[str, Any] | None = None,
    tag: str = "",
    port: int = 443,
    ip: str = "",
    custom_path: str = "",
    domain_binding: str = "domain",
    user_agent: str | None = None,
    user_agent_parsed: dict[str, Any] | None = None,
    server_side: bool = False,
    users: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Full Jinja context with UserVar, DomainVar, HConfigVar, PlatformVar, ProxyVar."""
    from hiddifypanel.models.custom_proxy import CustomProxy
    from hiddifypanel.models.domain import Domain
    from hiddifypanel.models.user import User
    from hiddifypanel.proxy_v3.context_vars import DomainIPVar, IPVar, ProxyVar, build_client_context, build_server_context

    raw_hconfigs = _load_raw_hconfigs(child_id)
    hconfigs = wrap_hconfigs(raw_hconfigs)
    normalized_path = normalize_custom_path(custom_path)

    domain_input = domain if domain is not None else domain_data
    domain_db: Domain | None = None
    domain_var_: DomainIPVar
    if isinstance(domain_input, DomainIPVar):
        domain_var_ = domain_input
    elif isinstance(domain_input, Domain):
        domain_db = domain_input
        domain_var_ = DomainIPVar.from_domain(
            domain_db,
            raw_hconfigs,
            ip=IPVar.from_strings(ipv4=ip or None),
            port=port or None,
        )
    elif isinstance(domain_input, dict) and domain_input:
        domain_id = domain_input.get("id") or domain_input.get("domain_id")
        if domain_id:
            domain_db = Domain.query.filter(Domain.id == int(domain_id), Domain.child_id == child_id).first()
        if domain_db is None and domain_input.get("domain"):
            domain_db = Domain.query.filter(
                Domain.child_id == child_id,
                Domain.domain == str(domain_input.get("domain")).lower(),
            ).first()
        if domain_db is not None:
            domain_var_ = DomainIPVar.from_domain(
                domain_db,
                raw_hconfigs,
                ip=IPVar.from_strings(ipv4=ip or None),
                port=port or None,
            )
        else:
            domain_var_ = DomainIPVar()
            domain_var_.extra.update(domain_input)
    else:
        domain_var_ = DomainIPVar()

    if ip and domain_binding == "ip":
        bound_ip = IPVar.from_strings(ipv4=ip)
        domain_var_ = domain_var_.model_copy(update={"server": ip, "ip": bound_ip})

    user_db: User | None = None
    if isinstance(user, User):
        user_db = user
    elif isinstance(user, dict) and user.get("id"):
        user_db = User.query.filter(User.id == int(user["id"])).first()

    proxy_row: CustomProxy | None = None
    if isinstance(proxy, CustomProxy):
        proxy_row = proxy
    elif isinstance(proxy_data, dict) and proxy_data.get("id"):
        proxy_row = CustomProxy.query.filter(
            CustomProxy.id == int(proxy_data["id"]),
            CustomProxy.child_id == child_id,
        ).first()

    client_ctx = build_client_context(
        user=user_db or user,
        domain=domain_var_,
        proxy=proxy_row,
        hconfigs_raw=raw_hconfigs,
        user_agent=user_agent,
        user_agent_parsed=user_agent_parsed,
        path=normalized_path,
        tag=tag or str((proxy_data or {}).get("tag") or ""),
        ipv4=ip or None,
    )
    if proxy_data and not proxy_row:
        base_proxy = client_ctx.proxy
        updates: dict[str, Any] = {}
        if proxy_data.get("mode"):
            updates["mode"] = proxy_data["mode"]
        if proxy_data.get("tag"):
            updates["tag"] = proxy_data["tag"]
        if proxy_data.get("tcp_ports"):
            updates["tcp_ports"] = list(proxy_data["tcp_ports"])
        if proxy_data.get("udp_ports"):
            updates["udp_ports"] = list(proxy_data["udp_ports"])
        if proxy_data.get("path"):
            updates["path"] = normalize_custom_path(proxy_data["path"])
        if updates:
            client_ctx = client_ctx.model_copy(update={"proxy": base_proxy.model_copy(update=updates)})

    users = _normalize_template_users(users, user_db or user)
    ctx: dict[str, Any] = {
        **client_ctx.to_dict(),
        "hconfigs": hconfigs,
        "users": users,
        "child_id": child_id,
        "fake_ip_for_sub_link": datetime.datetime.now().strftime("%H.%M--%Y.%m.%d.time:%H%M"),
        "skip": skip_proxy,
        "enumerate": enumerate,
        "include_path": include_path,
        "jsbool": jsbool,
    }
    if server_side:
        from hiddifypanel.models import Domain

        cache = ProxyRenderCache.load(child_id)
        domain_ids = [int(item["id"]) for item in cache.domains if item.get("id")]
        by_id = {row.id: row for row in Domain.query.filter(Domain.id.in_(domain_ids)).all()} if domain_ids else {}
        server_domains = [
            DomainIPVar.from_domain(by_id[int(item["id"])], raw_hconfigs)
            for item in cache.domains
            if item.get("id") and int(item["id"]) in by_id
        ]
        server_ctx = build_server_context(
            hconfigs_raw=raw_hconfigs,
            domains=server_domains,
            custom_proxies=cache.proxies,
            ips_v4=cache.ips_v4,
            ips_v6=cache.ips_v6,
        )
        ctx.update(server_ctx.to_dict())
    else:
        proxy_id = client_ctx.proxy.id or (proxy_data or {}).get("id")
        if proxy_id:
            domains = client_domain_vars_for_proxy(child_id, int(proxy_id))
        elif client_ctx.domain.name:
            domains = [client_ctx.domain]
        else:
            domains = []
        ctx["domains"] = domains
        client_ctx = client_ctx.model_copy(update={"domains": domains})
        ctx.update({"domain": client_ctx.domain})

    return ctx


def jsbool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "y", "on")
    if isinstance(value, str) and value.lower() in ("false", "0", "no", "n", "off"):
        return False
    return bool(value)
