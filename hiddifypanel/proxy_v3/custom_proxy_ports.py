from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hiddifypanel.models.custom_proxy import CustomProxy, CustomProxyMode, InboundTcpUdp

# Backward-compatible re-exports for modules outside context_vars.
from hiddifypanel.proxy_v3.context_vars.ports import (
    GATEWAY_CLIENT_HTTP_PORT,
    GATEWAY_CLIENT_TLS_PORT,
    ResolvedInboundPorts,
    coerce_proxy_mode,
    gateway_client_port,
    gateway_client_ports,
    mode_value,
    normalize_port_list,
    ports_list_to_ranges,
    primary_resolved_port,
    resolve_inbound_ports,
)


def mode_requires_static_ports(mode: CustomProxyMode | str) -> bool:
    from hiddifypanel.models.custom_proxy import CustomProxyMode

    parsed = coerce_proxy_mode(mode)
    return parsed in (CustomProxyMode.domains_single_public_port, CustomProxyMode.ip)


def mode_uses_auto_ports(mode: CustomProxyMode | str) -> bool:
    from hiddifypanel.models.custom_proxy import CustomProxyMode

    return coerce_proxy_mode(mode) == CustomProxyMode.domains_auto_public_ports


def mode_uses_gateway_port(mode: CustomProxyMode | str) -> bool:
    from hiddifypanel.models.custom_proxy import CustomProxyMode

    parsed = coerce_proxy_mode(mode)
    return parsed in (
        CustomProxyMode.domains_l7_gateway,
        CustomProxyMode.domains_sni_gateway,
        CustomProxyMode.domains_dns_gateway,
    )


def mode_port_requires_domain(mode: CustomProxyMode | str) -> bool:
    from hiddifypanel.models.custom_proxy import CustomProxyMode

    parsed = coerce_proxy_mode(mode)
    return parsed in (
        CustomProxyMode.domains_auto_public_ports,
        CustomProxyMode.domains_sni_gateway,
        CustomProxyMode.domains_dns_gateway,
    )


def mode_allows_domain_mode_selection(mode: CustomProxyMode | str) -> bool:
    from hiddifypanel.models.custom_proxy import CustomProxyMode

    parsed = coerce_proxy_mode(mode)
    return parsed in (
        CustomProxyMode.domains_l7_gateway,
        CustomProxyMode.domains_auto_public_ports,
        CustomProxyMode.domains_single_public_port,
    )


def mode_allows_ip_domain_modes(mode: CustomProxyMode | str) -> bool:
    from hiddifypanel.models.custom_proxy import CustomProxyMode

    return coerce_proxy_mode(mode) == CustomProxyMode.ip


def default_domain_modes_for_mode(mode: CustomProxyMode | str) -> list[str]:
    from hiddifypanel.models.custom_proxy import CustomProxyMode
    from hiddifypanel.proxy_v3.domain_mode_filter import VALID_DIRECT_RELAY_DOMAIN_MODES, V2RAY_ALL_DOMAIN_MODES

    parsed = coerce_proxy_mode(mode)
    if parsed == CustomProxyMode.domains_l7_gateway:
        return list(V2RAY_ALL_DOMAIN_MODES)
    return list(VALID_DIRECT_RELAY_DOMAIN_MODES)


def ports_for_proxy_row(
    row: CustomProxy,
    *,
    domain_id: int | None = None,
    server_side: bool = True,
) -> ResolvedInboundPorts:
    from hiddifypanel.models.custom_proxy import effective_server_tcp_udp

    return resolve_inbound_ports(
        row.mode,
        row.id,
        domain_id=domain_id,
        db_tcp_ports=normalize_port_list(row.server_inbound_tcp_ports),
        db_udp_ports=normalize_port_list(row.server_inbound_udp_ports),
        server_side=server_side,
        tcp_udp=effective_server_tcp_udp(row),
        tls_layer=row.tls_layer,
    )


def mode_uses_firewall_ports(mode: CustomProxyMode | str) -> bool:
    from hiddifypanel.models.custom_proxy import CustomProxyMode

    parsed = coerce_proxy_mode(mode)
    return parsed not in (
        CustomProxyMode.domains_l7_gateway,
        CustomProxyMode.domains_sni_gateway,
        CustomProxyMode.domains_dns_gateway,
    )


def firewall_protocols(tcp_udp: InboundTcpUdp | str | None) -> list[str]:
    from hiddifypanel.models.custom_proxy import InboundTcpUdp

    parsed = tcp_udp if isinstance(tcp_udp, InboundTcpUdp) else InboundTcpUdp(tcp_udp or InboundTcpUdp.both)
    if parsed == InboundTcpUdp.tcp:
        return ["tcp"]
    if parsed == InboundTcpUdp.udp:
        return ["udp"]
    return ["tcp", "udp"]


def firewall_protocols_for_proxy(row: CustomProxy) -> list[str]:
    from hiddifypanel.models.custom_proxy import InboundTcpUdp, uses_xhttp_download_settings

    if uses_xhttp_download_settings(row):
        protocols: list[str] = []
        for value in (
            row.server_inbound_tcp_udp,
            row.server_inbound_download_tcp_udp,
        ):
            for protocol in firewall_protocols(value or InboundTcpUdp.tcp):
                if protocol not in protocols:
                    protocols.append(protocol)
        return protocols or ["tcp"]
    return firewall_protocols(row.server_inbound_tcp_udp or InboundTcpUdp.both)


def ports_dict_for_proxy_row(row: CustomProxy, *, domain_id: int | None = None, server_side: bool = True) -> dict:
    resolved = ports_for_proxy_row(row, domain_id=domain_id, server_side=server_side)
    primary = primary_resolved_port(resolved)
    data = {
        "server_inbound_tcp_ports": resolved.tcp_ports,
        "server_inbound_udp_ports": resolved.udp_ports,
        "tcp_ports": resolved.tcp_ports,
        "udp_ports": resolved.udp_ports,
        "tcp_port": resolved.tcp_port,
        "udp_port": resolved.udp_port,
        "server_inbound_port": primary,
    }
    if mode_uses_firewall_ports(row.mode):
        tcp_udp = row.server_inbound_tcp_udp
        data["tcp_udp"] = tcp_udp.value if tcp_udp else "both"
        data["firewall_protocols"] = firewall_protocols_for_proxy(row)
    if not mode_port_requires_domain(row.mode):
        data["port"] = primary
    return data
