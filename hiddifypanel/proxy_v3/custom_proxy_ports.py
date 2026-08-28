from __future__ import annotations

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


def mode_requires_static_ports(mode) -> bool:
    from hiddifypanel.models.custom_proxy import CustomProxyMode

    mode = coerce_proxy_mode(mode)
    return mode in (CustomProxyMode.domains_single_public_port, CustomProxyMode.ip)


def mode_uses_auto_ports(mode) -> bool:
    from hiddifypanel.models.custom_proxy import CustomProxyMode

    return coerce_proxy_mode(mode) == CustomProxyMode.domains_auto_public_ports


def mode_uses_gateway_port(mode) -> bool:
    from hiddifypanel.models.custom_proxy import CustomProxyMode

    mode = coerce_proxy_mode(mode)
    return mode in (
        CustomProxyMode.domains_l7_gateway,
        CustomProxyMode.domains_sni_gateway,
        CustomProxyMode.domains_dns_gateway,
    )


def mode_port_requires_domain(mode) -> bool:
    from hiddifypanel.models.custom_proxy import CustomProxyMode

    mode = coerce_proxy_mode(mode)
    return mode in (
        CustomProxyMode.domains_auto_public_ports,
        CustomProxyMode.domains_sni_gateway,
        CustomProxyMode.domains_dns_gateway,
    )


def mode_allows_domain_mode_selection(mode) -> bool:
    from hiddifypanel.models.custom_proxy import CustomProxyMode

    mode = coerce_proxy_mode(mode)
    return mode in (
        CustomProxyMode.domains_l7_gateway,
        CustomProxyMode.domains_auto_public_ports,
        CustomProxyMode.domains_single_public_port,
    )


def mode_allows_ip_domain_modes(mode) -> bool:
    from hiddifypanel.models.custom_proxy import CustomProxyMode

    return coerce_proxy_mode(mode) == CustomProxyMode.ip


def default_domain_modes_for_mode(mode) -> list[str]:
    from hiddifypanel.models.custom_proxy import CustomProxyMode

    mode = coerce_proxy_mode(mode)
    if mode in (
        CustomProxyMode.domains_l7_gateway,
        CustomProxyMode.domains_auto_public_ports,
        CustomProxyMode.domains_single_public_port,
    ):
        if mode == CustomProxyMode.domains_l7_gateway:
            return ["direct"]
        return ["direct", "relay"]
    if mode == CustomProxyMode.domains_sni_gateway:
        return ["direct", "relay"]
    if mode == CustomProxyMode.ip:
        return []
    return ["direct", "relay"]


def ports_for_proxy_row(
    row,
    *,
    domain_id: int | None = None,
    server_side: bool = True,
) -> ResolvedInboundPorts:
    from hiddifypanel.models.custom_proxy import effective_server_tcp_udp

    return resolve_inbound_ports(
        row.mode,
        row.id,
        domain_id=domain_id,
        db_tcp_ports=normalize_port_list(getattr(row, "server_inbound_tcp_ports", None)),
        db_udp_ports=normalize_port_list(getattr(row, "server_inbound_udp_ports", None)),
        server_side=server_side,
        tcp_udp=effective_server_tcp_udp(row),
        tls_layer=getattr(row, "tls_layer", None),
    )


def mode_uses_firewall_ports(mode) -> bool:
    from hiddifypanel.models.custom_proxy import CustomProxyMode

    mode = coerce_proxy_mode(mode)
    return mode not in (
        CustomProxyMode.domains_l7_gateway,
        CustomProxyMode.domains_sni_gateway,
        CustomProxyMode.domains_dns_gateway,
    )


def firewall_protocols(tcp_udp) -> list[str]:
    from hiddifypanel.models.custom_proxy import InboundTcpUdp

    if isinstance(tcp_udp, str):
        tcp_udp = InboundTcpUdp(tcp_udp)
    if tcp_udp == InboundTcpUdp.tcp:
        return ["tcp"]
    if tcp_udp == InboundTcpUdp.udp:
        return ["udp"]
    return ["tcp", "udp"]


def firewall_protocols_for_proxy(row) -> list[str]:
    from hiddifypanel.models.custom_proxy import uses_xhttp_download_settings

    if uses_xhttp_download_settings(row):
        protocols: list[str] = []
        for value in (
            getattr(row, "server_inbound_tcp_udp", None),
            getattr(row, "server_inbound_download_tcp_udp", None),
        ):
            for protocol in firewall_protocols(value or "tcp"):
                if protocol not in protocols:
                    protocols.append(protocol)
        return protocols or ["tcp"]
    return firewall_protocols(getattr(row, "server_inbound_tcp_udp", None) or "both")


def ports_dict_for_proxy_row(row, *, domain_id: int | None = None, server_side: bool = True) -> dict:
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
        tcp_udp = getattr(row, "server_inbound_tcp_udp", None)
        data["tcp_udp"] = tcp_udp.value if tcp_udp else "both"
        data["firewall_protocols"] = firewall_protocols_for_proxy(row)
    if not mode_port_requires_domain(row.mode):
        data["port"] = primary
    return data
