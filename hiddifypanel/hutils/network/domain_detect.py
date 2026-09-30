"""Guess how a domain should be used on this panel: direct, CDN (and which one) or REALITY.

Order of evidence: the domain resolves to this server -> direct; its IPs are in a CDN's
published ranges, or the IP owner (GeoLite2 ASN, when installed) is a known CDN, or an HTTPS
response carries a CDN's headers -> cdn; otherwise it is someone else's site -> reality.
"""

from __future__ import annotations

import ipaddress
from dataclasses import asdict, dataclass, field

import requests
from loguru import logger

from hiddifypanel.cache import cache

# Published, stable ranges (Cloudflare: cloudflare.com/ips, Fastly: api.fastly.com/public-ip-list,
# ArvanCloud: arvancloud.ir/fa/ips.txt). Akamai/CloudFront/others are too large or dynamic: they are
# recognised by ASN owner or response headers instead.
_CDN_RANGES: dict[str, tuple[str, ...]] = {
    "Cloudflare": (
        "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22", "141.101.64.0/18",
        "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20", "197.234.240.0/22", "198.41.128.0/17",
        "162.158.0.0/15", "104.16.0.0/13", "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
        "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32", "2405:b500::/32", "2405:8100::/32",
        "2a06:98c0::/29", "2c0f:f248::/32",
    ),
    "Fastly": (
        "23.235.32.0/20", "43.249.72.0/22", "103.244.50.0/24", "103.245.222.0/23", "103.245.224.0/24",
        "104.156.80.0/20", "140.248.64.0/18", "140.248.128.0/17", "146.75.0.0/17", "151.101.0.0/16",
        "157.52.64.0/18", "167.82.0.0/17", "167.82.128.0/20", "167.82.160.0/20", "167.82.224.0/20",
        "172.111.64.0/18", "185.31.16.0/22", "199.27.72.0/21", "199.232.0.0/16",
        "2a04:4e40::/32", "2a04:4e42::/32",
    ),
    "ArvanCloud": ("185.143.232.0/22", "185.215.232.0/22", "94.101.182.0/27", "2.144.3.128/28", "89.45.48.64/28"),
}
_CDN_NETWORKS = {name: tuple(ipaddress.ip_network(r) for r in ranges) for name, ranges in _CDN_RANGES.items()}

# Substrings of the ASN owner (GeoLite2-ASN "autonomous_system_organization").
_CDN_ASN_ORGS: tuple[tuple[str, str], ...] = (
    ("cloudflare", "Cloudflare"),
    ("fastly", "Fastly"),
    ("akamai", "Akamai"),
    ("arvan", "ArvanCloud"),
    ("abrarvan", "ArvanCloud"),
    ("cloudfront", "CloudFront"),
    ("g-core", "Gcore"),
    ("gcore", "Gcore"),
    ("bunny", "BunnyCDN"),
    ("datacamp", "CDN77"),
    ("cdn77", "CDN77"),
    ("edgecast", "Edgio"),
    ("edgio", "Edgio"),
    ("limelight", "Edgio"),
    ("stackpath", "StackPath"),
    ("incapsula", "Imperva"),
    ("imperva", "Imperva"),
    ("sucuri", "Sucuri"),
    ("derak", "Derak Cloud"),
    ("verizon digital media", "Edgio"),
)

# (header, substring or "" for mere presence, provider)
_CDN_HEADERS: tuple[tuple[str, str, str], ...] = (
    ("cf-ray", "", "Cloudflare"),
    ("server", "cloudflare", "Cloudflare"),
    ("x-served-by", "cache-", "Fastly"),
    ("x-fastly-request-id", "", "Fastly"),
    ("server", "akamaighost", "Akamai"),
    ("x-akamai-transformed", "", "Akamai"),
    ("server", "arvancloud", "ArvanCloud"),
    ("ar-poweredby", "", "ArvanCloud"),
    ("x-amz-cf-id", "", "CloudFront"),
    ("via", "cloudfront", "CloudFront"),
    ("server", "bunnycdn", "BunnyCDN"),
    ("x-sucuri-id", "", "Sucuri"),
    ("x-iinfo", "", "Imperva"),
    ("server", "gcore", "Gcore"),
    ("server", "cdn77", "CDN77"),
    ("server", "derak", "Derak Cloud"),
)


@dataclass
class DomainDetection:
    domain: str
    mode: str  # direct | cdn | reality | unresolved
    cdn: str | None = None
    ips: list[str] = field(default_factory=list)
    reason: str = ""  # server_ip | cdn_range | cdn_asn | cdn_header | external | no_dns
    reality_friendly: bool | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _cdn_by_range(ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address]) -> str | None:
    for ip in ips:
        for name, networks in _CDN_NETWORKS.items():
            if any(ip.version == net.version and ip in net for net in networks):
                return name
    return None


def _cdn_by_asn(ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address]) -> str | None:
    from hiddifypanel.hutils.network import maxmind

    for ip in ips:
        try:
            org = (maxmind.get_ip_info(str(ip)).asn_org or "").lower()
        except Exception:
            return None
        if not org or org == "unknown":
            continue
        for needle, name in _CDN_ASN_ORGS:
            if needle in org:
                return name
    return None


def _cdn_by_headers(domain: str) -> str | None:
    try:
        # Only the headers matter; no redirects, short timeout, any certificate.
        res = requests.head(f"https://{domain}/", timeout=4, allow_redirects=False, verify=False)
    except requests.RequestException:
        return None
    headers = {k.lower(): str(v).lower() for k, v in res.headers.items()}
    for header, needle, name in _CDN_HEADERS:
        value = headers.get(header)
        if value is not None and (not needle or needle in value):
            return name
    return None


@cache.cache(ttl=600)
def detect_domain(domain: str) -> dict:
    from hiddifypanel import hutils

    name = (domain or "").strip().lower().strip("[]")
    server_ips = set(hutils.network.get_ips())
    try:
        literal = ipaddress.ip_address(name)
        return DomainDetection(name, "direct" if literal in server_ips else "unresolved", ips=[name], reason="server_ip" if literal in server_ips else "no_dns").to_dict()
    except ValueError:
        pass

    ips = sorted(hutils.network.get_domain_ips_cached(name), key=str)
    if not ips:
        return DomainDetection(name, "unresolved", reason="no_dns").to_dict()
    shown = [str(ip) for ip in ips]
    if any(ip in server_ips for ip in ips):
        return DomainDetection(name, "direct", ips=shown, reason="server_ip").to_dict()
    for finder, reason in ((_cdn_by_range, "cdn_range"), (_cdn_by_asn, "cdn_asn")):
        if cdn := finder(ips):
            return DomainDetection(name, "cdn", cdn=cdn, ips=shown, reason=reason).to_dict()
    if cdn := _cdn_by_headers(name):
        return DomainDetection(name, "cdn", cdn=cdn, ips=shown, reason="cdn_header").to_dict()
    try:
        friendly = bool(hutils.network.is_domain_reality_friendly(name))
    except Exception as err:
        logger.debug(f"reality check failed for {name}: {err}")
        friendly = None
    return DomainDetection(name, "reality", ips=shown, reason="external", reality_friendly=friendly).to_dict()
