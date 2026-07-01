from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hiddifypanel.models.custom_proxy import CustomProxy
    from hiddifypanel.models.domain import Domain
    from hiddifypanel.models.user import User

from .ctx_client import ClientContextVar
from .ctx_server import ServerContextVar
from .domain import DomainIPVar
from .hconfig import HConfigVar
from .ip import IPVar
from .platform import PlatformVar
from .proxy import ProxyVar
from .user import UserVar


def user_var(user: User | UserVar | None) -> UserVar:
    from hiddifypanel.models.user import User

    if user is None:
        return UserVar()
    if isinstance(user, UserVar):
        return user
    return UserVar.from_user(user)


def domain_var(
    domain: Domain | DomainIPVar | None,
    hconfigs: dict[str, Any] | None = None,
    *,
    port: int | None = None,
    ip: IPVar | None = None,
) -> DomainIPVar:
    from hiddifypanel.models.domain import Domain

    if domain is None:
        return DomainIPVar()
    if isinstance(domain, DomainIPVar):
        return domain
    return DomainIPVar.from_domain(
        domain,
        hconfigs or {},
        ip=ip or IPVar.empty(),
        port=port,
    )


def hconfig_var(raw: dict[str, Any] | None = None, *, server_side: bool = False) -> HConfigVar:
    return HConfigVar(raw, server_side=server_side)


def platform_var(ua: str | None = None, parsed: dict[str, Any] | None = None) -> PlatformVar:
    return PlatformVar.from_user_agent(ua, parsed)


def ip_var(
    *,
    ipv4: str | list[str] | None = None,
    ipv6: str | list[str] | None = None,
    ips: list[str] | tuple[str, ...] | IPVar | None = None,
) -> IPVar:
    if isinstance(ips, IPVar):
        return ips
    if ips:
        return IPVar.from_mixed(list(ips)).merge(IPVar.from_strings(ipv4=ipv4, ipv6=ipv6))
    return IPVar.from_strings(ipv4=ipv4, ipv6=ipv6)


def reality_public_key(hconfig: HConfigVar) -> str:
    return str(hconfig.get("reality_public_key") or "")


def proxy_var(
    proxy: CustomProxy | ProxyVar | None,
    hconfig: HConfigVar,
    *,
    path: str | None = None,
    tag: str | None = None,
) -> ProxyVar:
    from hiddifypanel.models.custom_proxy import CustomProxy

    if proxy is None:
        return ProxyVar()
    if isinstance(proxy, ProxyVar):
        return proxy
    return ProxyVar.from_custom_proxy(proxy, hconfig, tag=tag)


def build_client_context(
    *,
    user: User | UserVar | None = None,
    domain: Domain | DomainIPVar | None = None,
    domains: list[DomainIPVar] | None = None,
    proxy: CustomProxy | ProxyVar | None = None,
    hconfigs_raw: dict[str, Any] | None = None,
    user_agent: str | None = None,
    user_agent_parsed: dict[str, Any] | None = None,
    path: str | None = None,
    tag: str | None = None,
    ip: IPVar | None = None,
) -> ClientContextVar:
    """Build typed client-side template roots."""
    hconfig = hconfig_var(hconfigs_raw, server_side=False)
    domain_var_ = domain_var(domain, hconfigs_raw, ip=ip_)
    domain_list = list(domains or [])
    if domain_var_.name and all(d.name != domain_var_.name for d in domain_list):
        domain_list.insert(0, domain_var_)
    elif not domain_list:
        domain_list = [domain_var_]
    platform = platform_var(user_agent, user_agent_parsed)
    user_var_ = user_var(user)
    proxy_var_ = proxy_var(proxy, hconfig, path=path, tag=tag)
    return ClientContextVar(
        user=user_var_,
        domains=domain_list,
        hconfig=hconfig,
        platform=platform,
        proxy=proxy_var_,
    )


def build_server_context(
    *,
    hconfigs_raw: dict[str, Any] | None = None,
    users: list[UserVar] | None = None,
    domains: list[DomainIPVar] | None = None,
    proxies: list[ProxyVar] | None = None,
    custom_proxies: list[dict[str, Any]] | None = None,
    ip: IPVar | None = None,
    ips_v4: list[dict[str, Any]] | None = None,
    ips_v6: list[dict[str, Any]] | None = None,
) -> ServerContextVar:
    """Build typed server-side template roots."""
    hconfig = hconfig_var(hconfigs_raw, server_side=True)
    ip_ = ip or IPVar.empty()
    if ips_v4 or ips_v6:
        ip_ = ip_.merge(IPVar.from_server_records(ips_v4, ips_v6))
    return ServerContextVar(
        users=list(users or []),
        domains=list(domains or []),
        hconfig=hconfig,
        proxies=list(proxies or []),
        custom_proxies=list(custom_proxies or []),
        ip=ip_,
        ips_v4=list(ips_v4 or []),
        ips_v6=list(ips_v6 or []),
    )


def build_var_context(
    *,
    user: User | UserVar | None = None,
    domain: Domain | DomainIPVar | None = None,
    proxy: CustomProxy | ProxyVar | None = None,
    hconfigs_raw: dict[str, Any] | None = None,
    user_agent: str | None = None,
    user_agent_parsed: dict[str, Any] | None = None,
    server_side: bool = False,
    path: str | None = None,
    tag: str | None = None,
    ip: IPVar | None = None,
) -> ClientContextVar | ServerContextVar:
    if server_side:
        return build_server_context(hconfigs_raw=hconfigs_raw, ip=ip)
    return build_client_context(
        user=user,
        domain=domain,
        proxy=proxy,
        hconfigs_raw=hconfigs_raw,
        user_agent=user_agent,
        user_agent_parsed=user_agent_parsed,
        path=path,
        tag=tag,
        ip=ip,
    )
