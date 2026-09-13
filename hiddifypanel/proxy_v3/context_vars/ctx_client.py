from __future__ import annotations

from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict, Field

from hiddifypanel.models import FakeMode
from hiddifypanel.models.custom_proxy import CustomProxyMode, CustomProxyTransport, L7Proto, ProxyProto, TlsLayer
from hiddifypanel.proxy_v3.context_vars.ip import IPVar

from .cert import CertVar
from .domain import DomainIPVar, expand_sni_domain_servers
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
    shared_cert: CertVar = Field(default_factory=CertVar.empty)
    client_proxy_tags: list[str] = Field(default_factory=list)

    def iter_ctx_domains(self) -> Iterator[ClientContextDomainVar]:
        domains = [domain for domain in self.proxy.domains if _client_domain_allowed(domain, self.proxy)]
        domains = expand_client_domains(self.proxy, domains)
        for domain in domains:
            yield ClientContextDomainVar(
                user=self.user,
                hconfig=self.hconfig,
                platform=self.platform,
                proxy=self.proxy.with_domain(domain),
                shared_cert=self.shared_cert,
                client_proxy_tags=list(self.client_proxy_tags),
            )


class ClientContextDomainVar(ClientContextVar):
    """Client context bound to one domain (``ctx.proxy.domain``)."""

    proxy: ClientProxyDomainVar


def _client_domain_allowed(domain: DomainIPVar, proxy: ClientBuilderProxyVar) -> bool:
    if domain.is_sub_link_only():
        return False

    if domain.is_reality() and not is_reality_domain_valid(domain, proxy):
        return False
    if domain.download and domain.download.is_reality() and not (is_reality_domain_valid(domain.download, proxy) and is_reality_download_valid(proxy)):
        return False

    return True


def expand_client_domains(proxy: ClientBuilderProxyVar, domains: list[DomainIPVar]) -> list[DomainIPVar]:
    domains = [domain for domain in domains if not domain.is_sub_link_only()]
    if proxy.mode == CustomProxyMode.no_inbound:
        return domains
    if proxy.mode == CustomProxyMode.ip:
        return _unique_ip_mode_domains(proxy, domains)
    expanded: list[DomainIPVar] = []
    for domain in domains:
        expanded.extend(expand_sni_domain_servers(domain))
    return expanded


def _ip_mode_domain_rank(domain: DomainIPVar) -> tuple[int, str]:
    if domain.fake_mode == FakeMode.reality:
        return (2, domain.name)
    if domain.fake_mode == FakeMode.fake:
        return (1, domain.name)
    return (0, domain.name)


def _unique_ip_mode_domains(proxy: ClientBuilderProxyVar, domains: list[DomainIPVar]) -> list[DomainIPVar]:
    """IP-mode clients connect by address:port; emit one entry per distinct IP.

    Domains with a bound ``server_domain`` keep that hostname and are not expanded.
    """
    unique: list[tuple[DomainIPVar, str]] = []
    seen: set[tuple[str, int]] = set()
    kept: list[DomainIPVar] = []
    for domain in sorted(domains, key=_ip_mode_domain_rank):
        if domain.has_server_domain:
            kept.append(domain)
            continue
        bound = proxy.with_domain(domain)
        port = int(bound.port or 0)
        candidates = [str(ip).strip() for ip in (domain.ips.ips if domain.ips else []) if str(ip).strip()]
        if not candidates:
            server = str(bound.server or "").strip()
            if server:
                candidates = [server]
        for ip in candidates:
            key = (ip, port)
            if key in seen:
                continue
            seen.add(key)
            unique.append((domain, ip))

    result: list[DomainIPVar] = list(kept)
    for domain, ip in unique:
        result.append(
            domain.model_copy(
                update={
                    "dst_server": ip,
                    "ips": IPVar.from_strings(ip),
                    "download": None,
                    "has_server_domain": False,
                }
            )
        )
    return result


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


def is_reality_download_valid(proxy: ClientBuilderProxyVar) -> bool:
    """xHTTP download REALITY cannot use QUIC or TLS H1; plain HTTP is allowed."""
    if proxy.transport != CustomProxyTransport.xhttp:
        return True
    layer = proxy.download_tls_layer if proxy.download_tls_layer is not None else proxy.tls_layer
    return layer not in (TlsLayer.quic_tls, TlsLayer.quic_tcp_tls, TlsLayer.tls_h1)
