import ipaddress
import random
import re

from flask import has_request_context, request
from flask_babel import gettext as _

from hiddifypanel import hutils
from hiddifypanel.cache import STATIC, cache
from hiddifypanel.models.config import hconfig
from hiddifypanel.models.config_enum import ConfigEnum

from . import maxmind

#: Operator code of the CDN IP field for every operator that has no address of its own.
OTHER_OPERATOR = "OTHER"
#: An operator Hiddify has no name for, by its AS number ("AS12880").
AS_OPERATOR = re.compile(r"^AS\d+$")


def is_operator_code(token: str) -> bool:
    """Whether a token of the CDN IP field names who an address is for (a known operator, an AS number or OTHER)."""
    return token in maxmind.ASN_SHORT_NAMES or token == OTHER_OPERATOR or bool(AS_OPERATOR.match(token))


def operator_key(short_name: str, asn: str) -> str:
    """How the CDN IP field names this operator: its short name, else "AS<number>" ("" when neither is known)."""
    if short_name and short_name != "unknown":
        return short_name
    return f"AS{asn}" if asn and asn.isdigit() else ""

DEFAULT_IPs = """
mci.ircf.space		MCI
mcix.ircf.space		MCI
mtn.ircf.space		MTN
mtnx.ircf.space		MTN
mkh.ircf.space		MKH
mkhx.ircf.space		MKH
rtl.ircf.space		RTL
hwb.ircf.space		HWB
ast.ircf.space		AST
sht.ircf.space		SHT
prs.ircf.space		PRS
mbt.ircf.space		MBT
ask.ircf.space		ASK
rsp.ircf.space		RSP
afn.ircf.space		AFN
ztl.ircf.space		ZTL
psm.ircf.space		PSM
arx.ircf.space		ARX
smt.ircf.space		SMT
fnv.ircf.space		FNV
dbn.ircf.space		DBN
apt.ircf.space		APT
"""


def get_asn_short_name(user_ip: str = "") -> str:
    return maxmind.get_ip_info(user_ip or get_real_user_ip()).short_name


def get_asn_id(user_ip: str = "") -> str:
    return maxmind.get_ip_info(user_ip or get_real_user_ip()).asn


def get_country(user_ip: str = "") -> str:
    return maxmind.get_ip_info(user_ip or get_real_user_ip()).country


def get_real_user_ip_debug(user_ip: str = "") -> str:
    return __get_real_user_ip_debug_imp(user_ip or get_real_user_ip())


@cache.cache(modes=STATIC)
def __get_real_user_ip_debug_imp(user_ip: str) -> str:
    info = maxmind.get_ip_info(user_ip)
    default = __get_host_base_on_asn(DEFAULT_IPs, info.short_name).replace(".ircf.space", "")
    err = "ERROR" if info.short_name == "unknown" else ""
    return f"{info.ip} {info.country} {info.asn} {info.short_name} {err} fullname={info.asn_org} default:{default}"


def get_real_user_ip() -> str:
    if not has_request_context():
        return ""
    user_ip = request.remote_addr
    for header in ["CF-Connecting-IP", "ar-real-ip", "X-Forwarded-For", "X-Real-IP"]:
        if header in request.headers:
            user_ip = request.headers.get(header)
            break

    return str(user_ip)


def parse_operator_groups(text: str | list[str]) -> list[tuple[list[str], list[str]]]:
    """The CDN IP field as (addresses, operators) groups: addresses, then the codes they are for
    ("1.1.1.1,2606:4700::1111,104.16.0.0/24 MKH,AS254"). An address is an IP, a range (CIDR) or a host name.

    Line by line: on a line, a run of addresses then a run of codes is one group ("1.1.1.1 MCI 2.2.2.2 MTN" is two).
    Addresses without a code are for every operator without its own (OTHER). Addresses and codes never look alike.
    """
    lines = text.splitlines() if isinstance(text, str) else [" ".join(text)]
    groups: list[tuple[list[str], list[str]]] = []
    for line in lines:
        hosts: list[str] = []
        codes: list[str] = []
        for token in split_pattern.split(line.strip()):
            if not token:
                continue
            if is_operator_code(token):
                if hosts:
                    codes.append(token)
                continue
            if codes:  # an address after codes: the next group
                groups.append((hosts, codes))
                hosts, codes = [], []
            hosts.append(token)
        if hosts:
            groups.append((hosts, codes or [OTHER_OPERATOR]))
    return groups


def parse_operator_ips(text: str | list[str]) -> list[tuple[str, list[str]]]:
    """The CDN IP field as (address, operators) rows, one per address (see parse_operator_groups)."""
    return [(host, codes) for hosts, codes in parse_operator_groups(text) for host in hosts]


def pick_address(entry: str) -> str:
    """An entry of the CDN IP field as one address: a range (CIDR) gives a random address in it."""
    if "/" not in entry:
        return entry
    try:
        net = ipaddress.ip_network(entry, strict=False)
    except ValueError:
        return entry
    if net.num_addresses <= 2:
        return str(net.network_address)
    # not the network address, nor an IPv4 broadcast
    return str(net.network_address + random.randrange(1, net.num_addresses - (1 if net.version == 4 else 0)))


def __get_host_base_on_asn(ips: str | list[str], asn_short: str, asn: str = "") -> str:
    rows = parse_operator_ips(ips)
    valid_hosts = [host for host, _codes in rows if len(host) > 5]
    if not valid_hosts:
        hutils.flask.flash(_("Error! auto cdn ip can not be find, please contact admin."))
        return ""
    # The user's AS number; their operator; else the "OTHER" rows (operators without their own); else any address.
    for wanted in (f"AS{asn}" if asn and asn.isdigit() else None, asn_short, OTHER_OPERATOR):
        if not wanted:
            continue
        hosts = [host for host, codes in rows if wanted in codes]
        if hosts:
            return pick_address(random.choice(hosts))
    return pick_address(random.choice(valid_hosts))


def get_clean_ip(ips: str | list[str], resolve: bool = False) -> str:
    user_ip = get_real_user_ip()
    default_asn = request.args.get("asn", "") if has_request_context() else ""
    return get_clean_ip_user(user_ip, ips, default_asn)


split_pattern = re.compile(r"[ \t\r\n;,]+")


@cache.cache(300)
def get_clean_ip_user(user_ip, ipliststr: str, default_asn: str = "") -> tuple[str, str]:
    ipliststr = ipliststr.strip()
    if not ipliststr:
        ipliststr = DEFAULT_IPs.strip()

    ips = split_pattern.split(ipliststr)

    info = maxmind.get_ip_info(user_ip)
    asn_short = info.short_name
    country = info.country
    # print("Real user ip",get_real_user_ip_debug(), user_ip,asn_short,country)
    is_morteza_format = any(is_operator_code(x) for x in ips)
    # print("IPs",ips)
    if is_morteza_format:
        asn = info.asn
        if str(country).lower() != hconfig(ConfigEnum.country) and default_asn:
            asn_short, asn = default_asn, ""  # abroad (a VPN): the operator the link asks for, not the AS seen
        selected_server = __get_host_base_on_asn(ips, asn_short, asn)
    else:
        selected_server = random.sample(ips, 1)[0]
    # print("selected_server",selected_server)
    return str(selected_server), asn_short
