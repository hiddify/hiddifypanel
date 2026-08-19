from __future__ import annotations
from wcwidth import ljust
import os

from typing import Any

from hiddifypanel.models import ConfigEnum, Domain, DomainType, get_hconfigs
from hiddifypanel.models.custom_proxy import CustomProxyMode, normalize_custom_path
from hiddifypanel.models.user import User
from hiddifypanel.proxy_v3.context_vars.domain import DomainIPVar
from hiddifypanel.proxy_v3.context_vars.hconfig import HConfigVar
from hiddifypanel.proxy_v3.context_vars.ip import IPVar
from hiddifypanel.proxy_v3.context_vars.platform import PlatformVar
from hiddifypanel.proxy_v3.context_vars.proxy import ProxyVar
from hiddifypanel.proxy_v3.context_vars.user import UserVar

from .proxy_render_matrix import ProxyRenderCache, client_domain_vars_for_proxy


class TemplateSkip(Exception):
    """Raised when a template intentionally skips rendering (outputs SKIP)."""

    def __init__(self, reason: str = "") -> None:
        self.reason = reason or ""
        super().__init__(self.reason or "SKIP")


HIDDIFY_MANAGER_ROOT = "/opt/hiddify-manager"


class HconfigsAccessor(dict):
    """Legacy panel settings dict for templates that still read hconfigs."""

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, ConfigEnum):
            key = key.name
        return super().get(str(key))

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return self.get(name)

    def get(self, key: Any, default: Any = None) -> Any:  # type: ignore[override]
        if isinstance(key, ConfigEnum):
            key = key.name
        return super().get(str(key), default)


def _load_raw_hconfigs(child_id: int = 0) -> dict[str, Any]:
    try:
        raw = get_hconfigs(child_id)
        return {(getattr(k, "name", None) or str(k)): v for k, v in raw.items()}
    except RuntimeError:
        return {}


def _wrap_hconfigs(raw: dict[str, Any]) -> HconfigsAccessor:
    return HconfigsAccessor(raw)


def _user_var(user: User | UserVar | dict[str, Any] | None) -> UserVar:
    if isinstance(user, UserVar):
        return user
    if isinstance(user, User):
        return UserVar.from_user(user)
    if isinstance(user, dict):
        uuid = str(user.get("uuid") or "")
        return UserVar(
            uuid=uuid,
            uuid_hex=uuid.replace("-", ""),
            name=str(user.get("name") or ""),
            username=str(user.get("username") or user.get("name") or ""),
            id=user.get("id"),
            lang=str(user.get("lang") or ""),
            enable=bool(user.get("enable", True)),
            is_active=bool(user.get("is_active", True)),
            ed25519_public_key=str(user.get("ed25519_public_key") or ""),
            ed25519_private_key=str(user.get("ed25519_private_key") or ""),
            wg_pk=str(user.get("wg_pk") or ""),
            wg_pub=str(user.get("wg_pub") or ""),
            wg_psk=str(user.get("wg_psk") or ""),
        )
    return UserVar()


def _domain_type(value: Any) -> DomainType:
    if isinstance(value, DomainType):
        return value
    try:
        return DomainType(str(value or "direct"))
    except ValueError:
        return DomainType.direct


def _resolve_domain(
    child_id: int,
    domain_data: dict[str, Any] | None,
    *,
    ip: str = "",
) -> DomainIPVar:
    domain_db: Domain | None = None
    if domain_data:
        domain_id = domain_data.get("id") or domain_data.get("domain_id")
        if domain_id is not None:
            domain_db = Domain.query.filter(Domain.id == int(domain_id), Domain.child_id == child_id).first()
        if domain_db is None:
            host = domain_data.get("name") or domain_data.get("domain")
            if host:
                domain_db = Domain.query.filter(
                    Domain.child_id == child_id,
                    Domain.domain == str(host).strip().lower(),
                ).first()
    if domain_db is not None:
        return DomainIPVar.from_domain(domain_db)

    data = domain_data or {}
    name = str(data.get("name") or data.get("domain") or "example.com").lower()
    server = str(data.get("server") or ip or name)
    return DomainIPVar(
        id=data.get("id"),
        name=name,
        host=str(data.get("host") or name),
        sni=str(data.get("sni") or name),
        port=int(data.get("port") or 443),
        mode=_domain_type(data.get("mode")),
        alias=str(data.get("alias") or ""),
        child_id=int(data.get("child_id") or child_id),
        ips=IPVar.from_strings(server, str(data.get("ipv6") or "")),
    )


def _proxy_var(
    proxy_data: dict[str, Any] | None,
    *,
    tag: str,
    port: int,
    custom_path: str,
) -> ProxyVar:
    data = dict(proxy_data or {})
    data.setdefault("tag", tag)
    data.setdefault("port", port)
    data["path"] = normalize_custom_path(str(data.get("path") or custom_path or ""))
    mode = data.get("mode")
    if isinstance(mode, str):
        try:
            data["mode"] = CustomProxyMode(mode)
        except ValueError:
            data.pop("mode", None)
    return ProxyVar.model_validate(data)


def _chown_generated_path(path: str) -> None:
    """Make dump sidecars writable by the panel even if this process is root."""
    try:
        os.chmod(path, 0o775 if os.path.isdir(path) else 0o640)
    except OSError:
        pass
    if os.geteuid() != 0:
        return
    try:
        import grp
        import pwd

        uid = pwd.getpwnam("hiddify-panel").pw_uid
        gid = grp.getgrnam("hiddify-common").gr_gid
        os.chown(path, uid, gid)
    except (KeyError, OSError):
        pass


def include_path(ctx: Any, slug: str, prefix: str = "include/") -> str:
    """Render a template slug to a sidecar file and return its deployed absolute path."""
    rel = (slug or "").strip().lstrip("/")
    if not rel:
        raise ValueError("slug is required")

    rel_prefix = (prefix or "include/").strip().strip("/")
    rel = f"{rel_prefix}/{rel}" if rel_prefix else rel
    abs_path = f"{HIDDIFY_MANAGER_ROOT}/generated/{rel}"
    parent_dir = os.path.dirname(abs_path)
    if parent_dir:
        os.makedirs(parent_dir, mode=0o775, exist_ok=True)
        _chown_generated_path(parent_dir)

    from hiddifypanel.proxy_v3.config_builder.jinja_render import render_slug_template

    rendered = render_slug_template(slug, 0, {"ctx": ctx})
    try:
        with open(abs_path, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    except PermissionError:
        # Directory may be writable even if a leftover root-owned file is not.
        os.unlink(abs_path)
        with open(abs_path, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    _chown_generated_path(abs_path)
    return abs_path


def skip_proxy(reason: Any = "") -> str:
    """Jinja callable — also used by {{ skip() if cond }}."""
    raise TemplateSkip(str(reason) if reason else "")


def jsbool(value: Any) -> str:
    """Return JSON boolean literals for embedding in config templates."""
    if isinstance(value, bool):
        truthy = value
    elif isinstance(value, (int, float)):
        truthy = bool(value)
    elif isinstance(value, str):
        lowered = value.lower()
        if lowered in ("false", "0", "no", "n", "off", ""):
            truthy = False
        elif lowered in ("true", "1", "yes", "y", "on"):
            truthy = True
        else:
            truthy = bool(value.strip())
    else:
        truthy = bool(value)
    return "true" if truthy else "false"


class RenderContextAdapter:
    """Expose dict template context with typed-style ``iter_ctx_domains()``."""

    def __init__(self, data: dict[str, Any]) -> None:
        object.__setattr__(self, "_data", data)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._data[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_data":
            object.__setattr__(self, name, value)
            return
        self._data[name] = value

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def iter_ctx_domains(self):
        proxy = self._data.get("proxy")
        domains = list(self._data.get("domains") or [])
        if not domains and self._data.get("domain") is not None:
            domains = [self._data["domain"]]
        for domain in domains:
            child = dict(self._data)
            child["domain"] = domain
            if proxy is not None and hasattr(proxy, "with_domain"):
                child["proxy"] = proxy.with_domain(domain)
            yield RenderContextAdapter(child)

    def iter_ctx_domain(self):
        return self.iter_ctx_domains()


def build_template_context(
    child_id: int = 0,
    *,
    user: User | UserVar | dict[str, Any] | None = None,
    domain_data: dict[str, Any] | None = None,
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
    del domain_binding, user_agent_parsed  # kept for caller compatibility

    raw_hconfigs = _load_raw_hconfigs(child_id)
    hconfig = HConfigVar(raw_hconfigs, server_side=server_side)
    user_var = _user_var(user)
    platform = PlatformVar.from_user_agent(user_agent or "")
    domain_var = _resolve_domain(child_id, domain_data, ip=ip)
    proxy_var = _proxy_var(proxy_data, tag=tag, port=port, custom_path=custom_path)

    ctx: dict[str, Any] = {
        "user": user_var,
        "domain": domain_var,
        "hconfig": hconfig,
        "platform": platform,
        "proxy": proxy_var,
        "users": list(users or []),
        "hconfigs": _wrap_hconfigs(raw_hconfigs),
        "child_id": child_id,
        "custom_path": normalize_custom_path(custom_path),
        "port": port,
        "tag": tag,
        "skip": skip_proxy,
        "enumerate": enumerate,
        "include_path": include_path,
        "jsbool": jsbool,
        "ConfigEnum": ConfigEnum,
        "ljust": ljust,
    }

    if server_side:
        cache = ProxyRenderCache.load(child_id)
        domain_ids = [int(item["id"]) for item in cache.domains if item.get("id")]
        by_id = {row.id: row for row in Domain.query.filter(Domain.id.in_(domain_ids)).all()} if domain_ids else {}
        ctx["domains"] = [DomainIPVar.from_domain(by_id[did]) for did in domain_ids if did in by_id]
        ctx["custom_proxies"] = cache.proxies
        ctx["ips_v4"] = cache.ips_v4
        ctx["ips_v6"] = cache.ips_v6
    else:
        proxy_id = (proxy_data or {}).get("id")
        if proxy_id:
            ctx["domains"] = client_domain_vars_for_proxy(child_id, int(proxy_id))
        elif domain_var.name:
            ctx["domains"] = [domain_var]
        else:
            ctx["domains"] = []

    if hasattr(proxy_var, "domains"):
        proxy_var.domains = list(ctx["domains"])

    return {
        "ctx": RenderContextAdapter(ctx),
        "skip": skip_proxy,
        "enumerate": enumerate,
        "include_path": include_path,
        "jsbool": jsbool,
        "ConfigEnum": ConfigEnum,
    }
