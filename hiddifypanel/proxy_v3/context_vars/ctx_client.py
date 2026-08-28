from __future__ import annotations

from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict

from hiddifypanel.models.custom_proxy import TlsLayer

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
            if domain.is_reality() and self.proxy.tls_layer in [TlsLayer.quic_tls, TlsLayer.http]:
                # logger.warning(f"Domain {domain.domain} is reality but proxy {self.proxy.slug} is using quic_tls")
                continue
            if domain.download and domain.download.is_reality() and self.proxy.download_tls_layer in [TlsLayer.quic_tls, TlsLayer.http]:
                # logger.warning(f"Domain {domain.domain} is reality but proxy {self.proxy.slug} is using quic_tls")
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
