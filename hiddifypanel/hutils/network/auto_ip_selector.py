import random
import re

from flask import has_request_context, request
from flask_babel import gettext as _

from hiddifypanel import hutils
from hiddifypanel.cache import cache
from hiddifypanel.models.config import hconfig
from hiddifypanel.models.config_enum import ConfigEnum

from . import maxmind

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


@cache.cache()
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


def __get_host_base_on_asn(ips: str | list[str], asn_short: str) -> str:
    if type(ips) == str:
        ips = re.split("[ \t\r\n;,]+", ips.strip())
    valid_hosts = [ip for ip in ips if len(ip) > 5]

    if len(ips) % 2 != 0 or len(valid_hosts) == 0:
        hutils.flask.flash(_("Error! auto cdn ip can not be find, please contact admin."))
        if len(valid_hosts) == 0:
            return ""

    all_hosts = []
    for i in range(0, len(ips), 2):
        if asn_short == ips[i + 1]:
            # print("selected ",ips[i],ips[i+1])
            all_hosts.append(ips[i])

    selected = random.sample(valid_hosts, 1)[0]
    if len(all_hosts):
        selected = random.sample(all_hosts, 1)[0]

    return selected


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
    is_morteza_format = any(name in ips for name in maxmind.ASN_SHORT_NAMES)
    # print("IPs",ips)
    if is_morteza_format:
        if str(country).lower() != hconfig(ConfigEnum.country) and default_asn:
            asn_short = default_asn
        selected_server = __get_host_base_on_asn(ips, asn_short)
    else:
        selected_server = random.sample(ips, 1)[0]
    # print("selected_server",selected_server)
    return str(selected_server), asn_short
