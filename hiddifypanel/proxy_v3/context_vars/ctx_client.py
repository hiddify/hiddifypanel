from __future__ import annotations

from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict

from .domain import DomainIPVar
from .hconfig import HConfigVar
from .platform import PlatformVar
from .proxy import ClientBuilderProxyVar, ClientProxyDomainVar
from .user import UserVar


class ClientContextVar(BaseModel):
    """Typed client-side template context."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    user: UserVar
    hconfig: HConfigVar
    platform: PlatformVar
    proxy: ClientBuilderProxyVar
    # all_child_hconfigs: dict[int, HConfigVar] = Field(default_factory=dict)

    def iter_ctx_domains(self) -> Iterator[ClientContextDomainVar]:
        for domain in self.proxy.domains:
            yield ClientContextDomainVar(
                user=self.user,
                hconfig=self.hconfig,
                platform=self.platform,
                proxy=self.proxy.with_domain(domain),
            )

    # def iter_ctx_domain_alpns(self) -> Iterator[ClientContextDomainAlpnVar]:
    #     for ctxd in self.iter_ctx_domains():
    #         yield from ctxd.iter_ctx_domain_alpns()


class ClientContextDomainVar(ClientContextVar):
    """Client context bound to one domain."""

    proxy: ClientProxyDomainVar

    @property
    def domain(self) -> DomainIPVar:
        return self.proxy.domain

    # def iter_ctx_domain_alpns(self) -> Iterator[ClientContextDomainAlpnVar]:
    #     for alpn_proxy in self.proxy.iter_proxies_with_alpns():
    #         yield ClientContextDomainAlpnVar(
    #             user=self.user,
    #             domains=self.domains,
    #             hconfig=self.hconfig,
    #             platform=self.platform,
    #             proxy=alpn_proxy,
    #         )


# class ClientContextDomainAlpnVar(ClientContextDomainVar):
#     """Client context bound to one domain and ALPN variant."""

#     proxy: ProxyDomainAlpnVar
