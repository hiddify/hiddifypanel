from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from hiddifypanel.models.custom_proxy import CustomProxyMode, normalize_custom_path
from hiddifypanel.models.proxy import ProxyProto

if TYPE_CHECKING:
    from hiddifypanel.models.custom_proxy import CustomProxy

from ..alpn_helpers import (
    AlpnTags,
    resolve_alpn_tags,
)
from .domain import DomainIPVar
from .hconfig import HConfigVar


class ProxyVar(BaseModel):
    """Base custom-proxy fields before domain / ALPN resolution."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    id: int | None = None
    mode: CustomProxyMode = CustomProxyMode.domains_l7_gateway
    tag: str = ""
    tcp_ports: list[int] = Field(default_factory=list)
    udp_ports: list[int] = Field(default_factory=list)
    path: str = ""
    availble_alpns: list[AlpnTags] = Field(default_factory=list)
    availble_download_alpns: list[AlpnTags] = Field(default_factory=list)
    proto: ProxyProto = ProxyProto.vless

    @property
    def tcp_port(self) -> int:
        return int(self.tcp_ports[0]) if self.tcp_ports else 0

    @property
    def udp_port(self) -> int:
        return int(self.udp_ports[0]) if self.udp_ports else 0

    @property
    def tcp_port_ranges(self) -> list[int | str]:
        from ..custom_proxy_ports import ports_list_to_ranges

        return ports_list_to_ranges(list(self.tcp_ports))

    @property
    def udp_port_ranges(self) -> list[int | str]:
        from ..custom_proxy_ports import ports_list_to_ranges

        return ports_list_to_ranges(list(self.udp_ports))

    @classmethod
    def from_custom_proxy(
        cls,
        proxy: CustomProxy,
        hconfig: HConfigVar,
        *,
        tag: str | None = None,
    ) -> ProxyVar:
        from hiddifypanel.models.custom_proxy import CustomProxy
        from ..custom_proxy_ports import normalize_port_list

        mode: CustomProxyMode = proxy.mode  # type: ignore
        tcp_ports = normalize_port_list(proxy.server_inbound_tcp_ports)
        udp_ports = normalize_port_list(proxy.server_inbound_udp_ports)
        proto: ProxyProto = proxy.proto  # type: ignore
        alpn_tags = resolve_alpn_tags(proxy.alpns, hconfig, proto)  # type: ignore
        download_tags = resolve_alpn_tags(proxy.download_alpns, hconfig, proto)  # type: ignore
        path = normalize_custom_path(proxy.custom_path)  # type: ignore
        return cls(
            id=proxy.id or 0,  # type: ignore
            mode=mode,
            tag=tag or "",
            tcp_ports=tcp_ports,
            udp_ports=udp_ports,
            path=path,
            availble_alpns=alpn_tags,
            availble_download_alpns=download_tags,
        )

    def direct_port_access(self) -> bool:
        return self.mode.direct_port_access()

    def iter_proxies_with_domain(self, domains: list[DomainIPVar]) -> Iterator[ProxyDomainVar]:
        for domain in domains:
            yield self.with_domain(domain)

    def with_domain(self, domain: DomainIPVar) -> ProxyDomainVar:
        return ProxyDomainVar.from_proxy(self, domain)


class ProxyDomainVar(ProxyVar):
    """Proxy bound to a domain (before ALPN variant selection)."""

    def __init__(self, domain: DomainIPVar, **data: Any):
        super().__init__(**data)
        self.domain = domain
        from ..custom_proxy_ports import resolve_inbound_ports

        resolved = resolve_inbound_ports(
            self.mode,
            int(self.id or 0),
            domain_id=domain.id,
            stored_tcp_ports=list(self.tcp_ports),
            stored_udp_ports=list(self.udp_ports),
        )
        self.tcp_ports = resolved.tcp_ports
        self.udp_ports = resolved.udp_ports

    domain: DomainIPVar = Field(default_factory=DomainIPVar)
    extra: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_proxy(cls, proxy: ProxyVar, domain: DomainIPVar) -> ProxyDomainVar:
        return cls(domain=domain, **proxy.model_dump())

    @property
    def server(self) -> str:
        if self.mode == CustomProxyMode.ip:
            return self.domain.ip or self.domain.ipv4 or self.domain.server or self.domain.name
        return self.domain.server or self.domain.name

    def iter_proxies_with_alpns(self) -> Iterator[ProxyDomainAlpnVar]:
        for alpn in self.availble_alpns:
            for download_alpn in self.availble_download_alpns or [None]:
                yield self.with_alpn(alpn, download_alpn)

    def with_alpn(self, alpn_tag: Any, download_alpn_tag: Any = None) -> ProxyDomainAlpnVar:
        return ProxyDomainAlpnVar.from_domain_proxy(self, alpn_tag, download_alpn_tag)


class ProxyDomainAlpnVar(ProxyDomainVar):
    """Proxy bound to a domain with a concrete ALPN variant."""

    alpn: AlpnTags
    download_alpn: AlpnTags | None = None

    @classmethod
    def from_domain_proxy(
        cls,
        base: ProxyDomainVar,
        alpn_tag: AlpnTags,
        download_alpn_tag: AlpnTags | None = None,
    ) -> ProxyDomainAlpnVar:
        base_data = base.model_dump()
        return cls(alpn=alpn_tag, download_alpn=download_alpn_tag, **base_data)
