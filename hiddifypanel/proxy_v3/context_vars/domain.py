from __future__ import annotations

import ipaddress
import re
from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hiddifypanel import hutils
from hiddifypanel.hutils.network.auto_ip_selector import split_pattern
from hiddifypanel.hutils.proxy import random_or_none
from hiddifypanel.models import Domain, DomainType, FakeMode
from hiddifypanel.models.config import hconfig
from hiddifypanel.models.config_enum import ConfigEnum

from .cert import CertVar
from .ip import IPVar
from .json_map import JsonMap

DEFAULT_MAX_PROXY_IPS_PER_VERSION = 3
_FORCED_HOST_SPLIT = re.compile(r"[ \t\r\n;,]+")


class _ExtractedSniHost(TypedDict):
    sni: str
    host: str


class DomainIPVar(BaseModel):
    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    id: int | None = None
    name: str = ""
    ips: IPVar = Field(default_factory=IPVar.empty)
    host: str = ""
    sni: str = ""
    port: int = 443

    mode: DomainType
    fake_mode: FakeMode = FakeMode.valid
    alias: str = ""
    need_valid_ssl: bool = True
    child_id: int = 0
    echinfo: str = ""
    resolve_ip: bool = False
    has_server_domain: bool = False

    cert: CertVar = Field(default_factory=CertVar.empty)
    download: DomainIPVar | None = None
    dst_server: str | None = None
    extra_params: JsonMap = Field(default_factory=JsonMap)

    custom_proxy_ids: set[int] = Field(default_factory=set)

    @field_validator("extra_params", mode="before")
    @classmethod
    def _coerce_extra_params(cls, value: object) -> JsonMap:
        return JsonMap.from_any(value)

    @property
    def extra(self) -> JsonMap:
        """Alias for ``extra_params`` (legacy templates)."""
        return self.extra_params

    @property
    def special(self) -> bool:
        return self.fake_mode == FakeMode.reality

    def is_reality(self) -> bool:
        return self.fake_mode == FakeMode.reality

    def is_fake_tls(self) -> bool:
        return self.fake_mode == FakeMode.fake

    def is_sub_link_only(self) -> bool:
        return self.mode == DomainType.sub_link_only

    def uses_public_edge_tls(self) -> bool:
        """CDN/worker: the client sees the CDN edge cert, not the origin cert in tls_store."""
        return self.mode in (DomainType.cdn, DomainType.worker)

    def has_domain_fronting(self) -> bool:
        if not self.uses_public_edge_tls():
            return False
        sni = (self.sni or "").strip().lower()
        name = (self.name or "").strip().lower()
        return bool(sni) and sni != name

    @property
    def allow_insecure(self) -> bool:
        if self.uses_public_edge_tls():
            # Pin only the probed edge cert when SNI is a fronting hostname.
            return self.has_domain_fronting()
        if self.cert is None:
            return False
        return (not self.cert.valid_cert) or self.cert.self_signed

    @classmethod
    def from_name(cls, name: str, *, child_id: int = 0) -> DomainIPVar:
        hostname = str(name or "example.com").strip().lower()
        return cls(
            name=hostname,
            host=hostname,
            sni=hostname,
            mode=DomainType.direct,
            fake_mode=FakeMode.valid,
            child_id=child_id,
        )

    @classmethod
    def from_domain(cls, domain_db: Domain) -> DomainIPVar:

        extracted_data = sni_host_ip_extractor(domain_db)
        hostname = str(domain_db.domain or "").lower()
        sni = extracted_data["sni"] or hostname
        extra = JsonMap.from_any(domain_db.extra_params_json())
        ips = get_ips(domain_db)
        server_host = domain_db.get_server()
        cert = _client_cert_for_domain(domain_db, hostname=hostname, sni=sni, connect_host=server_host or hostname)
        var = cls(
            id=domain_db.id,
            name=hostname,
            host=extracted_data["host"] or hostname,
            sni=sni,
            dst_server=server_host,
            mode=domain_db.mode,
            fake_mode=domain_db.fake_mode,
            alias=domain_db.alias or domain_db.name,
            need_valid_ssl=bool(domain_db.need_valid_ssl),
            child_id=int(domain_db.child_id or 0),
            echinfo=_resolve_domain_ech(domain_db),
            cert=cert,
            extra_params=extra,
            resolve_ip=bool(domain_db.resolve_ip),
            has_server_domain=bool(domain_db.usable_server_domain()),
            custom_proxy_ids=set(domain_db.custom_proxy_ids),
            ips=ips,
        )
        if domain_db.download_domain:
            var.download = cls.from_domain(domain_db.download_domain)
        else:
            # Same-domain download without a self-reference (breaks pydantic model_dump).
            var.download = var.model_copy(update={"download": None})

        return var

    def server(self, force_ip: bool = False) -> str:
        dst_domain = self.dst_server if isinstance(self.dst_server, str) and self.dst_server else (self.host or self.name or "")
        if self.has_server_domain:
            return dst_domain
        if is_ip_address(dst_domain):
            return strip_ip_brackets(dst_domain)
        if force_ip or self.resolve_ip or self.fake_mode != FakeMode.valid:
            return prefer_ipv4_server(self.ips, dst_domain)
        return dst_domain

    @property
    def ip_version(self) -> str:
        """IP4/IP6 when this outbound's server is an address, else empty."""
        return ip_version_label(self.server())


def cap_ipvar(ips: IPVar, *, only_ipv4: bool = False, max_per_version: int = DEFAULT_MAX_PROXY_IPS_PER_VERSION) -> IPVar:
    limit = max(1, int(max_per_version or DEFAULT_MAX_PROXY_IPS_PER_VERSION))
    v4 = list(ips.ipsv4)[:limit]
    v6 = [] if only_ipv4 else list(ips.ipsv6)[:limit]
    return IPVar(ipsv4=set(v4), ipsv6=set(v6))


def prefer_ipv4_server(ips: IPVar | None, fallback: str) -> str:
    if ips:
        if ips.ipsv4:
            return sorted(ips.ipsv4)[0]
        if ips.ipsv6:
            return sorted(ips.ipsv6)[0]
    return fallback


def strip_ip_brackets(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("[") and text.endswith("]"):
        return text[1:-1]
    return text


def is_ip_address(value: str | None) -> bool:
    text = strip_ip_brackets(str(value or ""))
    if not text:
        return False
    try:
        ipaddress.ip_address(text)
        return True
    except ValueError:
        return False


def ip_version_label(host: str) -> str:
    ips = hutils.network.get_domain_ips_cached(host)
    has_ipv4 = any(isinstance(ip, ipaddress.IPv4Address) for ip in ips)
    has_ipv6 = any(isinstance(ip, ipaddress.IPv6Address) for ip in ips)
    if has_ipv4 and has_ipv6:
        return "IP4/6"
    if has_ipv4:
        return "IP4"
    if has_ipv6:
        return "IP6"
    return ""


def server_ip_candidates(domain: DomainIPVar) -> list[tuple[str, str]]:
    ips = domain.ips or IPVar.empty()
    out: list[tuple[str, str]] = []
    for ip in sorted(ips.ipsv4):
        out.append(("ip4", ip))
    for ip in sorted(ips.ipsv6):
        out.append(("ip6", ip))
    return out


def expand_sni_domain_servers(domain: DomainIPVar) -> list[DomainIPVar]:
    """One client domain per server IP when no ``server_domain`` is bound."""
    if domain.has_server_domain:
        return [domain]

    candidates = server_ip_candidates(domain)
    if not candidates:
        return [domain]

    multi = len(candidates) > 1
    expanded: list[DomainIPVar] = []
    for version, ip in candidates:
        alias = (domain.alias or domain.name or "").strip()
        if multi and alias:
            alias = f"{alias} {version}"
        update: dict = {
            "dst_server": ip,
            "has_server_domain": False,
        }
        if alias:
            update["alias"] = alias
        if not domain.resolve_ip:
            update["ips"] = IPVar.from_strings(ip)
        expanded.append(domain.model_copy(update=update))
    return expanded


def get_ips(domain_db: Domain) -> IPVar:
    ips = IPVar.empty()
    if sd := domain_db.usable_server_domain():
        ips.merge(hutils.network.get_domain_ips_cached(sd.domain))
    else:
        forced = _ips_from_forced_hosts(domain_db)
        if forced.ips:
            ips.merge(forced)
        elif domain_db.fake_mode != FakeMode.valid:
            ips.merge(hutils.network.get_ips())
        elif domain_db.mode.name_is_real():
            hostname = str(domain_db.domain or "")
            if hostname and "*" not in hostname:
                ips.merge(hutils.network.get_domain_ips_cached(hostname))
            if not ips.ips and domain_db.mode.is_direct():
                ips.merge(hutils.network.get_ips())
        elif domain_db.mode.is_direct():
            ips.merge(hutils.network.get_ips())

    return cap_ipvar(ips, only_ipv4=hconfig(ConfigEnum.only_ipv4), max_per_version=hconfig(ConfigEnum.max_proxy_ips_per_version))


def _ips_from_forced_hosts(domain_db: Domain) -> IPVar:
    ips = IPVar.empty()
    raw = str(domain_db.cdn_ip or "").strip()
    if not raw:
        return ips
    for token in _FORCED_HOST_SPLIT.split(raw):
        host = token.strip()
        if not host:
            continue
        parsed = IPVar.from_strings(host)
        if parsed.ips:
            ips.merge(parsed)
            continue
        if "." not in host and ":" not in host:
            continue
        ips.merge(hutils.network.get_domain_ips_cached(host))
    return ips


def _client_cert_for_domain(domain_db: Domain, *, hostname: str, sni: str, connect_host: str) -> CertVar:
    """Client TLS material: origin cert, except CDN/worker which must not pin origin.

    Domain fronting (SNI != hostname) probes the edge leaf and pins that instead.
    """
    origin = CertVar.for_domain(domain_db)
    if domain_db.fake_mode != FakeMode.valid:
        return origin
    if domain_db.mode not in (DomainType.cdn, DomainType.worker):
        return origin

    fronting = bool(sni) and sni.strip().lower() != (hostname or "").strip().lower()
    if not fronting:
        return origin.model_copy(update={"pinnedPeerCertSha256": [], "public_key_sha256": ""})
    pin, spki = hutils.network.get_tls_peer_pins(connect_host, sni)
    if not pin:
        return origin.model_copy(update={"pinnedPeerCertSha256": [], "public_key_sha256": ""})
    return origin.model_copy(update={"pinnedPeerCertSha256": [pin], "public_key_sha256": spki or ""})


def sni_host_ip_extractor(domain_db: Domain) -> _ExtractedSniHost:
    sni = host = domain_db.domain.replace("*", hutils.random.get_random_string(5, 15))
    if all_snis := split_pattern.split((domain_db.servernames or "").strip()):
        if domain_db.fake_mode == FakeMode.reality:
            sni = all_snis[0]
        else:
            sni = random_or_none(all_snis) or sni

    return {"sni": sni, "host": host}


def _resolve_domain_ech(domain_db: Domain) -> str:
    if not domain_db.ech or not domain_db.mode.is_cdn():
        return ""

    hostname = str(domain_db.domain or "").replace("*", hutils.random.get_random_string(5, 15))
    if not hostname:
        return ""
    return hutils.network.get_ech_info(hostname) or ""
