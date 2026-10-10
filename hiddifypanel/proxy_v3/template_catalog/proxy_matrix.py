from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

from hiddifypanel.models.proxy import ProxyCDN, ProxyL3, ProxyProto, ProxyTransport

# Same transport/cdn/proto strings as init_db.get_proxy_rows_v1 / make_proxy_rows.
#: ``l3`` of the WireGuard row that hiddify-core serves as an endpoint (a separate preset from the wg-quick one).
WIREGUARD_ENDPOINT_L3 = "wg_endpoint"

#: Not created for now: a hiddify-core WireGuard endpoint has no per-user accounting (usage, limits), which the
#: wg-quick WireGuard rows have. The templates and builders stay; turn this on to get the preset again.
WIREGUARD_ENDPOINT_ENABLED = False

PROXY_CFG_STRINGS: list[str] = [
    "h2 direct vless",
    "WS direct vless",
    "WS direct trojan",
    "WS direct vmess",
    "httpupgrade direct vless",
    "httpupgrade direct vmess",
    "httpupgrade direct trojan",
    "xhttp direct vless",
    "xhttp direct vmess",
    "xhttp direct trojan",
    "tcp direct vless",
    "tcp direct vmess",
    "http direct vless",
    "http direct trojan",
    "http direct vmess",
    "grpc direct vless",
    "grpc direct trojan",
    "grpc direct vmess",
    "faketls direct ss",
    "WS direct v2ray",
    "h2 relay vless",
    "WS relay vless",
    "WS relay trojan",
    "WS relay vmess",
    "httpupgrade relay vless",
    "httpupgrade relay vmess",
    "httpupgrade relay trojan",
    "xhttp relay vless",
    "xhttp relay vmess",
    "xhttp relay trojan",
    "tcp relay vless",
    "tcp relay vmess",
    "http relay vless",
    "http relay trojan",
    "http relay vmess",
    "grpc relay vless",
    "grpc relay trojan",
    "grpc relay vmess",
    "faketls relay ss",
    "WS relay v2ray",
    "WS CDN v2ray",
    "WS CDN vless",
    "WS CDN trojan",
    "WS CDN vmess",
    "httpupgrade CDN vless",
    "httpupgrade CDN vmess",
    "httpupgrade CDN trojan",
    "xhttp CDN vless",
    "xhttp CDN vmess",
    "xhttp CDN trojan",
    "grpc CDN vless",
    "grpc CDN trojan",
    "grpc CDN vmess",
]

EXTRA_PROXY_ROWS: list[dict[str, Any]] = [
    {"l3": ProxyL3.custom, "transport": ProxyTransport.shadowsocks, "cdn": "direct", "proto": "shadowsocks", "name": "ShadowSocks2022"},
    {"l3": ProxyL3.custom, "transport": ProxyTransport.shadowsocks, "cdn": "relay", "proto": "shadowsocks", "name": "ShadowSocks2022 Relay"},
    {"l3": ProxyL3.tls, "transport": ProxyTransport.shadowtls, "cdn": "direct", "proto": "shadowsocks", "name": "ShadowTLS"},
    {"l3": ProxyL3.tls, "transport": ProxyTransport.shadowtls, "cdn": "relay", "proto": "shadowsocks", "name": "ShadowTLS Relay"},
    {"l3": "ssh", "transport": "ssh", "cdn": "direct", "proto": "ssh", "name": "SSH"},
    {"l3": "ssh", "transport": ProxyTransport.ssh, "cdn": ProxyCDN.relay, "proto": ProxyProto.ssh, "name": "SSH Relay"},
    {"l3": ProxyL3.h3_quic, "transport": "custom", "cdn": "direct", "proto": "tuic", "name": "TUIC"},
    {"l3": ProxyL3.h3_quic, "transport": "custom", "cdn": "relay", "proto": "tuic", "name": "TUIC Relay"},
    {"l3": ProxyL3.h3_quic, "transport": "custom", "cdn": "direct", "proto": "hysteria2", "name": "Hysteria2"},
    {"l3": ProxyL3.h3_quic, "transport": "custom", "cdn": "relay", "proto": "hysteria2", "name": "Hysteria2 Relay"},
    {"l3": ProxyL3.h3_quic, "transport": "custom", "cdn": "direct", "proto": "hysteria", "name": "Hysteria"},
    {"l3": ProxyL3.h3_quic, "transport": "custom", "cdn": "relay", "proto": "hysteria", "name": "Hysteria Relay"},
    {"l3": ProxyL3.custom, "transport": ProxyTransport.custom, "cdn": ProxyCDN.direct, "proto": ProxyProto.dnstt, "name": "DNSTT"},
    {"l3": ProxyL3.custom, "transport": ProxyTransport.custom, "cdn": ProxyCDN.direct, "proto": ProxyProto.slipstream, "name": "Slipstream"},
    {"l3": ProxyL3.custom, "transport": ProxyTransport.custom, "cdn": ProxyCDN.direct, "proto": ProxyProto.masterdns, "name": "MasterDNS"},
    # Snell v5 and v6 (v4 is gone: the v5 wire protocol is the same as v4, so v5 serves v4 clients too)
    {"l3": "snell_v5", "transport": "custom", "cdn": "direct", "proto": "snell", "name": "Snell v5"},
    {"l3": "snell_v5", "transport": "custom", "cdn": "relay", "proto": "snell", "name": "Snell v5 Relay"},
    {"l3": "snell_v6", "transport": "custom", "cdn": "direct", "proto": "snell", "name": "Snell v6"},
    {"l3": "snell_v6", "transport": "custom", "cdn": "relay", "proto": "snell", "name": "Snell v6 Relay"},
    {"l3": ProxyL3.udp, "transport": ProxyTransport.custom, "cdn": ProxyCDN.direct, "proto": ProxyProto.wireguard, "name": "WireGuard"},
    {"l3": ProxyL3.udp, "transport": ProxyTransport.custom, "cdn": ProxyCDN.relay, "proto": ProxyProto.wireguard, "name": "WireGuard Relay"},
    {"l3": "tls", "transport": "custom", "cdn": "direct", "proto": "naive", "name": "Naive"},
    {"l3": "tls", "transport": "custom", "cdn": "relay", "proto": "naive", "name": "Naive Relay"},
    {"l3": "tls", "transport": "tcp", "cdn": "direct", "proto": "mieru", "name": "Mieru TCP"},
    {"l3": "tls", "transport": "udp", "cdn": "direct", "proto": "mieru", "name": "Mieru UDP"},
    {"l3": "tls", "transport": "tcp", "cdn": "relay", "proto": "mieru", "name": "Mieru TCP Relay"},
    {"l3": "tls", "transport": "udp", "cdn": "relay", "proto": "mieru", "name": "Mieru UDP Relay"},
    {"l3": "tls", "transport": "custom", "cdn": "direct", "proto": "socks", "name": "SOCKS", "enable": False},
    {"l3": "tls", "transport": "custom", "cdn": "relay", "proto": "socks", "name": "SOCKS Relay", "enable": False},
    {"l3": "tls", "transport": "custom", "cdn": "direct", "proto": "anytls", "name": "AnyTLS"},
    {"l3": "tls", "transport": "custom", "cdn": "relay", "proto": "anytls", "name": "AnyTLS Relay"},
]

# WireGuard served by hiddify-core itself (a sing-box wireguard endpoint), on its own port: it does not use the
# wg-quick service of the plain WireGuard rows above.
WIREGUARD_ENDPOINT_ROWS: list[dict[str, Any]] = [
    {"l3": WIREGUARD_ENDPOINT_L3, "transport": ProxyTransport.custom, "cdn": ProxyCDN.direct, "proto": ProxyProto.wireguard, "name": "WireGuard Endpoint"},
]

L3_LAYERS: list[str | ProxyL3] = [
    ProxyL3.h3_quic,
    "tls_h2",
    ProxyL3.tls,
    ProxyL3.http,
    ProxyL3.reality,
]


def is_wireguard_endpoint(combo: "ProxyCombination") -> bool:
    return str(combo.proto).lower() == "wireguard" and str(combo.l3) == WIREGUARD_ENDPOINT_L3


@dataclass
class ProxyCombination:
    l3: str
    transport: str
    cdn: str
    proto: str
    enable: bool
    name: str
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def preset_slug(self) -> str:
        base = f"{self.l3}-{self.transport}-{self.cdn}-{self.proto}".lower()
        base = base.replace(" ", "-")
        if self.params.get("download", {}).get("alpn"):
            alpn = self.params["download"]["alpn"].replace("/", "")
            base = f"{base}-dl-{alpn}"
        return base


def _enum_val(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def iter_proxy_combinations(cfgs: list[str] | None = None) -> Iterator[ProxyCombination]:
    """Port of init_db.make_proxy_rows — yields every valid l3 × transport × cdn × proto combo."""
    cfg_list = cfgs if cfgs is not None else PROXY_CFG_STRINGS
    for l3 in L3_LAYERS:
        l3_s = _enum_val(l3)
        for c in cfg_list:
            transport, cdn, proto = c.split(" ")
            if transport != ProxyTransport.xhttp and l3 == ProxyL3.h3_quic:
                continue
            if l3_s in ("kcp", "reality") and cdn != "direct":
                continue
            # REALITY rides TCP, xHTTP (h2), gRPC and raw HTTP ("rawhttp", transport "http") over TLS;
            # clients only offer it for VLESS (context_vars/ctx_client.is_reality_domain_valid).
            if l3_s == "reality" and (transport not in ("tcp", "XTLS", ProxyTransport.xhttp, "grpc", "http") or proto != "vless"):
                continue
            if proto == "trojan" and l3_s not in ("tls", "xtls", "tls_h2", "h3_quic"):
                continue
            if transport in ("grpc", "XTLS", "faketls") and l3_s == "http":
                if proto not in ("vless", "vmess"):
                    continue
            if transport == "faketls" and l3_s != "tls":
                continue
            if transport in ("h2",) and l3_s != "reality":
                continue
            if l3 in (ProxyL3.h3_quic, "tls_h2") and transport in (ProxyTransport.httpupgrade, ProxyTransport.WS):
                continue
            if transport in (ProxyTransport.httpupgrade, ProxyTransport.WS):
                if l3_s == "http":
                    if proto not in ("vless", "vmess"):
                        continue
                elif l3_s != "tls":
                    continue

            enable = l3_s != "http" or proto in ("vless", "vmess")
            enable = enable and (transport != "tcp" or l3_s in ("reality", "http", "tls"))
            enable = enable and (transport != "http" or l3_s in ("http", "tls", "reality"))
            name = f"{l3_s} {c}"

            params_list: list[tuple[str, dict[str, Any]]] = [("", {})]

            for name_postfix, params in params_list:
                yield ProxyCombination(
                    l3=l3_s,
                    transport=transport,
                    cdn=cdn,
                    proto=proto,
                    enable=enable,
                    name=name + name_postfix,
                    params=params,
                )

    for row in EXTRA_PROXY_ROWS + (WIREGUARD_ENDPOINT_ROWS if WIREGUARD_ENDPOINT_ENABLED else []):
        yield ProxyCombination(
            l3=_enum_val(row["l3"]),
            transport=_enum_val(row["transport"]),
            cdn=_enum_val(row["cdn"]),
            proto=_enum_val(row["proto"]),
            enable=bool(row.get("enable", True)),
            name=row["name"],
        )
