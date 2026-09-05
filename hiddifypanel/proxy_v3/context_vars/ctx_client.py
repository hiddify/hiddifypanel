from __future__ import annotations

from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict

from hiddifypanel.models import FakeMode
from hiddifypanel.models.custom_proxy import L7Proto, TlsLayer, CustomProxyTransport, ProxyProto, CustomProxyMode

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

    def iter_ctx_domains(self) -> Iterator[ClientContextDomainVar]:
        domains = [domain for domain in self.proxy.domains if _client_domain_allowed(domain, self.proxy)]
        if self.proxy.mode == CustomProxyMode.ip:
            domains = _unique_ip_mode_domains(self.proxy, domains)
        for domain in domains:
            yield ClientContextDomainVar(
                user=self.user,
                hconfig=self.hconfig,
                platform=self.platform,
                proxy=self.proxy.with_domain(domain),
            )


class ClientContextDomainVar(ClientContextVar):
    """Client context bound to one domain (``ctx.proxy.domain``)."""

    proxy: ClientProxyDomainVar


def _client_domain_allowed(domain: DomainIPVar, proxy: ClientBuilderProxyVar) -> bool:
    if domain.is_reality() and not is_reality_domain_valid(domain, proxy):
        return False
    if domain.download and domain.download.is_reality() and not is_reality_domain_valid(domain.download, proxy):
        return False
    return True


def _ip_mode_domain_rank(domain: DomainIPVar) -> tuple[int, str]:
    if domain.fake_mode == FakeMode.reality:
        return (2, domain.name)
    if domain.fake_mode == FakeMode.fake:
        return (1, domain.name)
    return (0, domain.name)


def _unique_ip_mode_domains(proxy: ClientBuilderProxyVar, domains: list[DomainIPVar]) -> list[DomainIPVar]:
    """IP-mode clients connect by address:port; keep one domain per endpoint."""
    unique: list[DomainIPVar] = []
    seen: set[tuple[str, int]] = set()
    for domain in sorted(domains, key=_ip_mode_domain_rank):
        bound = proxy.with_domain(domain)
        key = (bound.server, bound.port)
        if key in seen:
            continue
        seen.add(key)
        unique.append(domain)
    return unique


# based on xtls documentation https://xtls.github.io/en/protocol/reality/ only vless and xhttp and grpc and raw is supported
def is_reality_domain_valid(domain: ClientProxyDomainVar | DomainIPVar, proxy: ClientBuilderProxyVar) -> bool:
    if domain.is_reality():
        if proxy.tls_layer in [TlsLayer.quic_tls, TlsLayer.http]:
            return False
        if proxy.transport not in [CustomProxyTransport.xhttp, CustomProxyTransport.grpc, CustomProxyTransport.tcp]:
            return False
        if proxy.l7_reverse_proto not in [L7Proto.h2] and proxy.transport in [CustomProxyTransport.xhttp]:
            return False
        if proxy.mode != CustomProxyMode.domains_l7_gateway:
            return False
        if proxy.proto not in [ProxyProto.vless]:
            return False
    return True
