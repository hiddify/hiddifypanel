"""The "Complete IP Info" checks of a server's address, from open sources and free lists only (each one's terms allow a
commercial product to use it for free), plus three checks of the server itself:

- Tor: the Tor Project's Onionoo service (relays, exits, running now; its data is CC0);
- iCloud Private Relay: Apple's published egress ranges;
- crawlers: the IP ranges Google, Bing, Apple and OpenAI publish for their bots;
- abuse: the Spamhaus DROP lists (free for all; credit "The Spamhaus Project"; at most one download a day: kept a
  week here) and abuse.ch's Feodo Tracker and SSL Blacklist (CC0). Never Spamhaus's DNSBL (paid for commercial use);
- attackers: the NetAPI honeypot list, the addresses that attacked its sensors in the last 30 days (CC BY 4.0, free
  for commercial use; credit "NetAPI"). One public file is read: the server's address is sent to nobody;
- the server itself: its TLS certificates (port 443, each of its domains), an open directory listing on its web
  root, and the IPFS swarm port (4001);
- "likely" signs read from the AS, the network's names and the reverse DNS name (satellite, anycast, a dynamic
  line, a security scanner).

Every value is True, False, or None when it could not be checked. Lists are kept a week (``ip_details.TTL``).
"""

from __future__ import annotations

import ipaddress
import re
import socket
import ssl
import warnings
from datetime import datetime, timezone

import requests
from loguru import logger

_TIMEOUT = 8
_UA = {"User-Agent": "HiddifyPanel (node info)"}

_ONIONOO = "https://onionoo.torproject.org/details"
_APPLE_RELAY = "https://mask-api.icloud.com/egress-ip-ranges.csv"
_CRAWLERS = {
    "Google": "https://developers.google.com/static/search/apis/ipranges/googlebot.json",
    "Bing": "https://www.bing.com/toolbox/bingbot.json",
    "Apple": "https://search.developer.apple.com/applebot.json",
    "OpenAI": "https://openai.com/gptbot.json",
}
_DROP = ("https://www.spamhaus.org/drop/drop_v4.json", "https://www.spamhaus.org/drop/drop_v6.json")
_ABUSE_CH = ("https://feodotracker.abuse.ch/downloads/ipblocklist.txt", "https://sslbl.abuse.ch/blacklist/sslipblacklist.txt")
_NETAPI = "https://netapi.com/api2/?method=compromised&dataset_type=ip-all&window=30d"

# AS numbers of satellite internet providers (Starlink, Viasat, HughesNet, Inmarsat, OneWeb, Intelsat, Eutelsat…)
_SATELLITE_ASNS = {"14593", "7155", "6621", "31515", "800", "22351", "29286", "40306", "19571", "27277", "45474"}
_SATELLITE_WORDS = re.compile(r"starlink|spacex|viasat|hughes|inmarsat|oneweb|iridium|intelsat|eutelsat|skylogic|telesat|o3b|satellite", re.I)
# AS numbers that announce their addresses from many places at once (Cloudflare, Quad9, Fastly, OpenDNS, Google DNS…)
_ANYCAST_ASNS = {"13335", "209242", "19281", "54113", "36692", "42", "3856", "397213"}
_ANYCAST_WORDS = re.compile(r"anycast", re.I)
# reverse DNS names of home lines whose address changes
_DYNAMIC_PTR = re.compile(r"\b(dsl|adsl|vdsl|xdsl|dyn|dynamic|dhcp|pool|ppp|pppoe|cable|ftth|fttx|broadband|dialup|cust(omer)?)\b|\d{1,3}[-.]\d{1,3}[-.]\d{1,3}[-.]\d{1,3}", re.I)
_SCANNER_WORDS = re.compile(r"shodan|censys|shadowserver|rapid7|binaryedge|internet-?measurement|stretchoid|recyber|onyphe|leakix|criminalip|scan(ner|ning)?\b", re.I)
_DIRECTORY = re.compile(r"<title>\s*(index of /|directory listing for)", re.I)


def _kept(name: str, fetch):
    from hiddifypanel.hutils.network import ip_details

    return ip_details._kept(f"flags:{name}", fetch)


def _text(url: str) -> str:
    try:
        res = requests.get(url, headers=_UA, timeout=_TIMEOUT)
        return res.text if res.ok else ""
    except Exception as exc:
        logger.debug(f"ip flags: {url}: {exc}")
        return ""


def _in(ip: str, cidrs: list[str]) -> bool | None:
    """Whether ``ip`` is in one of ``cidrs``; None when the list could not be had."""
    if not cidrs:
        return None
    addr = ipaddress.ip_address(ip)
    for cidr in cidrs:
        try:
            net = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            continue
        if net.version == addr.version and addr in net:
            return True
    return False


# --- Tor -------------------------------------------------------------------------------------------------------------
def tor_relay(ip: str) -> dict | None:
    """The Tor relay on this address (its nickname, whether it runs now and is an exit), {} when none, None on error."""
    try:
        res = requests.get(_ONIONOO, params={"search": ip, "fields": "nickname,running,flags,exit_addresses"}, headers=_UA | {"Accept-Encoding": "gzip"}, timeout=_TIMEOUT)
        relays = res.json().get("relays", []) if res.ok else None
    except Exception:
        return None
    if relays is None:
        return None
    if not relays:
        return {}
    relay = relays[0]
    exits = relay.get("exit_addresses") or []
    return {"nickname": str(relay.get("nickname") or ""), "running": bool(relay.get("running")), "exit": "Exit" in (relay.get("flags") or []) or ip in exits}


# --- published ranges and lists ----------------------------------------------------------------------------------------
def _cidrs_in_json(value) -> list[str]:
    """Every "…Prefix" / "cidr" value in a published ranges file (each provider names them a little differently)."""
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str) and (key.lower().endswith("prefix") or key.lower() == "cidr"):
                found.append(item)
            else:
                found += _cidrs_in_json(item)
    elif isinstance(value, list):
        for item in value:
            found += _cidrs_in_json(item)
    return found


def _crawler(ip: str) -> str | None:
    """The search engine or AI company whose published bot ranges hold ``ip``, "" when none, None when none could be read."""
    got_any = False
    for name, url in _CRAWLERS.items():
        def fetch(url=url):
            try:
                res = requests.get(url, headers=_UA, timeout=_TIMEOUT)
                return _cidrs_in_json(res.json()) if res.ok else []
            except Exception:
                return []

        cidrs = _kept(f"crawler:{name}", fetch)
        if cidrs:
            got_any = True
            if _in(ip, cidrs):
                return name
    return "" if got_any else None


def _apple_relay(ip: str) -> bool | None:
    """Whether ``ip`` is an iCloud Private Relay egress address. Apple's file is large, so it is read as it streams in;
    the answer is kept with the rest of the address's details, so this runs once a week per address."""
    addr = ipaddress.ip_address(ip)
    try:
        with requests.get(_APPLE_RELAY, headers=_UA, timeout=20, stream=True) as res:
            if not res.ok:
                return None
            for line in res.iter_lines(decode_unicode=True):
                prefix = (line or "").split(",", 1)[0].strip()
                if not prefix or (":" in prefix) != (addr.version == 6):
                    continue
                try:
                    if addr in ipaddress.ip_network(prefix, strict=False):
                        return True
                except ValueError:
                    continue
        return False
    except Exception:
        return None


def _drop() -> list[str]:
    """Spamhaus DROP: netblocks hijacked or run by criminals ("The Spamhaus Project", free for all; a week here)."""

    def fetch():
        cidrs: list[str] = []
        for url in _DROP:
            for line in _text(url).splitlines():
                m = re.search(r'"cidr"\s*:\s*"([^"]+)"', line)
                if m:
                    cidrs.append(m.group(1))
        return cidrs

    return _kept("spamhaus-drop", fetch)


def _abuse_ch() -> list[str]:
    """abuse.ch Feodo Tracker and SSL Blacklist: botnet command servers (CC0). Either may be empty for a while."""

    def fetch():
        ips: list[str] = []
        fetched = False
        for url in _ABUSE_CH:
            text = _text(url)
            fetched = fetched or bool(text)
            for line in text.splitlines():
                token = line.strip().split(",", 1)[0]
                if token and not token.startswith("#"):
                    try:
                        ips.append(str(ipaddress.ip_address(token)))
                    except ValueError:
                        continue
        # an empty list that was read is an answer ("not listed"), unlike one that could not be read
        return ips or (["0.0.0.0/32"] if fetched else [])

    return _kept("abuse-ch", fetch)


def _attacker(ip: str) -> bool | None:
    """Whether ``ip`` attacked NetAPI's honeypot sensors in the last 30 days: logins tried, exploits sent (addresses
    that only scanned are not listed; IPv4 only). The list is over a megabyte, so, like Apple's, it is read as it
    streams in; the answer is kept with the rest of the address's details, so this runs once a week per address."""
    addr = ipaddress.ip_address(ip)
    if addr.version != 4:
        return False
    wanted = str(addr)
    read = False
    try:
        with requests.get(_NETAPI, headers=_UA, timeout=20, stream=True) as res:
            if not res.ok:
                return None
            for line in res.iter_lines():
                token = line.decode("ascii", "ignore").strip()
                if not token or token.startswith("#"):
                    continue
                read = True
                if token == wanted:
                    return True
        # an answer without a single address is not a list that was read
        return False if read else None
    except Exception:
        return None


# --- the server itself -------------------------------------------------------------------------------------------------
def _host(ip: str) -> str:
    return f"[{ip}]" if ":" in ip else ip


def _ipfs(ip: str) -> bool | None:
    try:
        with socket.create_connection((ip, 4001), timeout=2.5):
            return True
    except (ConnectionRefusedError, socket.timeout, TimeoutError):
        return False
    except OSError:
        return None


def _open_directory(ip: str) -> bool | None:
    seen = False
    for scheme in ("http", "https"):
        try:
            # the server's own address: its certificate is for its domains, so it is not verified here
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = requests.get(f"{scheme}://{_host(ip)}/", headers=_UA, timeout=5, verify=False, allow_redirects=True)
        except Exception:
            continue
        seen = True
        if _DIRECTORY.search(res.text[:4000]):
            return True
    return False if seen else None


def _certificates(ip: str, domains: list[str]) -> list[dict]:
    """The TLS certificates the server hands out on 443: its default one and each of its domains' (up to five)."""
    from cryptography import x509

    out: list[dict] = []
    now = datetime.now(timezone.utc)
    seen: set[bytes] = set()
    for name in [None, *domains[:5]]:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            with socket.create_connection((ip, 443), timeout=4) as sock, ctx.wrap_socket(sock, server_hostname=name) as tls:
                der = tls.getpeercert(binary_form=True)
        except Exception:
            continue
        if not der or der in seen:
            continue
        seen.add(der)
        cert = x509.load_der_x509_certificate(der)
        ends = cert.not_valid_after_utc
        subject = next((a.value for a in cert.subject if a.oid == x509.NameOID.COMMON_NAME), "") or (name or "")
        out.append({"name": str(subject), "not_after": ends.date().isoformat(), "expired": ends < now})
    return out


# --- all of them -------------------------------------------------------------------------------------------------------
def check(ip: str, *, asn: str, names: str, ptr: str, datacenter: bool, mobile: bool, relay: dict | None, domains: list[str]) -> dict:
    """The flags of the "Complete IP Info" section, and what they were read from."""
    addr = ipaddress.ip_address(ip)
    public = addr.is_global
    number = asn.removeprefix("AS")
    crawler = _crawler(ip) if public else ""
    drop = _in(ip, _drop()) if public else False
    botnet = _in(ip, _abuse_ch()) if public else False
    attacker = _attacker(ip) if public else False
    certs = _certificates(ip, domains) if public else []
    icloud = _apple_relay(ip) if public else False
    tor = None if relay is None else bool(relay)
    flags = {
        # network and infrastructure
        "bogon": not public,
        "datacenter": datacenter,
        "mobile": mobile,
        "satellite": number in _SATELLITE_ASNS or bool(_SATELLITE_WORDS.search(names)),
        "anycast": number in _ANYCAST_ASNS or bool(_ANYCAST_WORDS.search(names)),
        "dsl_dynamic": not datacenter and bool(ptr) and bool(_DYNAMIC_PTR.search(ptr)),
        "ipfs": _ipfs(ip) if public else False,
        # anonymity and privacy
        "proxy": datacenter,
        "vpn": datacenter,
        "tor": tor,
        "relay": icloud,
        "anonymous": True if (tor or icloud) else (None if tor is None and icloud is None else False),
        "active_tor": None if relay is None else bool(relay and relay.get("running")),
        # behaviour and threats
        "crawler": None if crawler is None else bool(crawler),
        "abuser": None if drop is None and botnet is None and attacker is None else bool(drop or botnet or attacker),
        "known_abuser": drop,
        "threat": botnet,
        "attacker": attacker,
        "security_scanner": bool(_SCANNER_WORDS.search(f"{ptr} {names}")),
        # security and the web
        "tor_exit": None if relay is None else bool(relay and relay.get("exit")),
        "open_directory": _open_directory(ip) if public else False,
        "expired_certificate": any(c["expired"] for c in certs) if certs else None,
    }
    return {"flags": flags, "certificates": certs, "tor_relay": relay or {}, "crawler": crawler or ""}
