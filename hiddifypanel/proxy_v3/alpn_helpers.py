from __future__ import annotations
from hiddifypanel.proxy_v3.context_vars.hconfig import HConfigVar
from hiddifypanel.proxy_v3.context_vars.proxy import ProxyVar
from hiddifypanel.models.proxy import ProxyProto
import copy
from typing import Any
from hiddifypanel.models.config_enum import ConfigEnum
from dataclasses import dataclass

DEFAULT_OUTBOUND_TAG_TEMPLATE = "{{ proxy.tag }} {{ domain.alias or domain.name }} {{ proxy.alpn }}"

XHTTP_ALPN_TAGS = [
    "h1",
    "tls_h1",
    "tls_h2",
    "tls_h3",
    "tls_h3_h2",
    "tls_h3_h2_h1",
    "tls_h2_h1",
]


@dataclass
class AlpnTags:
    h1: bool = False
    tls_h3: bool = False
    tls_h2: bool = False
    tls_h1: bool = False

    def to_tag(self) -> str:
        if self.h1 and not any((self.tls_h1, self.tls_h2, self.tls_h3)):
            return "h1"
        parts: list[str] = []
        if self.tls_h1:
            parts.append("h1")
        if self.tls_h2:
            parts.append("h2")
        if self.tls_h3:
            parts.append("h3")
        if not parts:
            return ""
        return "tls_" + "_".join(parts)

    def to_tls_alpn_list(self) -> list[str]:
        res = []
        if self.tls_h3:
            res.append("h3")
        if self.tls_h2:
            res.append("h2")
        if self.tls_h1:
            res.append("http/1.1")
        return res

    def to_http_alpn_list(self) -> list[str]:
        res = []
        if self.h1:
            res.append("http/1.1")
        return res

    def __hash__(self) -> int:
        return hash((self.tls_h3, self.tls_h2, self.tls_h1, self.h1))

    def filter(self, hconfigs: HConfigVar, protocol: ProxyProto) -> AlpnTags:

        alpns = copy.deepcopy(self)
        if not hconfigs.get(ConfigEnum.h2_enable) and self.tls_h2:
            alpns.tls_h2 = False
        if not hconfigs.get(ConfigEnum.quic_enable) and self.tls_h3:
            alpns.tls_h3 = False
        if not hconfigs.get(ConfigEnum.http_proxy_enable) and self.h1:
            alpns.h1 = False
        if protocol == ProxyProto.trojan:
            alpns.h1 = False
        if protocol in {ProxyProto.hysteria2, ProxyProto.tuic}:
            alpns.h1 = False
            alpns.tls_h1 = False
            alpns.tls_h2 = False
        return alpns

    @classmethod
    def from_tag(cls, tag: str) -> AlpnTags:
        normalized = normalize_alpn_tag(tag)
        tls = "tls" in normalized
        return cls(
            h1="h1" in normalized and not tls,
            tls_h3=tls and "h3" in normalized,
            tls_h2=tls and "h2" in normalized,
            tls_h1=tls and "h1" in normalized,
        )


def normalize_alpn_tag(tag: str | None) -> str:
    return str(tag or "").strip().lower()


def alpn_list_for_tag(tag: str | None) -> list[str]:
    if not tag:
        return []
    alpn = AlpnTags.from_tag(tag)
    return alpn.to_tls_alpn_list() + alpn.to_http_alpn_list()


def alpn_http_for_tag(tag: str | None) -> bool:
    return AlpnTags.from_tag(normalize_alpn_tag(tag)).h1


def _filter_trojan_alpns(tags: list[str], proto: str) -> list[str]:
    if proto == "trojan":
        return [t for t in tags if not (normalize_alpn_tag(t) == "h1")]
    return list(tags)


def alpns_for_l3(l3: str) -> list[str]:
    l3_key = str(l3).lower()
    if l3_key in ("quic", "udp"):
        return ["tls_h3"]
    return ["h1", "tls_h1", "tls_h2"]


def resolve_alpn_tags(
    tags: list[str] | tuple[str, ...] | None,
    hconfigs: HConfigVar,
    protocol: ProxyProto = ProxyProto.vless,
) -> list[AlpnTags]:
    seen: dict[str, AlpnTags] = {}
    for tag in tags or []:
        normalized = normalize_alpn_tag(tag)
        if not normalized:
            continue
        alpn = AlpnTags.from_tag(normalized).filter(hconfigs, protocol)
        key = alpn.to_tag() or normalized
        seen[key] = alpn
    return list(seen.values())


def normalize_alpn_tags(
    tags: list[str] | tuple[str, ...] | None,
    hconfigs: dict[ConfigEnum, Any] | None = None,
    protocol: str = "",
) -> list[str]:
    """Normalize ALPN tag strings, optionally filtered by panel hconfigs."""
    if hconfigs is not None or protocol:
        return [t.to_tag() or normalize_alpn_tag(t.to_tag()) for t in resolve_alpn_tags(tags, hconfigs, protocol) if t.to_tag()]
    seen: list[str] = []
    for tag in tags or []:
        normalized = normalize_alpn_tag(tag)
        if normalized and normalized not in seen:
            seen.append(normalized)
    return seen


def alpns_for_combo(l3: str, transport: str, proto: str = "") -> list[str]:
    transport_key = str(transport).lower()
    proto_key = str(proto).lower()

    if transport_key == "grpc":
        tags = ["tls_h2"]
    elif transport_key in ("ws", "httpupgrade", "tcp"):
        tags = ["h1", "tls_h1"]
    elif transport_key == "xhttp":
        tags = list(["h1", "tls_h1", "tls_h2", "tls_h3", "tls_h3_h2", "tls_h3_h2_h1", "tls_h2_h1"])
    else:
        tags = alpns_for_l3(l3)

    return normalize_alpn_tags(_filter_trojan_alpns(tags, proto_key), {}, proto_key)


def download_alpns_for_combo(transport: str) -> list[str]:
    if str(transport).lower() == "xhttp":
        return normalize_alpn_tags(list(XHTTP_ALPN_TAGS))
    return []


def is_xhttp_proxy_data(data: dict) -> bool:
    tags = [str(t).lower() for t in (data.get("tags") or [])]
    if "xhttp" in tags:
        return True
    name = str(data.get("name") or "").lower()
    slug = str(data.get("slug") or "").lower()
    return "xhttp" in name or "xhttp" in slug


def alpn_tls_for_tag(tag: str | None) -> bool:
    return "tls" in tag


def alpn_variant_skip_reason(alpn_tag: str | None, child_id: int = 0) -> str | None:
    from hiddifypanel.models import ConfigEnum, hconfig

    tag = normalize_alpn_tag(alpn_tag)
    if not tag:
        return None
    wire = alpn_list_for_tag(tag)
    if "h2" in wire and not hconfig(ConfigEnum.h2_enable, child_id):
        return "h2_enable is false"
    if "h3" in wire and not hconfig(ConfigEnum.quic_enable, child_id):
        return "quic_enable is false"
    return None


def is_tls_alpn_tag(tag: str | None) -> bool:
    return alpn_tls_for_tag(tag)


def stable_proxy_port(proxy_id: int | None, domain_id: int | None = None) -> int:
    """Deterministic port in [10000, 50000] from proxy and domain ids."""
    pid = int(proxy_id or 0)
    did = int(domain_id or 0)
    if pid <= 0:
        return 2080
    mixed = (pid * 1_000_003 + did * 1_009 + 17) % 40_001
    return 10_000 + mixed
