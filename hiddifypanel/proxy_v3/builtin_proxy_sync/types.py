from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from hiddifypanel.models.custom_proxy import (
    CustomProxy,
    CustomProxyMode,
    InboundTcpUdp,
    normalize_custom_path,
)
from hiddifypanel.proxy_v3.custom_proxy_ports import normalize_port_list


@dataclass(frozen=True)
class PresetClientCore:
    core: str
    version: str
    slug: str
    outbounds_template: str
    is_builtin: bool = True


@dataclass(frozen=True)
class PresetServerConfig:
    core: str
    inbound_template: str
    template_slugs: tuple[str, ...]
    tag: str
    inbound_tcp_ports: tuple[int, ...] = ()
    inbound_udp_ports: tuple[int, ...] = ()
    sni_domains: tuple[str, ...] = ()


@dataclass(frozen=True)
class CustomProxyPreset:
    name: str
    slug: str
    enable: bool
    mode: CustomProxyMode
    proto: str
    transport: str
    tls_layer: str
    l7_reverse_proto: str | None
    categories: tuple[str, ...]
    domain_modes: tuple[str, ...]
    custom_path: str
    server_config: PresetServerConfig
    client_cores: tuple[PresetClientCore, ...]
    download_tls_layer: str | None = None
    download_domain_modes: tuple[str, ...] = ()
    sort_order: int = 0
    tcp_udp: InboundTcpUdp = InboundTcpUdp.both
    download_tcp_udp: InboundTcpUdp | None = None
    is_common_proxy: bool = False

    def snapshot(self) -> CustomProxySnapshot:
        return CustomProxySnapshot.from_preset(self)


@dataclass(frozen=True)
class ClientCoreSnapshot:
    core: str
    version: str
    slug: str
    outbounds_template: str

    @classmethod
    def from_preset_core(cls, item: PresetClientCore) -> ClientCoreSnapshot:
        return cls(
            core=item.core,
            version=item.version,
            slug=item.slug,
            outbounds_template=item.outbounds_template,
        )


@dataclass(frozen=True)
class CustomProxySnapshot:
    custom_path: str
    domain_modes: list[str]
    transport: str | None
    tls_layer: str | None
    l7_reverse_proto: str | None
    download_tls_layer: str | None
    download_domain_modes: list[str]
    server_core: str
    server_tag: str
    server_inbound_tcp_ports: list[int]
    server_inbound_udp_ports: list[int]
    server_inbound_tcp_udp: str
    server_config: str
    server_inbound_download_tcp_udp: str | None = None
    client_cores: tuple[ClientCoreSnapshot, ...] = field(default_factory=tuple)

    @classmethod
    def from_preset(cls, preset: CustomProxyPreset) -> CustomProxySnapshot:
        server = preset.server_config
        return cls(
            custom_path=normalize_custom_path(preset.custom_path),
            domain_modes=list(preset.domain_modes),
            transport=preset.transport or None,
            tls_layer=preset.tls_layer or None,
            l7_reverse_proto=preset.l7_reverse_proto,
            download_tls_layer=preset.download_tls_layer,
            download_domain_modes=list(preset.download_domain_modes),
            server_core=server.core,
            server_tag=server.tag,
            server_inbound_tcp_ports=list(server.inbound_tcp_ports),
            server_inbound_udp_ports=list(server.inbound_udp_ports),
            server_inbound_tcp_udp=preset.tcp_udp.value,
            server_inbound_download_tcp_udp=(preset.download_tcp_udp.value if preset.download_tcp_udp else None),
            server_config=server.inbound_template,
            client_cores=tuple(ClientCoreSnapshot.from_preset_core(cc) for cc in preset.client_cores),
        )

    @classmethod
    def from_row(cls, row: CustomProxy) -> CustomProxySnapshot:
        from hiddifypanel.proxy_v3.template_catalog.custom_proxy_builtin import effective_field

        return cls(
            custom_path=normalize_custom_path(row.custom_path),
            domain_modes=list(row.domain_modes or []),
            transport=row.transport.value if row.transport else None,
            tls_layer=row.tls_layer.value if row.tls_layer else None,
            l7_reverse_proto=row.l7_reverse_proto.value if row.l7_reverse_proto else None,
            download_tls_layer=row.download_tls_layer.value if row.download_tls_layer else None,
            download_domain_modes=list(row.download_domain_modes or []),
            server_core=row.server_core.value if row.server_core else "xray",
            server_tag=str(effective_field(row, "server_tag") or row.slug or ""),
            server_inbound_tcp_ports=normalize_port_list(row.server_inbound_tcp_ports),
            server_inbound_udp_ports=normalize_port_list(row.server_inbound_udp_ports),
            server_inbound_tcp_udp=(row.server_inbound_tcp_udp.value if row.server_inbound_tcp_udp else InboundTcpUdp.both.value),
            server_inbound_download_tcp_udp=(row.server_inbound_download_tcp_udp.value if row.server_inbound_download_tcp_udp else None),
            server_config=row.effective_server_config_text(),
            client_cores=tuple(
                ClientCoreSnapshot(
                    core=cc.core.value,
                    version=cc.version or "",
                    slug=cc.slug or f"client-{cc.core.value}",
                    outbounds_template=cc.effective_outbounds_template(),
                )
                for cc in row.client_cores
            ),
        )

    def iter_builtin_fields(self) -> Iterator[tuple[str, Any]]:
        from ..template_catalog.custom_proxy_builtin import (
            GENERAL_OVERRIDE_FIELDS,
            SERVER_OVERRIDE_FIELDS,
            client_override_key,
        )

        values: dict[str, Any] = {
            "custom_path": self.custom_path,
            "domain_modes": list(self.domain_modes),
            "transport": self.transport,
            "tls_layer": self.tls_layer,
            "l7_reverse_proto": self.l7_reverse_proto,
            "download_tls_layer": self.download_tls_layer,
            "download_domain_modes": list(self.download_domain_modes),
            "server_core": self.server_core,
            "server_tag": self.server_tag,
            "server_inbound_tcp_ports": list(self.server_inbound_tcp_ports),
            "server_inbound_udp_ports": list(self.server_inbound_udp_ports),
            "server_config": self.server_config,
        }
        for key in GENERAL_OVERRIDE_FIELDS + SERVER_OVERRIDE_FIELDS:
            if key in values and values[key] is not None:
                yield key, values[key]
        for cc in self.client_cores:
            if cc.core:
                yield client_override_key(cc.core), cc.outbounds_template
