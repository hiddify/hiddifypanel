from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from hiddifypanel.models import DomainType, FakeMode
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
from .ports import normalize_port_list, ports_list_to_ranges, resolve_inbound_ports
from .version import TemplateVersion


class ConfigVar(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    core: TemplateCore
    version: TemplateVersion
    content: str = ""


class ProxyVar(BaseModel):
    """Base custom-proxy fields with resolved inbound ports for the current binding."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    id: int | None = None
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

    domains: list[DomainIPVar] = Field(default_factory=list)

    @property
    def uses_tls(self) -> bool:
        return self.tls_layer is None or self.tls_layer == TlsLayer.tls

    @property
    def download_uses_tls(self) -> bool:
        if self.download_tls_layer is not None:
            return self.download_tls_layer == TlsLayer.tls
        return self.uses_tls

    @property
    def tcp_port(self) -> int:
        return int(self.tcp_ports[0]) if self.tcp_ports else 0

    @property
    def udp_port(self) -> int:
        return int(self.udp_ports[0]) if self.udp_ports else 0

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
        mode: CustomProxyMode = proxy.mode  # type: ignore
        proxy_id = int(proxy.id or 0)
        tcp_udp = proxy.effective_server_tcp_udp()
        resolved = resolve_inbound_ports(
            mode,
            proxy_id,
            db_tcp_ports=db_tcp_ports,
            db_udp_ports=db_udp_ports,
            server_side=server_side,
            tcp_udp=tcp_udp,
        )
        return cls(
            id=proxy_id,
            mode=mode,
            tag=proxy.name or proxy.slug or "",  # type: ignore
            tcp_ports=list(resolved.tcp_ports),
            udp_ports=list(resolved.udp_ports),
            path=normalize_custom_path(proxy.custom_path),  # type: ignore
            tls_layer=proxy.tls_layer,  # type: ignore
            l7_reverse_proto=proxy.l7_reverse_proto,  # type: ignore
            download_tls_layer=proxy.download_tls_layer,  # type: ignore
            domain_modes=[str(m) for m in (proxy.domain_modes or [])],
            download_domain_modes=[str(m) for m in (proxy.download_domain_modes or [])],
            proto=proxy.effective_proto(),
            transport=proxy.transport or None,  # type: ignore
            db_tcp_ports=db_tcp_ports,
            db_udp_ports=db_udp_ports,
            tcp_udp=tcp_udp,  # type: ignore
            slug=proxy.slug or "",
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


class ProxyDomainVar(ProxyVar):
    domain: DomainIPVar

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
        if not self.tls_layer == TlsLayer.tls:
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
                core=proxy.server_core,  # type: ignore
                version=TemplateVersion(),
                content=proxy.effective_server_config_text(),
            ),
        )


class ClientProxyDomainVar(ClientBuilderProxyVar):
    """Proxy bound to a domain."""

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
        )
        return cls(
            domain=domain,
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
        if self.tls_layer != TlsLayer.tls:
            return False
        return self.domain.is_reality()
