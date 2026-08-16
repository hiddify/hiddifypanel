import datetime
import json
import re
from concurrent.futures import ThreadPoolExecutor

import requests
import user_agents
from apiflask import abort
from flask import Response, g, render_template, request
from flask_babel import gettext as _
from flask_classful import FlaskView, route

from hiddifypanel import hutils
from hiddifypanel.auth import login_required
from hiddifypanel.cache import cache
from hiddifypanel.models import *
from hiddifypanel.panel import hiddify
from hiddifypanel.proxy_v3.config_builder.dump import render_client_configs


class UserView(FlaskView):
    def index(self):
        return self.auto_sub()

    @route("/ua")
    def user_agent(self):
        ua = str(g.user_agent) + "\n" + str(request.user_agent)
        print(ua)
        return ua

    def auto_sub(self):
        if g.user_agent["is_browser"]:
            return self.new()
        return self.get_proper_config() or self.links_imp(base64=True)

    # former /sub/ or /sub (it was auto actually but we named it as /sub/)
    @route("/auto/")
    @route("/auto")
    @login_required(roles={Role.user})
    def force_sub(self):
        return self.get_proper_config() or self.links_imp(base64=False)

    # region new endpoints
    @route("/sub/")
    @route("/sub")
    @login_required(roles={Role.user})
    def sub(self):
        """Returns proxy links (not base64 encoded)"""
        return self.links_imp(base64=False)

    @route("/sub64/")
    @route("/sub64")
    @login_required(roles={Role.user})
    def sub64(self):
        """Returns proxy links (base64 encoded)"""
        return self.links_imp(base64=True)

    @route("/xray/")
    @route("/xray")
    @login_required(roles={Role.user})
    def xray(self):
        """Returns Xray JSON proxy config"""
        c = get_common_data(g.account.uuid, mode="new")
        if request.method == "HEAD":
            return add_headers("", c, "application/json")

        data = self._render_core_config("xray", c, pretty=True)

        return add_headers(data, c, "application/json")

    @route("/singbox/")
    @route("/singbox")
    @login_required(roles={Role.user})
    def singbox_full(self):
        """Returns singbox / hiddify-core client JSON config"""
        return self.full_singbox_imp()

    @route("/singbox-ssh/")
    @route("/singbox-ssh")
    @login_required(roles={Role.user})
    def singbox_ssh(self):
        """Returns singbox client JSON config (ssh)"""
        return self.singbox_ssh_imp()

    @route("/wireguard/")
    @route("/wireguard")
    @login_required(roles={Role.user})
    def wireguard(self):
        """Returns wireguard client config"""
        c = get_common_data(g.account.uuid, "new")
        wireguards = []
        for pinfo in hutils.proxy.get_valid_proxies(c["domains"]):
            if pinfo["proto"] != ProxyProto.wireguard:
                continue
            wireguards.append(pinfo)

        if not len(wireguards):
            abort(404)
        resp = ""
        for wg in wireguards:
            resp += f"#========={wg['extra_info']} {wg['name']}================\n"
            resp += hutils.proxy.wireguard.generate_wireguard_config(wg)
            resp += "\n\n"
        return add_headers(resp, c)

    @route("/clash/")
    @route("/clash")
    @login_required(roles={Role.user})
    def clash(self):
        """Returns clash client config"""
        return self.clash_config_imp(meta_or_normal="normal")

    @route("/clashmeta/")
    @route("/clashmeta")
    @login_required(roles={Role.user})
    def clashmeta(self):
        """Returns clash meta client config"""
        return self.clash_config_imp(meta_or_normal="meta")

    # endregion

    @route("/new/")
    @route("/new")
    @login_required(roles={Role.user})
    def new(self):
        conf = self.get_proper_config()
        if conf:
            return conf

        c = get_common_data(g.account.uuid, mode="new")
        user_agent = user_agents.parse(request.user_agent.string)
        return render_template("new.html", **c, ua=user_agent)

    def get_proper_config(self):
        """Returns proper config based on user agent"""
        if g.user_agent["is_browser"]:
            return None

        ua = request.user_agent.string
        if g.user_agent["is_singbox"] or re.match("^(HiddifyNext|Dart|SFI|SFA)", ua, re.IGNORECASE):
            return self.full_singbox_imp()

        if re.match("^(Clash-verge|Clash-?Meta|Stash|NekoBox|NekoRay|Pharos|hiddify-desktop)", ua, re.IGNORECASE):
            return self.clash_config_imp(meta_or_normal="meta")
        if re.match("^(Clash|Stash)", ua, re.IGNORECASE):
            return self.clash_config_imp(meta_or_normal="normal")

        if hconfig(ConfigEnum.sub_full_xray_json_enable):
            if g.user_agent.get("is_v2rayng") and hutils.flask.is_client_version(hutils.flask.ClientVersion.v2ryang, 1, 8, 17):
                return self.xray()
            elif g.user_agent.get("is_streisand"):
                return self.xray()

        if re.match("^(Hiddify|FoXray|Fair|v2rayNG|SagerNet|Shadowrocket|V2Box|Loon|Liberty|Streisand)", ua, re.IGNORECASE):
            return self.links_imp(base64=True)

    @route("/clash/<meta_or_normal>/proxies.yml")
    @route("/clash/proxies.yml")
    @login_required(roles={Role.user})
    def clash_proxies(self, meta_or_normal="normal"):
        mode = request.args.get("mode")
        domain = request.args.get("domain", None)

        c = get_common_data(g.account.uuid, mode, filter_domain=domain)
        text = self._render_core_config("clash", c, pretty=False)
        proxies_only = _clash_proxies_yaml(text)
        resp = Response(proxies_only)
        resp.mimetype = "text/plain"
        return resp

    @route("/clash/<typ>.yml", methods=["GET", "HEAD"])
    @route("/clash/<meta_or_normal>/<typ>.yml", methods=["GET", "HEAD"])
    @login_required(roles={Role.user})
    def clash_config_imp(self, meta_or_normal="normal", typ="all.yml"):
        del typ  # proxy_v3 clash base already selects full client shell
        if meta_or_normal == "meta" and not hconfig(ConfigEnum.sub_full_clash_meta_enable):
            return "The Clash meta subscription is disabled"
        elif meta_or_normal == "normal" and not hconfig(ConfigEnum.sub_full_clash_enable):
            return "The Clash subscription is disabled"

        c = get_common_data(g.account.uuid, request.args.get("mode"))
        if request.method == "HEAD":
            return add_headers("", c)

        resp = self._render_core_config("clash", c, pretty=False)
        return add_headers(resp, c)

    @route("/full-singbox.json", methods=["GET", "HEAD"])
    @login_required(roles={Role.user})
    def full_singbox_imp(self):
        mode = "new"
        c = get_common_data(g.account.uuid, mode)
        if request.method == "HEAD":
            return add_headers("", c, "application/json")

        # HiddifyNext / sing-box clients use the hiddify-core client shell.
        data = self._render_core_config("hiddify-core", c, pretty=True)
        return add_headers(data, c, "application/json")

    @route("/singbox.json", methods=["GET", "HEAD"])
    @login_required(roles={Role.user})
    def singbox_ssh_imp(self):
        if not hconfig(ConfigEnum.ssh_server_enable):
            return "The SSH server is disabled"

        mode = "new"
        c = get_common_data(g.account.uuid, mode)
        if request.method == "HEAD":
            resp = ""
        else:
            resp = render_template(
                "singbox_config.json",
                **c,
                host_keys=hutils.proxy.get_ssh_hostkeys(get_hconfigs_json()),
                ssh_client_version=hiddify.get_ssh_client_version(g.user),
                ssh_ip=hutils.network.get_direct_host_or_ip(4),
                base64=False,
            )

        return add_headers(resp, c)

    @route("/all.txt", methods=["GET", "HEAD"])
    @login_required(roles={Role.user})
    def links_imp(self, base64=False):
        """Returns subscription links (base64 or not)"""
        mode = "new"
        base64 = base64 or request.args.get("base64", "").lower() == "true"
        c = get_common_data(g.account.uuid, mode)
        if request.method == "HEAD":
            resp = ""
        else:
            resp = self._render_core_config("sublink", c, pretty=False)

        if base64:
            resp = hutils.encode.do_base_64(resp)
        return add_headers(resp, c)

    def _render_core_config(self, core: str, common: dict, *, pretty: bool) -> str:
        child_id = int(getattr(common.get("db_domain"), "child_id", 0) or 0)
        result = render_client_configs(
            user=common["user"],
            child_id=child_id,
            sublink_domain=request.host,
            user_agent=request.user_agent.string,
            pretty=pretty,
            cores=(core,),
            invalidate_cache=False,
        )
        return result.configs.get(core) or ""

    @route("/offline.html")
    @login_required(roles={Role.user})
    def offline():
        return f"Not Connected <a href='{hiddify.get_account_panel_link(g.account, request.host)}'>click for reload</a>"

    # backward compatiblity
    @route("/admin/<path:path>")
    @login_required()
    def admin(self, path):
        return ""


def get_domain_information(no_domain=False, filter_domain=None, alternative=None):
    domains = []
    if filter_domain:
        domain = filter_domain
        db_domain = Domain.query.filter(Domain.domain == domain).first() or Domain(domain=domain, mode=DomainType.direct, cdn_ip="", show_domains=[], child_id=0)
        domains = [db_domain]
    else:
        domain = alternative if not no_domain else None
        db_domain = Domain.query.filter(Domain.domain == domain).first()

        if not db_domain:
            parts = domain.split(".")  # TODO fix bug domain maybe null
            parts[0] = "*"
            domain_new = ".".join(parts)
            db_domain = Domain.query.filter(Domain.domain == domain_new).first()

        if not db_domain:
            db_domain = Domain(domain=domain, show_domains=[])
            hutils.flask.flash(_("This domain does not exist in the panel!" + domain))

        domains = db_domain.show_domains or Domain.query.filter(Domain.sub_link_only != True).all()

    has_auto_cdn = False

    if len(domains) == 0:
        domains = [Domain(id=0, domain=alternative, mode=DomainType.direct, cdn_ip="", show_domains=[], child_id=0)]

    return domains, db_domain, has_auto_cdn


def get_common_data(user_uuid, mode, no_domain=False, filter_domain=None):
    """Usable for user account"""
    domains, db_domain, has_auto_cdn = get_domain_information(no_domain, filter_domain, request.host)

    domain = db_domain.domain
    user: User = g.account if g.account.uuid == user_uuid else User.by_uuid(f"{user_uuid}")
    if user is None:
        abort(401, "Invalid User")

    expire_days = user.remaining_days
    reset_days = user.days_to_reset()
    if reset_days >= expire_days:
        reset_days = 1000

    expire_s = int((datetime.date.today() + datetime.timedelta(days=expire_days) - datetime.date(1970, 1, 1)).total_seconds())

    user_ip = hutils.network.auto_ip_selector.get_real_user_ip()
    asn = hutils.network.auto_ip_selector.get_asn_short_name(user_ip)
    profile_title = f"{db_domain.alias or db_domain.domain} {user.name}"
    profile_url = hiddify.get_account_panel_link(user, request.host)
    if has_auto_cdn and asn != "unknown":
        profile_title += f" {asn}"

    return {
        "profile_title": profile_title,
        "user": user,
        "user_activate": user.is_active,
        "domain": domain,
        "mode": mode,
        "fake_ip_for_sub_link": datetime.datetime.now().strftime("%H.%M--%Y.%m.%d.time:%H%M"),
        "usage_limit_b": int(user.usage_limit_GB * 1024 * 1024 * 1024),
        "usage_current_b": int(user.current_usage_GB * 1024 * 1024 * 1024),
        "expire_s": expire_s,
        "expire_days": expire_days,
        "expire_rel": hutils.convert.format_timedelta(datetime.timedelta(days=expire_days)),
        "reset_day": reset_days,
        "hconfigs": get_hconfigs(),
        "hdomains": Domain.modes_and_domains(),
        "ConfigEnum": ConfigEnum,
        "link_maker": hutils.proxy,
        "domains": domains,
        "bot": g.get("bot", None),
        "db_domain": db_domain,
        "telegram_enable": hiddify.is_telegram_proxy_enable(domains),
        "ip": user_ip,
        "ip_debug": hutils.network.auto_ip_selector.get_real_user_ip_debug(user_ip),
        "asn": asn,
        "country": hutils.network.auto_ip_selector.get_country(user_ip),
        "has_auto_cdn": has_auto_cdn,
        "profile_url": profile_url,
    }


def add_headers(res, c, mimetype="text/plain"):
    resp = Response(res)
    resp.mimetype = mimetype
    resp.headers["Subscription-Userinfo"] = f"upload=0;download={c['usage_current_b']};total={c['usage_limit_b']};expire={c['expire_s']}"
    resp.headers["profile-web-page-url"] = request.base_url.rsplit("/", 1)[0].replace("http://", "https://") + "/"

    if hconfig(ConfigEnum.branding_site):
        resp.headers["support-url"] = hconfig(ConfigEnum.branding_site)
    resp.headers["profile-update-interval"] = 1
    resp.headers["profile-title"] = "base64:" + hutils.encode.do_base_64(c["profile_title"])

    return resp


@cache.cache(ttl=300)
def fetch_url(url: str):
    if not (url.startswith("http://") or url.startswith("https://")):
        return url
    try:
        resp = requests.get(url, timeout=2, headers={"User-Agent": [request.user_agent.string]})
        resp.raise_for_status()
        content = resp.text

        return content

    except Exception:
        return ""


def get_and_merge_urls(urls: list[str], max_workers=8):
    if len(urls) == 0 or len(urls) == 1 and urls[0] == "":
        return []
    urls = [u.replace("{{UUID}}", g.account.uuid) for u in urls]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        contents = list(executor.map(lambda url: fetch_url(url), urls))

    return contents


def parse_json(s: str):
    try:
        return json.loads(s)
    except Exception:
        pass
    return {}


def _merge_json_client_sections(base: dict, extra: dict) -> None:
    for key in ("outbounds", "endpoints", "inbounds", "route", "dns", "experimental"):
        value = extra.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            base.setdefault(key, []).extend(value)
        elif isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key].update(value)
        elif key not in base:
            base[key] = value


def _clash_proxies_yaml(clash_text: str) -> str:
    try:
        import yaml

        data = yaml.safe_load(clash_text) if (clash_text or "").strip() else {}
    except Exception:
        data = {}
    proxies = data.get("proxies") if isinstance(data, dict) else None
    if not isinstance(proxies, list):
        proxies = []
    try:
        import yaml

        return yaml.dump({"proxies": proxies}, sort_keys=False, allow_unicode=True) or "proxies: []\n"
    except Exception:
        return "proxies: []\n"
