from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .alpn_helpers import stable_proxy_port

MODE_DOMAINS_L7_GATEWAY = 'domains_l7_gateway'
MODE_DOMAINS_SNI_GATEWAY = 'domains_sni_gateway'
MODE_DOMAINS_AUTO_PUBLIC_PORTS = 'domains_auto_public_ports'
MODE_DOMAINS_SINGLE_PUBLIC_PORT = 'domains_single_public_port'
MODE_IP = 'ip'


@dataclass(frozen=True)
class ResolvedInboundPorts:
    tcp_ports: list[int]
    udp_ports: list[int]
    tcp_port: int | None
    udp_port: int | None


def normalize_port_list(value: Any) -> list[int]:
    if value is None:
        return []
    if isinstance(value, bool):
        return []
    if isinstance(value, int):
        return [value] if value > 0 else []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        parts = [p.strip() for p in text.replace(';', ',').split(',') if p.strip()]
        return [int(p) for p in parts if int(p) > 0]
    if isinstance(value, (list, tuple)):
        out: list[int] = []
        for item in value:
            if item is None or item == '':
                continue
            port = int(item)
            if port > 0 and port not in out:
                out.append(port)
        return out
    return []


def mode_value(mode: Any) -> str:
    if mode is None:
        return ''
    if hasattr(mode, 'value'):
        return str(mode.value)
    return str(mode)


def mode_requires_static_ports(mode: Any) -> bool:
    value = mode_value(mode)
    return value in (MODE_DOMAINS_SINGLE_PUBLIC_PORT, MODE_IP)


def mode_uses_auto_ports(mode: Any) -> bool:
    return mode_value(mode) == MODE_DOMAINS_AUTO_PUBLIC_PORTS


def mode_uses_gateway_port(mode: Any) -> bool:
    value = mode_value(mode)
    return value in (MODE_DOMAINS_L7_GATEWAY, MODE_DOMAINS_SNI_GATEWAY)


def mode_port_requires_domain(mode: Any) -> bool:
    return mode_value(mode) in (MODE_DOMAINS_AUTO_PUBLIC_PORTS, MODE_DOMAINS_SNI_GATEWAY)


def mode_allows_domain_mode_selection(mode: Any) -> bool:
    value = mode_value(mode)
    return value in (MODE_DOMAINS_L7_GATEWAY, MODE_DOMAINS_AUTO_PUBLIC_PORTS, MODE_DOMAINS_SINGLE_PUBLIC_PORT)


def mode_allows_ip_domain_modes(mode: Any) -> bool:
    return mode_value(mode) == MODE_IP


def default_domain_modes_for_mode(mode: Any) -> list[str]:
    if mode_allows_domain_mode_selection(mode):
        if mode_value(mode) == MODE_DOMAINS_L7_GATEWAY:
            return ['direct']
        return ['special']
    if mode_value(mode) == MODE_DOMAINS_SNI_GATEWAY:
        return ['special']
    if mode_value(mode) == MODE_IP:
        return []
    return ['special']


def resolve_inbound_ports(
    mode: Any,
    proxy_id: int | None,
    *,
    domain_id: int | None = None,
    stored_tcp_ports: list[int] | None = None,
    stored_udp_ports: list[int] | None = None,
) -> ResolvedInboundPorts:
    value = mode_value(mode)
    pid = int(proxy_id or 0)

    if value in (MODE_DOMAINS_L7_GATEWAY, MODE_DOMAINS_SNI_GATEWAY):
        port = stable_proxy_port(pid, 0)
        return ResolvedInboundPorts([port], [port], port, port)

    if value == MODE_DOMAINS_AUTO_PUBLIC_PORTS:
        port = stable_proxy_port(pid, int(domain_id or 0))
        return ResolvedInboundPorts([port], [port], port, port)

    tcp_ports = list(stored_tcp_ports or [])
    udp_ports = list(stored_udp_ports or [])
    if not udp_ports and tcp_ports:
        udp_ports = list(tcp_ports)
    return ResolvedInboundPorts(
        tcp_ports,
        udp_ports,
        tcp_ports[0] if tcp_ports else None,
        udp_ports[0] if udp_ports else None,
    )


def ports_list_to_ranges(ports: list[int]) -> list[int | str]:
    """Collapse sorted consecutive ports into single ports or inclusive ranges (e.g. 1000-2000)."""
    cleaned = sorted({int(port) for port in ports if int(port) > 0})
    if not cleaned:
        return []

    ranges: list[int | str] = []
    start = prev = cleaned[0]
    for port in cleaned[1:]:
        if port == prev + 1:
            prev = port
            continue
        ranges.append(start if start == prev else f'{start}-{prev}')
        start = prev = port
    ranges.append(start if start == prev else f'{start}-{prev}')
    return ranges


def ports_for_proxy_row(
    row: Any,
    *,
    domain_id: int | None = None,
) -> ResolvedInboundPorts:
    return resolve_inbound_ports(
        row.mode,
        row.id,
        domain_id=domain_id,
        stored_tcp_ports=normalize_port_list(getattr(row, 'server_inbound_tcp_ports', None)),
        stored_udp_ports=normalize_port_list(getattr(row, 'server_inbound_udp_ports', None)),
    )


def ports_dict_for_proxy_row(row: Any, *, domain_id: int | None = None) -> dict[str, Any]:
    resolved = ports_for_proxy_row(row, domain_id=domain_id)
    primary = resolved.tcp_port or resolved.udp_port or 0
    data = {
        'server_inbound_tcp_ports': resolved.tcp_ports,
        'server_inbound_udp_ports': resolved.udp_ports,
        'tcp_ports': resolved.tcp_ports,
        'udp_ports': resolved.udp_ports,
        'tcp_port': resolved.tcp_port,
        'udp_port': resolved.udp_port,
        'server_inbound_port': primary,
    }
    if not mode_port_requires_domain(row.mode):
        data['port'] = primary
    return data
