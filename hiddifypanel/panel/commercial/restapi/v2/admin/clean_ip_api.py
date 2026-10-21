"""Clean IP scanner (Admin V2): the visitor's network, so a scan done in their browser can be saved for their ISP.

The scan itself runs in the browser of whoever opens the page (the panel's server is abroad and can not test the
internet in Iran). The page saves the result as "IP SHORT" pairs in a CDN domain's CDN IP field, through the
domains page API; Hiddify then gives each user the IP of their own ISP (hutils.network.auto_ip_selector).
"""

from __future__ import annotations

from flask.views import MethodView

from hiddifypanel.auth import login_required
from hiddifypanel.hutils.network import auto_ip_selector, maxmind
from hiddifypanel.models import ConfigEnum, Role, hconfig

ROLES = {Role.super_admin, Role.admin}


class CleanIpNetworkApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self):
        """Clean IP scanner: the network (ISP) this page is opened from"""
        ip = auto_ip_selector.get_real_user_ip()
        info = maxmind.get_ip_info(ip)
        country = str(info.country or "unknown").lower()
        return {
            "ip": ip,
            "asn": str(info.asn),
            "org": str(info.asn_org),
            "country": country,
            # Hiddify's ISP name ("MCI", "MTN", …): what the CDN IP field's pairs use; "unknown" when it has none
            "short_name": str(info.short_name),
            "short_names": sorted(maxmind.ASN_SHORT_NAMES),
            # A VPN (or an ISP abroad) shows as another country: the result would not be for the users' ISP
            "panel_country": str(hconfig(ConfigEnum.country) or "").lower(),
            "db_available": bool(info.db_available),
        }
