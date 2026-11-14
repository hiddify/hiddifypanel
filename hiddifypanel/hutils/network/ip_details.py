"""Everything known about a server's IP address, for the dashboard's node info sheet, from open sources only:

- location and AS: the panel's own GeoLite2 databases (``ip_lookup``), no request;
- network owner, range, abuse contact, registration dates: RDAP (RFC 9083), the regional registries' own open
  protocol, at the registry IANA's bootstrap files name for the address;
- reverse DNS: this server's resolver;
- Tor exit: the Tor Project's public exit list;
- hosting / datacenter networks: brianhama/bad-asn-list (MIT), plus the AS name;
- the company's logo: the favicon of the company's own website.

An address's answer is kept 72 hours (``TTL``), so opening the sheet again does not ask anyone; the lists and the
registries' bootstrap files are kept as long.
"""

from __future__ import annotations

import base64
import ipaddress
import json
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from loguru import logger

TTL = 72 * 3600
_TIMEOUT = 8
_UA = {"User-Agent": "HiddifyPanel (node info)", "Accept": "application/rdap+json, application/json"}
_KEY = "ipdetails:v1"

_BOOTSTRAP = {"v4": "https://data.iana.org/rdap/ipv4.json", "v6": "https://data.iana.org/rdap/ipv6.json", "asn": "https://data.iana.org/rdap/asn.json"}
_TOR_LIST = "https://check.torproject.org/torbulkexitlist"
_HOSTING_ASNS = "https://raw.githubusercontent.com/brianhama/bad-asn-list/master/bad-asn-list.csv"

# An AS name that says what kind of network it is (the list above does not know every host)
_HOSTING_WORDS = re.compile(
    r"host|cloud|data ?cent|datacenter|server|vps|colo|dedicated|compute|ovh|hetzner|digitalocean|linode|vultr|choopa|"
    r"amazon|aws|google|microsoft|azure|oracle|alibaba|tencent|scaleway|online sas|contabo|leaseweb|m247|akamai|"
    r"cloudflare|fastly|ionos|hostinger|godaddy|kamatera|upcloud|netcup|aeza|stark industries|psychz|quadranet",
    re.I,
)
_MOBILE_WORDS = re.compile(r"mobile|wireless|cellular|\blte\b|\b[345]g\b|mobil|irancell|mtn|vodafone|t-mobile|verizon wireless", re.I)


def _redis():
    from hiddifypanel.cache import redis_client

    return redis_client


def _get_json(url: str) -> dict | None:
    try:
        res = requests.get(url, headers=_UA, timeout=_TIMEOUT)
        if res.status_code == 200:
            return res.json()
    except Exception as exc:
        logger.debug(f"ip details: {url}: {exc}")
    return None


def _kept(name: str, fetch, ttl: int = TTL):
    """``fetch()`` once per ``ttl`` (a failed fetch is tried again after 10 minutes)."""
    key = f"{_KEY}:{name}"
    cached = _redis().get(key)
    if cached is not None:
        return json.loads(cached)
    value = fetch()
    _redis().set(key, json.dumps(value), ex=ttl if value else 600)
    return value


# --- open lists --------------------------------------------------------------------------------------------------
def _tor_exits() -> list[str]:
    def fetch():
        try:
            res = requests.get(_TOR_LIST, timeout=_TIMEOUT)
            return [line.strip() for line in res.text.splitlines() if line.strip() and not line.startswith("#")] if res.ok else []
        except Exception:
            return []

    return _kept("tor", fetch)


def _hosting_asns() -> dict[str, str]:
    def fetch():
        try:
            res = requests.get(_HOSTING_ASNS, timeout=_TIMEOUT)
            if not res.ok:
                return {}
            out = {}
            for line in res.text.splitlines()[1:]:
                num, _, name = line.partition(",")
                if num.strip().isdigit():
                    out[num.strip()] = name.strip().strip('"')
            return out
        except Exception:
            return {}

    return _kept("hosting-asns", fetch)


# --- RDAP --------------------------------------------------------------------------------------------------------
def _rdap_base(kind: str, value: str) -> str:
    """The registry that serves ``value`` (an address or an AS number), from IANA's bootstrap file."""
    services = _kept(f"bootstrap-{kind}", lambda: (_get_json(_BOOTSTRAP[kind]) or {}).get("services") or [], ttl=7 * 24 * 3600)
    if kind == "asn":
        number = int(value)
        for ranges, urls in services:
            for item in ranges:
                low, _, high = item.partition("-")
                if int(low) <= number <= int(high or low):
                    return urls[0]
        return ""
    ip = ipaddress.ip_address(value)
    best, best_len = "", -1
    for prefixes, urls in services:
        for prefix in prefixes:
            net = ipaddress.ip_network(prefix, strict=False)
            if ip.version == net.version and ip in net and net.prefixlen > best_len:
                best, best_len = urls[0], net.prefixlen
    return best


def _vcard(entity: dict) -> dict:
    out: dict[str, str] = {}
    for item in (entity.get("vcardArray") or [None, []])[1]:
        if not isinstance(item, list) or len(item) < 4:
            continue
        name, params, value = item[0], item[1] or {}, item[3]
        if name == "fn" and not out.get("name"):
            out["name"] = str(value)
        elif name == "email" and not out.get("email"):
            out["email"] = str(value)
        elif name == "tel" and not out.get("phone"):
            out["phone"] = str(value).removeprefix("tel:")
        elif name == "adr" and not out.get("address"):
            label = params.get("label") if isinstance(params, dict) else ""
            parts = [str(p) for p in value if p] if isinstance(value, list) else []
            out["address"] = " ".join(str(label or ", ".join(parts)).split())
    return out


def _entities(obj: dict):
    for entity in obj.get("entities") or []:
        yield entity
        yield from _entities(entity)


def _events(obj: dict) -> dict:
    return {e.get("eventAction"): (e.get("eventDate") or "")[:10] for e in obj.get("events") or [] if e.get("eventAction")}


def _rdap_ip(ip: str) -> dict:
    base = _rdap_base("v6" if ":" in ip else "v4", ip)
    data = _get_json(f"{base.rstrip('/')}/ip/{ip}") if base else None
    if not data:
        return {}
    owner: dict = {}
    abuse: dict = {}
    for entity in _entities(data):
        roles = entity.get("roles") or []
        card = _vcard(entity)
        if "abuse" in roles and not abuse.get("email"):
            abuse = card
        # the registrant that has an address is the organisation (RIPE also lists the maintainer as a registrant)
        if "registrant" in roles and (card.get("address") or not owner):
            owner = card
    cidrs = [f"{c.get('v4prefix') or c.get('v6prefix')}/{c.get('length')}" for c in data.get("cidr0_cidrs") or [] if c.get("length") is not None]
    events = _events(data)
    port43 = str(data.get("port43") or "")
    rir = next((r for r in ("RIPE", "ARIN", "APNIC", "LACNIC", "AFRINIC") if r.lower() in (port43 + base).lower()), "")
    return {
        "netname": str(data.get("name") or ""),
        "handle": str(data.get("handle") or ""),
        "range": f"{data.get('startAddress')} - {data.get('endAddress')}" if data.get("startAddress") else "",
        "cidr": ", ".join(cidrs),
        "type": str(data.get("type") or ""),
        "country": str(data.get("country") or ""),
        "rir": rir,
        "registered": events.get("registration", ""),
        "updated": events.get("last changed", ""),
        "owner": owner,
        "abuse": abuse,
    }


def _rdap_asn(asn: str) -> dict:
    number = asn.removeprefix("AS")
    if not number.isdigit():
        return {}

    def fetch():
        base = _rdap_base("asn", number)
        data = _get_json(f"{base.rstrip('/')}/autnum/{number}") if base else None
        if not data:
            return {}
        owner = next((_vcard(e) for e in _entities(data) if "registrant" in (e.get("roles") or []) and _vcard(e).get("name")), {})
        events = _events(data)
        return {"name": str(data.get("name") or ""), "org": owner.get("name", ""), "country": str(data.get("country") or ""), "registered": events.get("registration", ""), "updated": events.get("last changed", "")}

    return _kept(f"asn:{number}", fetch)


# --- the company's logo ------------------------------------------------------------------------------------------
_LOGO_MAX = 64 * 1024


def company_domain(*emails: str) -> str:
    """The company's website, from its contact addresses (abuse@scaleway.com → scaleway.com)."""
    for email in emails:
        domain = (email or "").rpartition("@")[2].strip().lower()
        if "." in domain and not re.search(r"ripe\.net|arin\.net|apnic\.net|lacnic\.net|afrinic\.net", domain):
            return domain
    return ""


def logo(domain: str) -> str:
    """A data: URL of the website's own icon, or "" (the sheet draws the company's initial then)."""
    if not domain:
        return ""

    def fetch():
        for path in ("/apple-touch-icon.png", "/favicon.ico"):
            for host in (domain, f"www.{domain}"):
                try:
                    res = requests.get(f"https://{host}{path}", timeout=5, headers={"User-Agent": _UA["User-Agent"]}, allow_redirects=True)
                except Exception:
                    continue
                kind = res.headers.get("content-type", "").split(";")[0].strip()
                if res.ok and kind.startswith("image/") and 0 < len(res.content) <= _LOGO_MAX:
                    return f"data:{kind};base64,{base64.b64encode(res.content).decode()}"
        return ""

    return _kept(f"logo:{domain}", fetch)


# --- one address ---------------------------------------------------------------------------------------------------
def _ptr(ip: str) -> str:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return ""


def _detect(ip: str, asn: str, org: str, rdap: dict) -> dict:
    addr = ipaddress.ip_address(ip)
    names = " ".join([org, rdap.get("netname", ""), rdap.get("owner", {}).get("name", "")])
    listed = asn.removeprefix("AS") in _hosting_asns()
    datacenter = listed or bool(_HOSTING_WORDS.search(names))
    mobile = not datacenter and bool(_MOBILE_WORDS.search(names))
    return {
        "datacenter": datacenter,
        "datacenter_listed": listed,
        # websites (and paid IP databases) treat datacenter addresses as VPN / proxy servers
        "vpn_likely": datacenter,
        "tor": ip in set(_tor_exits()),
        "mobile": mobile,
        "residential": not datacenter and not mobile and not addr.is_private,
        "bogon": not addr.is_global,
    }


def _describe(ip: str) -> dict:
    from hiddifypanel.hutils.network import ip_lookup

    geo = ip_lookup.lookup(ip)
    rdap = _rdap_ip(ip) if ipaddress.ip_address(ip).is_global else {}
    asn = geo.get("asn", "")
    owner = rdap.get("owner", {})
    abuse = rdap.get("abuse", {})
    domain = company_domain(abuse.get("email", ""), owner.get("email", ""))
    return {
        "ip": ip,
        "version": ipaddress.ip_address(ip).version,
        "ptr": _ptr(ip),
        "geo": geo,
        "network": rdap,
        "asn": {"asn": asn, "org": geo.get("org", ""), **_rdap_asn(asn)} if asn else {},
        "company": {"name": owner.get("name") or geo.get("org", ""), "domain": domain, "logo": logo(domain)},
        "detect": _detect(ip, asn, geo.get("org", ""), rdap),
        "fetched_at": int(time.time()),
    }


def describe(ip: str, refresh: bool = False) -> dict:
    """What is known about ``ip``, kept ``TTL`` (72 hours)."""
    key = f"{_KEY}:ip:{ip}"
    if not refresh:
        cached = _redis().get(key)
        if cached is not None:
            return json.loads(cached)
    info = _describe(ip)
    _redis().set(key, json.dumps(info), ex=TTL)
    return info


def describe_all(ips: list[str], refresh: bool = False) -> list[dict]:
    """Several addresses at once (each one's lookups run side by side, in the app's context for its cache)."""
    from flask import current_app

    if not ips:
        return []
    app = current_app._get_current_object()

    def one(ip: str) -> dict:
        with app.app_context():
            return describe(ip, refresh)

    with ThreadPoolExecutor(max_workers=min(4, len(ips))) as pool:
        return list(pool.map(one, ips))


def ttl_left(ip: str) -> int:
    left = _redis().ttl(f"{_KEY}:ip:{ip}")
    return int(left) if isinstance(left, int) and left > 0 else 0

