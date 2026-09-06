from __future__ import annotations

from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict, Field

from .cert import CertVar
from .domain import DomainIPVar
from .hconfig import HConfigVar
from .ip import IPVar
from .proxy import ProxyDomainVar, ServerBuilderProxyVar
from .server_platform_var import ServerPlatformVar
from .user import UserVar


class ServerContextVar(BaseModel):
    """Typed server-side template context."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    child_id: int = 0
    users: list[UserVar]
    inactive_users: list[UserVar]
    domains: list[DomainIPVar]
    hconfig: HConfigVar
    proxies: list[ServerBuilderProxyVar]
    ips: IPVar
    platform: ServerPlatformVar | None = None
    client_proxy_tags: list[str] = Field(default_factory=list)
    shared_cert: CertVar = Field(default_factory=CertVar.empty)

    def use_proxy(self, proxy: ServerBuilderProxyVar) -> ServerContextProxyVar:
        return ServerContextProxyVar(
            child_id=self.child_id,
            users=self.users,
            inactive_users=self.inactive_users,
            domains=proxy.domains,
            hconfig=self.hconfig,
            proxies=self.proxies,
            proxy=proxy,
            ips=self.ips,
            platform=self.platform,
            shared_cert=self.shared_cert,
        )


class ServerContextProxyVar(ServerContextVar):
    """Typed server-side template context."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    proxy: ServerBuilderProxyVar

    @property
    def domain(self) -> DomainIPVar | None:
        return self.domains[0] if self.domains else None

    def iter_ctx_domains(self) -> Iterator[ServerContextDomainVar]:
        for domain in self.proxy.domains:
            yield ServerContextDomainVar(
                child_id=self.child_id,
                users=self.users,
                inactive_users=self.inactive_users,
                domains=self.domains,
                hconfig=self.hconfig,
                proxy=self.proxy.with_domain(domain),
                proxies=self.proxies,
                ips=self.ips,
                platform=self.platform,
                shared_cert=self.shared_cert,
            )


class ServerContextDomainVar(ServerContextProxyVar):
    """Server context bound to one domain."""

    proxy: ProxyDomainVar

    @property
    def domain(self) -> DomainIPVar:
        return self.proxy.domain
