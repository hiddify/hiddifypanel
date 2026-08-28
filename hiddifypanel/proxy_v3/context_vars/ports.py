from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hiddifypanel.models.custom_proxy import CustomProxyMode, InboundTcpUdp

GATEWAY_CLIENT_TLS_PORT = 443
GATEWAY_CLIENT_HTTP_PORT = 80


def _tls_layer_key(tls_layer: Any) -> str:
    value = tls_layer.value if hasattr(tls_layer, "value") else tls_layer
    key = str(value or "tls").strip().lower().replace("-", "_").replace("+", "_")
    return {
        "tcp_tls": "tls",
        "quic_tcp_tls": "quic_tcp_tls",
        "quic_plus_tcp_tls": "quic_tcp_tls",
    }.get(key, key)


def gateway_client_ports(tls_layer: Any = None) -> tuple[int | None, int | None]:
    """Return (tcp_port, udp_port) for L7 client-facing ports."""
    key = _tls_layer_key(tls_layer)
    if key == "http":
        return GATEWAY_CLIENT_HTTP_PORT, None
    if key == "quic_tls":
        return None, GATEWAY_CLIENT_TLS_PORT
    if key == "quic_tcp_tls":
        return GATEWAY_CLIENT_TLS_PORT, GATEWAY_CLIENT_TLS_PORT
    return GATEWAY_CLIENT_TLS_PORT, None


def gateway_client_port(tls_layer: Any = None) -> int:
    tcp_port, udp_port = gateway_client_ports(tls_layer)
    return tcp_port or udp_port or GATEWAY_CLIENT_TLS_PORT


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
        parts = [p.strip() for p in text.replace(";", ",").split(",") if p.strip()]
        return [int(p) for p in parts if int(p) > 0]
    if isinstance(value, (list, tuple)):
        out: list[int] = []
        for item in value:
            if item is None or item == "":
                continue
            port = int(item)
            if port > 0 and port not in out:
                out.append(port)
        return out
    return []


def mode_value(mode: Any) -> str:
    if mode is None:
        return ""
    if hasattr(mode, "value"):
        return str(mode.value)
    return str(mode)


def coerce_proxy_mode(mode: Any) -> CustomProxyMode:
    from hiddifypanel.models.custom_proxy import CustomProxyMode

    if isinstance(mode, CustomProxyMode):
        return mode
    return CustomProxyMode(mode_value(mode))


def primary_resolved_port(resolved: ResolvedInboundPorts, *, default: int = 2080) -> int:
    if resolved.tcp_port is not None:
        return resolved.tcp_port
    if resolved.udp_port is not None:
        return resolved.udp_port
    return default


def _resolved_optional(tcp_port: int | None, udp_port: int | None) -> ResolvedInboundPorts:
    tcp_ports = [tcp_port] if tcp_port else []
    udp_ports = [udp_port] if udp_port else []
    return ResolvedInboundPorts(tcp_ports, udp_ports, tcp_port, udp_port)


def _resolved_lists(port: int) -> ResolvedInboundPorts:
    return ResolvedInboundPorts([port], [port], port, port)


def _stored_or_stable_lists(proxy_id: int, db_tcp_ports: list[int] | None, db_udp_ports: list[int] | None) -> tuple[list[int], list[int]]:
    from hiddifypanel.proxy_v3.alpn_helpers import stable_proxy_port

    tcp_ports = list(db_tcp_ports or [])
    udp_ports = list(db_udp_ports or [])
    if not tcp_ports and not udp_ports:
        port = stable_proxy_port(proxy_id, 0)
        return [port], [port]
    if not udp_ports and tcp_ports:
        udp_ports = list(tcp_ports)
    elif not tcp_ports and udp_ports:
        tcp_ports = list(udp_ports)
    return tcp_ports, udp_ports


def coerce_tcp_udp(tcp_udp: Any) -> InboundTcpUdp:
    from hiddifypanel.models.custom_proxy import InboundTcpUdp

    if isinstance(tcp_udp, InboundTcpUdp):
        return tcp_udp
    if tcp_udp is None:
        return InboundTcpUdp.both
    return InboundTcpUdp(str(tcp_udp))


def _apply_tcp_udp_filter(resolved: ResolvedInboundPorts, tcp_udp: Any) -> ResolvedInboundPorts:
    from hiddifypanel.models.custom_proxy import InboundTcpUdp

    tcp_udp = coerce_tcp_udp(tcp_udp)
    if tcp_udp == InboundTcpUdp.both:
        return resolved
    if tcp_udp == InboundTcpUdp.tcp:
        return ResolvedInboundPorts(
            list(resolved.tcp_ports),
            [],
            resolved.tcp_port,
            None,
        )
    return ResolvedInboundPorts(
        [],
        list(resolved.udp_ports),
        None,
        resolved.udp_port,
    )


def resolve_inbound_ports(
    mode: Any,
    proxy_id: int | None,
    *,
    domain_id: int | None = None,
    db_tcp_ports: list[int] | None = None,
    db_udp_ports: list[int] | None = None,
    server_side: bool = True,
    tcp_udp: Any = None,
    tls_layer: Any = None,
) -> ResolvedInboundPorts:
    from hiddifypanel.models.custom_proxy import CustomProxyMode
    from hiddifypanel.proxy_v3.alpn_helpers import stable_proxy_port

    mode = coerce_proxy_mode(mode)
    pid = int(proxy_id or 0)
    did = int(domain_id or 0)
    db_tcp = list(db_tcp_ports or [])
    db_udp = list(db_udp_ports or [])
    protocol = coerce_tcp_udp(tcp_udp)

    if mode == CustomProxyMode.domains_l7_gateway:
        if server_side:
            resolved = _resolved_lists(stable_proxy_port(pid, 0))
            return _apply_tcp_udp_filter(resolved, protocol)
        tcp_port, udp_port = gateway_client_ports(tls_layer)
        return _resolved_optional(tcp_port, udp_port)

    if mode == CustomProxyMode.domains_sni_gateway:
        if server_side:
            resolved = _resolved_lists(stable_proxy_port(pid, did))
        else:
            resolved = _resolved_lists(GATEWAY_CLIENT_TLS_PORT)
        return _apply_tcp_udp_filter(resolved, protocol)

    if mode == CustomProxyMode.domains_dns_gateway:
        if server_side:
            resolved = _resolved_lists(stable_proxy_port(pid, did))
        else:
            resolved = ResolvedInboundPorts([0], [0], 0, 0)
        return _apply_tcp_udp_filter(resolved, protocol)

    if mode == CustomProxyMode.domains_auto_public_ports:
        return _apply_tcp_udp_filter(_resolved_lists(stable_proxy_port(pid, did)), protocol)

    if mode in (CustomProxyMode.domains_single_public_port, CustomProxyMode.ip):
        tcp_ports, udp_ports = _stored_or_stable_lists(pid, db_tcp, db_udp)
        resolved = ResolvedInboundPorts(
            tcp_ports,
            udp_ports,
            tcp_ports[0] if tcp_ports else None,
            udp_ports[0] if udp_ports else None,
        )
        return _apply_tcp_udp_filter(resolved, protocol)

    tcp_ports, udp_ports = _stored_or_stable_lists(pid, db_tcp, db_udp)
    resolved = ResolvedInboundPorts(
        tcp_ports,
        udp_ports,
        tcp_ports[0] if tcp_ports else None,
        udp_ports[0] if udp_ports else None,
    )
    return _apply_tcp_udp_filter(resolved, protocol)


def ports_list_to_ranges(ports: list[int]) -> list[int | str]:
    """Collapse sorted consecutive ports into single ports or inclusive ranges."""
    cleaned = sorted({int(port) for port in ports if int(port) > 0})
    if not cleaned:
        return []

    ranges: list[int | str] = []
    start = prev = cleaned[0]
    for port in cleaned[1:]:
        if port == prev + 1:
            prev = port
            continue
        ranges.append(start if start == prev else f"{start}-{prev}")
        start = prev = port
    ranges.append(start if start == prev else f"{start}-{prev}")
    return ranges
