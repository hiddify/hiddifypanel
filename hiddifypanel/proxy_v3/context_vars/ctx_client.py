from __future__ import annotations

from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict, Field

from hiddifypanel.models.config_enum import ConfigEnum
from hiddifypanel.models.proxy import ProxyProto

from .domain import DomainIPVar
from .hconfig import HConfigVar
from .platform import PlatformVar
from .proxy import ProxyDomainAlpnVar, ProxyDomainVar, ProxyVar
from .user import UserVar


class ClientContextVar(BaseModel):
    """Typed client-side template context."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    user: UserVar = Field(default_factory=UserVar)
    domains: list[DomainIPVar] = Field(default_factory=list)
    hconfig: HConfigVar = Field(default_factory=lambda: HConfigVar())
    platform: PlatformVar = Field(default_factory=PlatformVar)
    proxy: ProxyVar = Field(default_factory=ProxyVar)

    def iter_ctx_domains(self) -> Iterator[ClientContextDomainVar]:
        for domain in self.domains:
            yield ClientContextDomainVar(
                user=self.user,
                domains=self.domains,
                hconfig=self.hconfig,
                platform=self.platform,
                proxy=self.proxy.with_domain(domain),
            )

    def iter_ctx_domain_alpns(self) -> Iterator[ClientContextDomainAlpnVar]:
        for ctxd in self.iter_ctx_domains():
            yield from ctxd.iter_ctx_domain_alpns()


class ClientContextDomainVar(ClientContextVar):
    """Client context bound to one domain."""

    proxy: ProxyDomainVar

    @property
    def domain(self) -> DomainIPVar:
        return self.proxy.domain

    def iter_ctx_domain_alpns(self) -> Iterator[ClientContextDomainAlpnVar]:
        for alpn_proxy in self.proxy.iter_proxies_with_alpns():
            yield ClientContextDomainAlpnVar(
                user=self.user,
                domains=self.domains,
                hconfig=self.hconfig,
                platform=self.platform,
                proxy=alpn_proxy,
            )


class ClientContextDomainAlpnVar(ClientContextDomainVar):
    """Client context bound to one domain and ALPN variant."""

    proxy: ProxyDomainAlpnVar


protocl_config_map = {
    ProxyProto.vless: ConfigEnum.vless_enable,
    ProxyProto.trojan: ConfigEnum.trojan_enable,
    ProxyProto.vmess: ConfigEnum.vmess_enable,
    ProxyProto.ss: ConfigEnum.shadowsocks2022_enable,
    ProxyProto.v2ray: ConfigEnum.v2ray_enable,
    ProxyProto.ssr: ConfigEnum.ssr_enable,
    ProxyProto.ssh: ConfigEnum.ssh_server_enable,
    ProxyProto.tuic: ConfigEnum.tuic_enable,
    ProxyProto.hysteria: ConfigEnum.hysteria_enable,
    ProxyProto.hysteria2: ConfigEnum.hysteria_enable,
    ProxyProto.wireguard: ConfigEnum.wireguard_enable,
    ProxyProto.naive: ConfigEnum.naive_enable,
    ProxyProto.mieru: ConfigEnum.mieru_enable,
    ProxyProto.anytls: ConfigEnum.anytls_enable,
    ProxyProto.dnstt: ConfigEnum.dnstt_enable,
}


def filter_proxy(proxy: ProxyVar, hconfig: HConfigVar) -> ProxyVar | None:
    if not hconfig.get(protocl_config_map[proxy.proto]):
        return None
    return proxy
