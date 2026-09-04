from __future__ import annotations

from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict

from hiddifypanel.models.custom_proxy import L7Proto, TlsLayer, CustomProxyTransport, ProxyProto

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
        for domain in self.proxy.domains:
            if domain.is_reality() and not is_reality_domain_valid(domain, self.proxy):
                continue
            if domain.download and domain.download.is_reality() and not is_reality_domain_valid(domain.download, self.proxy):
                continue
            yield ClientContextDomainVar(
                user=self.user,
                hconfig=self.hconfig,
                platform=self.platform,
                proxy=self.proxy.with_domain(domain),
            )


class ClientContextDomainVar(ClientContextVar):
    """Client context bound to one domain (``ctx.proxy.domain``)."""

    proxy: ClientProxyDomainVar


# based on xtls documentation https://xtls.github.io/en/protocol/reality/ only vless and xhttp and grpc and raw is supported
def is_reality_domain_valid(domain: ClientProxyDomainVar, proxy: ClientBuilderProxyVar) -> bool:
    if domain.is_reality():
        if proxy.tls_layer in [TlsLayer.quic_tls, TlsLayer.http]:
            return False
        if proxy.transport not in [CustomProxyTransport.xhttp, CustomProxyTransport.grpc, CustomProxyTransport.tcp]:
            return False
        if proxy.l7_reverse_proto not in [L7Proto.h2] and proxy.transport in [CustomProxyTransport.xhttp]:
            return False

        if proxy.proto not in [ProxyProto.vless]:
            return False
    return True
