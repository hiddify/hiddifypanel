import base64
import glob
import ipaddress
import os
import random
import re
import socket
import ssl
import time
import urllib.request
from typing import Literal
from urllib.parse import urlparse

import dns.resolver
import psutil
import requests
from dns.rdtypes.svcbbase import ECHParam

from hiddifypanel.cache import cache
from hiddifypanel.hutils.network import maxmind
from hiddifypanel.models import *


def get_domain_ip_old(domain: str, retry: int = 3, version: Literal[4, 6] | None = None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    res = None
    if not version:
        try:
            res = socket.gethostbyname(domain)
        except BaseException:
            pass

    if not res and version != 6:
        try:
            res = socket.getaddrinfo(domain, None, socket.AF_INET)[0][4][0]
        except BaseException:
            pass

    if not res and version != 4:
        try:
            res = f"{socket.getaddrinfo(domain, None, socket.AF_INET6)[0][4][0]}"

        except BaseException:
            pass

    if retry > 0:
        return get_domain_ip_old(domain, retry=retry - 1, version=version)

    if not res:
        return None
    return ipaddress.ip_address(res)


def get_domain_ip(domain: str, retry: int = 3, version: Literal[4, 6] | None = None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    ips = get_domain_ips_cached(domain)
    ips = [ip for ip in ips if version == None or (version == 4 and isinstance(ip, ipaddress.IPv4Address)) or (version == 6 and isinstance(ip, ipaddress.IPv6Address))]
    if ips:
        return random.sample(ips, 1)[0]
    return get_domain_ip_old(domain, 0)


@cache.cache(300)
def get_domain_ips_cached(domain: str, retry: int = 3) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        return set(ipaddress.ip_address(domain))
    except:  # if not ip
        return get_domain_ips(domain, retry)


def get_domain_ips(domain: str, retry: int = 3) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    res = set()
    if retry < 0:
        return res
    try:
        _, _, ips = socket.gethostbyname_ex(domain)
        for ip in ips:
            res.add(ipaddress.ip_address(ip))
    except Exception:
        pass

    try:
        for ip in socket.getaddrinfo(domain, None, socket.AF_INET):
            res.add(ipaddress.ip_address(ip[4][0]))
    except BaseException:
        pass

    try:
        for ip in socket.getaddrinfo(domain, None, socket.AF_INET6):
            res.add(ipaddress.ip_address(ip[4][0]))
    except BaseException:
        pass

    return res or get_domain_ips(domain, retry=retry - 1)


def get_socket_public_ip(version: Literal[4, 6]) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if version == 6:
            s.connect(("2001:4860:4860::8888", 80))
        else:
            s.connect(("8.8.8.8", 80))
        ip_address = ipaddress.ip_address(s.getsockname()[0])
        s.close()
        return ip_address if ip_address.is_global else None
    except OSError:
        return None


def get_interface_public_ip(version: Literal[4, 6]) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    addresses = []
    try:
        interfaces = psutil.net_if_addrs()
        for interface_addresses in interfaces.values():
            for addr in interface_addresses:
                if version == 4 and addr.family == socket.AF_INET:
                    ip = addr.address
                elif version == 6 and addr.family == socket.AF_INET6:
                    ip = addr.address
                else:
                    continue

                try:
                    ip_obj = ipaddress.ip_address(ip.split("%")[0])  # Remove scope_id for IPv6
                    if ip_obj.is_global:
                        addresses.append(ip_obj)
                except ValueError:
                    continue

        return addresses

    except (OSError, KeyError):
        return []


@cache.cache(ttl=600)
def get_ips(version: Literal[4, 6] | None = None) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    if not version:
        return [*get_ips(4), *get_ips(6)]
    addrs = []

    i_ips = get_interface_public_ip(version)
    if i_ips:
        addrs = i_ips

    s_ip = get_socket_public_ip(version)
    if s_ip:
        addrs.append(s_ip)

    # send request
    try:
        ip = urllib.request.urlopen(f"https://v{version}.ident.me/", timeout=2).read().decode("utf8")
        if ip:
            addrs.append(ipaddress.ip_address(ip))
    except BaseException:
        pass

    # remove duplicates
    return list(set(addrs))


@cache.cache(ttl=600)
def get_ip_str(version: Literal[4, 6], retry: int = 5) -> str | None:
    ip = get_ip(version, retry)
    if ip is None:
        return None
    return str(ip)


@cache.cache(ttl=600)
def get_ip(version: Literal[4, 6], retry: int = 5) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    ips = get_interface_public_ip(version)
    ip = None
    if ips:
        ip = random.sample(ips, 1)[0]

    if ip is None:
        ip = get_socket_public_ip(version)

    if ip is None:
        try:
            ip = urllib.request.urlopen(f"https://v{version}.ident.me/", timeout=2).read().decode("utf8")
            if ip:
                ip = ipaddress.ip_address(ip)
        except BaseException:
            pass
    if ip is None and retry > 0:
        ip = get_ip(version, retry=retry - 1)
    return ip


def get_random_user_agent():
    try:
        uas = requests.get(
            "https://cdn.jsdelivr.net/gh/microlinkhq/top-user-agents@master/src/index.json",
            timeout=5,
        ).json()
        if uas:
            return random.sample(uas, 1)[0]
    except BaseException:
        pass
    return "Mozilla/5.0"


_FALLBACK_DOMAINS = [
    "fa.wikipedia.org",
    "en.wikipedia.org",
    "wikipedia.org",
    "yahoo.com",
    "en.yahoo.com",
    "msn.com",
    "fast.com",
    "speedtest.net",
    "flightradar24.com",
    "chess.com",
    "amazon.com",
    "google.com",
    "gstatic.com",
    "hcaptcha.com",
    "sourceforge.net",
    "github.com",
    "www.google.com",
    "dash.cloudflare.com",
    "cloudflare.com",
    "www.gstatic.com",
    "fonts.gstatic.com",
    "bbc.com",
    "www.wikipedia.org",
]


def get_random_domains(count: int = 1, retry: int = 2) -> list[str]:
    """Pick random domains for decoy/reality.

    Network calls are hard-capped so a fresh ``init_db`` cannot hang for minutes
    when OONI/CDN is unreachable (common in Docker / restricted networks).
    """
    count = max(1, int(count))
    try:
        region = "CN" if retry < 2 else "IR"
        irurl = (
            "https://api.ooni.io/api/v1/measurements"
            f"?probe_cc={region}&test_name=web_connectivity"
            "&anomaly=false&confirmed=false&failure=false"
            f"&limit=100&offset={(2 - retry % 2) * 100}"
        )
        data_ir = requests.get(irurl, timeout=5).json()
        domains = [
            urlparse(d["input"]).netloc.lower()
            for d in data_ir.get("results", {})
            if d.get("scores", {}).get("blocking_country") == 0.0
        ]
        domains = [d for d in domains if d and not d.endswith(".ir") and ".gov" not in d]
        if len(domains) >= count:
            return random.sample(domains, count)
        if domains:
            padded = list(domains)
            while len(padded) < count:
                padded.append(random.choice(_FALLBACK_DOMAINS))
            return padded[:count]
        raise ValueError("OONI returned no usable domains")
    except BaseException as e:
        print("Error, getting random domains... ", e, "retrying...", retry)
        if retry <= 0:
            print("Error, using default domains")
            return random.sample(_FALLBACK_DOMAINS, min(count, len(_FALLBACK_DOMAINS)))
        return get_random_domains(count, retry - 1)


# not used
def is_domain_support_tls_13(domain: str) -> bool:
    context = ssl.create_default_context()
    port = 433
    with socket.create_connection((domain, port), timeout=2) as sock:
        with context.wrap_socket(sock, server_hostname=domain) as ssock:
            return ssock.version() == "TLSv1.3"


def is_domain_support_h2_tls13(sni: str, server: str = "") -> bool:
    try:
        context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
        context.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        context.options |= ssl.OP_NO_COMPRESSION
        context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20")
        context.set_alpn_protocols(["h2"])
        start_time = time.monotonic()
        with socket.create_connection((server or sni, 443), timeout=2) as sock:
            with context.wrap_socket(sock, server_hostname=sni) as ssock:
                elapsed_time = time.monotonic() - start_time
                valid = ssock.version() == "TLSv1.3"
                if valid:
                    if int(max(1, elapsed_time * 1000)):
                        return True
                return False
    except Exception as e:
        print(f"{sni} {e}")
        return False


def is_domain_reality_friendly(domain: str) -> bool:
    return is_domain_support_h2_tls13(domain)


def fallback_domain_compatible_with_servernames(fallback_domain: str, servername: str) -> bool:
    return is_domain_support_h2_tls13(servername, fallback_domain)


def get_random_decoy_domain() -> str:
    """Pick a Let's-Encrypt domain for decoy TLS.

    Prefer local fallbacks (bounded TLS probes) before calling OONI so ``_v1``
    init cannot stall ~10 minutes on a bad network.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _first_letsencrypt(domains: list[str]) -> str | None:
        if not domains:
            return None
        with ThreadPoolExecutor(max_workers=min(8, len(domains))) as executor:
            futures = {executor.submit(is_domain_use_letsencrypt, d): d for d in domains}
            for future in as_completed(futures):
                d = futures[future]
                try:
                    if future.result():
                        for f in futures:
                            f.cancel()
                        return d
                except BaseException:
                    continue
        return None

    local = random.sample(_FALLBACK_DOMAINS, min(8, len(_FALLBACK_DOMAINS)))
    found = _first_letsencrypt(local)
    if found:
        return found

    try:
        found = _first_letsencrypt(get_random_domains(8, retry=1))
        if found:
            return found
    except BaseException:
        pass

    return "www.wikipedia.org"


def is_domain_use_letsencrypt(domain: str) -> bool:
    """
    This function is used to filter the payment and big companies to
    avoid phishing detection
    """
    try:
        with socket.create_connection((domain, 443), timeout=2) as sock:
            context = ssl.create_default_context()
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                certificate = ssock.getpeercert()

        issuer = dict(x[0] for x in certificate.get("issuer", []))

        return issuer.get("organizationName") == "Let's Encrypt"
    except BaseException:
        return False


def pick_reality_friendly_domain(fallback: str = "yahoo.com") -> str:
    """Fast reality SNI/fallback picker for migrations (no long OONI loops)."""
    candidates = random.sample(_FALLBACK_DOMAINS, min(10, len(_FALLBACK_DOMAINS)))
    for d in candidates:
        if is_domain_reality_friendly(d):
            return d
    try:
        for d in get_random_domains(10, retry=1):
            if is_domain_reality_friendly(d):
                return d
    except BaseException:
        pass
    return fallback


@cache.cache(ttl=300)
def get_direct_host_or_ip(prefer_version: int) -> str:
    from hiddifypanel.models import Domain

    direct = Domain.query.filter(Domain.mode == DomainType.direct).first()
    if direct:
        return direct.domain

    direct = get_ip_str(prefer_version)
    if direct:
        return direct

    return get_ip_str(4 if prefer_version == 6 else 6)


# not used
def get_warp_info() -> str:
    proxies = dict(http="socks5://127.0.0.1:3000", https="socks5://127.0.0.1:3000")
    res = requests.get("https://cloudflare.com/cdn-cgi/trace", proxies=proxies, timeout=1).text

    dicres = {line.split("=")[0]: line.split("=")[0] for line in res}
    return str(dicres)


def is_ssh_password_authentication_enabled() -> bool:
    def check_file(file_path: str) -> bool:
        if os.path.isfile(file_path):
            try:
                with open(file_path) as f:
                    for line in f.readlines():
                        line = line.strip()
                        if line.startswith("#"):
                            continue
                        if re.search(r"^PasswordAuthentication\s+no", line, re.IGNORECASE):
                            return False
            except Exception as e:
                print(e)

        return True

    for config_file in glob.glob("/etc/ssh/sshd*") + glob.glob("/etc/ssh/sshd*/*"):
        if not check_file(config_file):
            return False

    return True


def is_out_of_range_port(port: int) -> bool:
    return port < 1 or port > 65535


def add_number_to_ipv4(ip: str, number: int) -> str:
    octets = list(map(int, ip.split(".")))

    octets[2] = octets[2] + (octets[3] + number) // 256
    octets[3] = (octets[3] + number) % 256

    return f"{octets[0]}.{octets[1]}.{octets[2]}.{octets[3]}"


def add_number_to_ipv6(ip: str, number: int) -> str:
    segments = ip.split(":")

    # Increment the last segment by the specified number
    segments[-1] = hex(int(segments[-1] or "0", 16) + number)[2:]

    # Join the segments back together with colons
    modified_ipv6 = ":".join(segments)

    return modified_ipv6


@cache.cache(600)
def is_in_same_asn(domain_or_ip: str, domain_or_ip_target: str) -> bool:
    """Returns True if domain is in panel ASN"""
    try:
        ip = domain_or_ip if is_ip(domain_or_ip) else get_domain_ip(domain_or_ip)
        ip_target = domain_or_ip_target if is_ip(domain_or_ip_target) else get_domain_ip(domain_or_ip_target)

        if not ip or not ip_target:
            return False

        ip_asn = get_ip_asn(ip)
        ip_target_asn = get_ip_asn(ip_target)

        if not ip_asn or not ip_target_asn:
            return False

        return ip_asn == ip_target_asn
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

        # hutils.flask.flash(_("domain.reality.asn_issue") +
        #                    f"<br> Server ASN={asn_ipv4.get('autonomous_system_organization','unknown')}<br>{domain}_ASN={asn_dip.get('autonomous_system_organization','unknown')}", "warning")


@cache.cache(600)
def get_ip_asn(ip: ipaddress.IPv4Address | ipaddress.IPv6Address | str) -> str:
    info = maxmind.get_ip_info(str(ip))
    if not info.db_available:
        return __get_ip_asn_api(ip)
    return "" if info.asn_org == "unknown" else info.asn_org


def __get_ip_asn_api(ip: ipaddress.IPv4Address | ipaddress.IPv6Address | str) -> str:
    ip = str(ip)
    if not is_ip(ip):
        return ""
    endpoint = f"https://ipapi.co/{ip}/asn/"
    return str(requests.get(endpoint).content)


@cache.cache(3600)
def is_ip(input: str):
    try:
        _ = ipaddress.ip_address(input)
        return True
    except:
        return False


def resolve_domain_with_api(domain: str) -> str:
    if not domain:
        return ""
    endpoint = f"http://ip-api.com/json/{domain}?fields=query"
    return str(requests.get(endpoint).json().get("query"))


@cache.cache(ttl=3600)
def get_tls_peer_pins(host: str, server_name: str, port: int = 443) -> tuple[str, str]:
    """Leaf cert SHA-256 hex and SPKI SHA-256 b64 as seen by a TLS client.

    Used for CDN domain-fronting pins (edge cert), not the origin cert on disk.
    """
    from hiddifypanel.proxy_v3.tls_store_sync import cert_sha256_hex_from_pem, public_key_sha256_from_pem

    connect_host = str(host or "").strip().strip("[]")
    sni = str(server_name or "").strip()
    if not connect_host or not sni or "*" in connect_host:
        return ("", "")
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        with socket.create_connection((connect_host, int(port or 443)), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=sni) as ssock:
                der = ssock.getpeercert(binary_form=True)
    except Exception:
        return ("", "")
    if not der:
        return ("", "")
    pem = ssl.DER_cert_to_PEM_cert(der)
    return (cert_sha256_hex_from_pem(pem) or "", public_key_sha256_from_pem(pem) or "")


@cache.cache(600)
def get_ech_info(domain: str) -> str | None:
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ["1.1.1.1"]  # Cloudflare DNS

        answers = resolver.resolve(domain, "HTTPS")
        for rdata in answers:
            for param in rdata.params.values():
                if isinstance(param, ECHParam):
                    ech_bytes = param.ech
                    return base64.b64encode(ech_bytes).decode()
    except BaseException:
        pass

    return None


def all_public_ports():
    tcp_ports = {80: "http", 443: "tls"}
    udp_ports = {
        443: "quic",
    }
    log = []
    if hconfig(ConfigEnum.wireguard_enable):
        udp_ports[hconfig(ConfigEnum.wireguard_port)] = "wireguard"

    if hconfig(ConfigEnum.shadowsocks2022_enable) and (p := hconfig(ConfigEnum.shadowsocks2022_port)):
        udp_ports[p] = "shadowsocks_2022"
        tcp_ports[p] = "shadowsocks_2022"
    if hconfig(ConfigEnum.mieru_enable):
        for p in hconfig(ConfigEnum.mieru_tcp_ports).split(","):
            tcp_ports[p] = "mieru"
        for p in hconfig(ConfigEnum.mieru_udp_ports).split(","):
            udp_ports[p] = "mieru"
    if hconfig(ConfigEnum.ssh_server_enable):
        tcp_ports[hconfig(ConfigEnum.ssh_server_port)] = "ssh"

    for p in (hconfig(ConfigEnum.tls_ports)).split(","):
        tcp_ports[p] = "tls"
        udp_ports[p] = "quic"
    for p in hconfig(ConfigEnum.http_ports).split(","):
        tcp_ports[p] = "http"

    for d in Domain.query.all():
        udp_ports[d.internal_port_tuic] = "tuic"
        udp_ports[d.internal_port_naive] = "naive"
        udp_ports[d.internal_port_hysteria2] = "hysteria"

    def to_int(ports):
        r = {}
        for p, v in ports.items():
            try:
                if ip := int(p):
                    r[ip] = v
            except:
                pass
        return {k: v for k, v in sorted(r.items())}

    return {"tcp": to_int(tcp_ports), "udp": to_int(udp_ports)}
