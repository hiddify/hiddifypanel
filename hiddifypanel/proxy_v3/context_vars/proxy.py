from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from hiddifypanel.models import DomainType
from hiddifypanel.models.custom_proxy import (
    CustomProxyMode,
    CustomProxyTransport,
    InboundTcpUdp,
    L7Proto,
    TlsLayer,
    normalize_custom_path,
)
from hiddifypanel.models.proxy import ProxyProto

if TYPE_CHECKING:
    from hiddifypanel.models.custom_proxy import CustomProxy

from hiddifypanel.models.custom_proxy import TemplateCore

from .domain import DomainIPVar
from .hconfig import HConfigVar
from .ports import gateway_client_port, normalize_port_list, ports_list_to_ranges, resolve_inbound_ports
from .version import TemplateVersion



_REALITY_TLS_LAYERS: frozenset[TlsLayer] = frozenset({TlsLayer.tls, TlsLayer.tls_h2})


def _tls_layer_allows_reality(transport: CustomProxyTransport, tls_layer: TlsLayer | None) -> bool:
    """TLS layers a REALITY domain can carry: TLS/TLS-h2, and TLS-h1 for raw HTTP (rawhttp)
    (see domain_mode_filter.transport_tls_supports_reality, which offers these domain modes)."""
    if tls_layer in _REALITY_TLS_LAYERS:
        return True
    return tls_layer == TlsLayer.tls_h1 and transport == CustomProxyTransport.http

class ConfigVar(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    core: TemplateCore
    version: TemplateVersion
    content: str = ""


class ProxyVar(BaseModel):
    """Base custom-proxy fields with resolved inbound ports for the current binding."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    id: int = 0
    mode: CustomProxyMode = CustomProxyMode.domains_l7_gateway
    slug: str = ""
    tag: str = ""
    tcp_ports: list[int] = Field(default_factory=list)
    udp_ports: list[int] = Field(default_factory=list)
    path: str = ""

    proto: ProxyProto = ProxyProto.vless
    transport: CustomProxyTransport = CustomProxyTransport.tcp
    l7_reverse_proto: L7Proto | None = None

    db_tcp_ports: list[int] = Field(default_factory=list)
    db_udp_ports: list[int] = Field(default_factory=list)
    tcp_udp: InboundTcpUdp = InboundTcpUdp.both

    tls_layer: TlsLayer | None = None
    download_tls_layer: TlsLayer | None = None

    domain_modes: list[str] = Field(default_factory=list)
    download_domain_modes: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    is_common_proxy: bool = False
    server_core: str = ""

    domains: list[DomainIPVar] = Field(default_factory=list)

    def effective_tls_layer(self) -> TlsLayer:
        """A missing layer is plain HTTP. There is no null TLS layer."""
        return self.tls_layer or TlsLayer.http

    def effective_download_tls_layer(self) -> TlsLayer:
        """Unset download layer follows the upload layer."""
        return self.download_tls_layer or self.effective_tls_layer()

    @property
    def uses_tls(self) -> bool:
        return self.effective_tls_layer() != TlsLayer.http

    @property
    def download_uses_tls(self) -> bool:
        return self.effective_download_tls_layer() != TlsLayer.http

    @property
    def download_port(self) -> int:
        if self.mode == CustomProxyMode.domains_l7_gateway:
            return gateway_client_port(self.effective_download_tls_layer())
        return self.tcp_port or self.udp_port

    @property
    def tcp_port(self) -> int:
        return int(self.tcp_ports[0]) if self.tcp_ports else 0

    @property
    def udp_port(self) -> int:
        return int(self.udp_ports[0]) if self.udp_ports else 0

    @property
    def port(self) -> int:
        return self.tcp_port or self.udp_port

    @property
    def tcp_port_ranges(self) -> list[int | str]:
        return ports_list_to_ranges(list(self.tcp_ports))

    @property
    def udp_port_ranges(self) -> list[int | str]:
        return ports_list_to_ranges(list(self.udp_ports))

    @property
    def public_access(self) -> bool:
        return self.direct_port_access()

    @classmethod
    def from_custom_proxy(cls, proxy: CustomProxy, hconfig: HConfigVar, *, server_side: bool = True) -> ProxyVar:

        db_tcp_ports = normalize_port_list(proxy.server_inbound_tcp_ports)
        db_udp_ports = normalize_port_list(proxy.server_inbound_udp_ports)
        mode: CustomProxyMode = proxy.mode
        proxy_id = int(proxy.id or 0)
        tcp_udp = proxy.effective_server_tcp_udp()
        resolved = resolve_inbound_ports(
            mode,
            proxy_id,
            db_tcp_ports=db_tcp_ports,
            db_udp_ports=db_udp_ports,
            server_side=server_side,
            tcp_udp=tcp_udp,
            tls_layer=proxy.tls_layer,
        )
        return cls(
            id=proxy_id,
            mode=mode,
            tag=proxy.name or proxy.slug or "",
            tcp_ports=list(resolved.tcp_ports),
            udp_ports=list(resolved.udp_ports),
            path=normalize_custom_path(proxy.custom_path),
            tls_layer=proxy.tls_layer or TlsLayer.http,
            l7_reverse_proto=proxy.l7_reverse_proto,
            download_tls_layer=proxy.download_tls_layer,
            domain_modes=[str(m) for m in (proxy.domain_modes or [])],
            download_domain_modes=[str(m) for m in (proxy.download_domain_modes or [])],
            categories=[str(c) for c in (proxy.categories or [])],
            proto=proxy.proto,
            transport=proxy.transport or None,
            db_tcp_ports=db_tcp_ports,
            db_udp_ports=db_udp_ports,
            tcp_udp=tcp_udp,
            slug=proxy.slug or "",
            is_common_proxy=bool(proxy.is_common_proxy),
            server_core=proxy.server_core.value if proxy.server_core else "",
        )

    def direct_port_access(self) -> bool:
        return self.mode.direct_port_access()

    def iter_proxies_with_domain(self) -> Iterator[ProxyDomainVar]:
        for domain in self.domains:
            yield self.with_domain(domain)

    def with_domain(self, domain: DomainIPVar) -> ProxyDomainVar:
        return ProxyDomainVar.from_proxy(self, domain)


def resolve_domain_type(domain_mode: str) -> DomainType:
    try:
        return DomainType(domain_mode)
    except ValueError as exc:
        raise ValueError(f"Invalid domain mode: {domain_mode}") from exc


def _l7_client_domain_ports(domain: DomainIPVar, proxy: ProxyVar) -> DomainIPVar:
    if proxy.mode != CustomProxyMode.domains_l7_gateway:
        return domain
    upload_port = gateway_client_port(proxy.effective_tls_layer())
    download_layer = proxy.effective_download_tls_layer()
    download_port = gateway_client_port(download_layer)
    download = domain.download
    if download is not None:
        download = download.model_copy(update={"port": download_port, "download": None})
    return domain.model_copy(update={"port": upload_port, "download": download})


class ProxyDomainVar(ProxyVar):
    domain: DomainIPVar

    def is_download_upload_different(self) -> bool:
        if self.domain.download is None:
            return False
        if self.domain.download.name != self.domain.name:
            return True
        if self.effective_download_tls_layer() != self.effective_tls_layer():
            return True
        if self.domain.download.server() != self.domain.server():
            return True
        return False

    @classmethod
    def from_proxy(cls, proxy: ProxyVar, domain: DomainIPVar, *, server_side: bool = True) -> ProxyDomainVar:
        resolved = resolve_inbound_ports(
            proxy.mode,
            int(proxy.id or 0),
            domain_id=domain.id,
            db_tcp_ports=list(proxy.db_tcp_ports),
            db_udp_ports=list(proxy.db_udp_ports),
            server_side=server_side,
            tcp_udp=proxy.tcp_udp,
            tls_layer=proxy.tls_layer,
        )
        return cls(
            domain=domain,
            **proxy.model_dump(exclude={"domain", "server_config", "client_configs", "tcp_ports", "udp_ports", "domains"}),
            tcp_ports=list(resolved.tcp_ports),
            udp_ports=list(resolved.udp_ports),
        )

    @property
    def server(self) -> str:
        return self.domain.server()
        # return self.domain.server(self.mode == CustomProxyMode.ip or self.domain.fake_mode != FakeMode.valid)

    @property
    def is_reality(self) -> bool:
        if self.proto not in {ProxyProto.vless, ProxyProto.trojan, ProxyProto.vmess}:
            return False
        if not _tls_layer_allows_reality(self.transport, self.tls_layer):
            return False
        if not self.domain.is_reality():
            return False
        return True


class ClientBuilderProxyVar(ProxyVar):
    client_configs: list[ConfigVar] = Field(default_factory=list)

    @classmethod
    def from_custom_proxy(cls, proxy: CustomProxy, hconfig: HConfigVar) -> ClientBuilderProxyVar:
        client_configs = [
            ConfigVar(
                core=TemplateCore(client_core.core.value),
                version=TemplateVersion(client_core.version),
                content=client_core.effective_outbounds_template(),
            )
            for client_core in proxy.client_cores
        ]
        base = ProxyVar.from_custom_proxy(proxy, hconfig, server_side=False)
        return cls(
            **base.model_dump(),
            client_configs=client_configs,
        )

    def with_domain(self, domain: DomainIPVar) -> ClientProxyDomainVar:
        return ClientProxyDomainVar.from_proxy(self, domain)


class ServerBuilderProxyVar(ProxyVar):
    server_config: ConfigVar

    @classmethod
    def from_custom_proxy(cls, proxy: CustomProxy, hconfig: HConfigVar) -> ServerBuilderProxyVar:
        base = ProxyVar.from_custom_proxy(proxy, hconfig, server_side=True)
        return cls(
            **base.model_dump(),
            server_config=ConfigVar(
                core=proxy.server_core,
                version=TemplateVersion(),
                content=proxy.effective_server_config_text(),
            ),
        )


class ClientProxyDomainVar(ClientBuilderProxyVar):
    """Proxy bound to a domain."""

    def is_download_upload_different(self) -> bool:
        if self.domain.download is None:
            return False
        if self.domain.download.name != self.domain.name:
            return True
        if self.effective_download_tls_layer() != self.effective_tls_layer():
            return True
        if self.domain.download.server() != self.domain.server():
            return True
        return False

    domain: DomainIPVar

    @classmethod
    def from_proxy(cls, proxy: ProxyVar, domain: DomainIPVar) -> ClientProxyDomainVar:
        resolved = resolve_inbound_ports(
            proxy.mode,
            int(proxy.id or 0),
            domain_id=domain.id,
            db_tcp_ports=list(proxy.db_tcp_ports),
            db_udp_ports=list(proxy.db_udp_ports),
            server_side=False,
            tcp_udp=proxy.tcp_udp,
            tls_layer=proxy.tls_layer,
        )
        return cls(
            domain=_l7_client_domain_ports(domain, proxy),
            **proxy.model_dump(exclude={"domain", "server_config", "tcp_ports", "udp_ports", "domains"}),
            tcp_ports=list(resolved.tcp_ports),
            udp_ports=list(resolved.udp_ports),
        )

    @property
    def server(self) -> str:
        return self.domain.server(self.mode == CustomProxyMode.ip)

    @property
    def is_reality(self) -> bool:
        if self.proto not in {ProxyProto.vless, ProxyProto.trojan, ProxyProto.vmess}:
            return False
        if not _tls_layer_allows_reality(self.transport, self.tls_layer):
            return False
        return self.domain.is_reality()
