"""Clean IP scanner (Admin V2): the visitor's network, so a scan done in their browser can be saved for their ISP.

The scan itself runs in the browser of whoever opens the page (the panel's server is abroad and can not test the
internet in Iran). The page saves the result as "IP SHORT" pairs in a CDN domain's CDN IP field, through the
domains page API; Hiddify then gives each user the IP of their own ISP (hutils.network.auto_ip_selector).

A browser can not test uploads (see the ip_scanner base config), so the page also makes a one-day command for the full test:
the admin runs it on a computer / phone in Iran, and the script sends its result back here, where it is saved for the
ISP the report comes from.
"""

from __future__ import annotations

import ipaddress
import json
import re
import secrets
import time

from apiflask import abort
from loguru import logger
from flask import Response, request
from flask.views import MethodView

from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.cache import cache, redis_client
from hiddifypanel.hutils.network import auto_ip_selector, maxmind
from hiddifypanel.models import ConfigEnum, Domain, Role, hconfig
from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide, ProxyBaseConfig

from hiddifypanel.panel import reality_watch


ROLES = {Role.super_admin, Role.admin}
TOKEN_TTL = 24 * 3600
_KEY = "hiddify:clean-ip:{}"
# https://www.cloudflare.com/ips-v4/
CLOUDFLARE_RANGES = [
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22", "141.101.64.0/18", "108.162.192.0/18",
    "190.93.240.0/20", "188.114.96.0/20", "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
]


class AsnNamesApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self):
        """Scanner: the companies of AS numbers (?asn=254,42337), for "AS…" operators; unknown ones are left out"""
        numbers = [int(x) for x in str(request.args.get("asn") or "").split(",") if x.strip().isdigit()][:50]
        return {"names": {str(n): name for n in numbers if (name := maxmind.asn_org(n))}}


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


# ---------------------------------------------------------------------------------------------- full test (a script)


def _load(token: str) -> dict | None:
    raw = redis_client.get(_KEY.format(token)) if token and len(token) < 64 else None
    return json.loads(raw) if raw else None


def _store(token: str, data: dict) -> None:
    ttl = redis_client.ttl(_KEY.format(token))
    redis_client.set(_KEY.format(token), json.dumps(data), ex=ttl if ttl and ttl > 0 else TOKEN_TTL)


def _cdn_domain(domain_id) -> Domain:
    try:
        d = Domain.query.filter(Domain.id == int(domain_id)).first()
    except (TypeError, ValueError):
        d = None
    if d is None or str(getattr(d.mode, "value", d.mode)) not in ("cdn", "worker"):
        abort(400, "Pick a CDN or worker domain")
    return d


def merge_cdn_ip(current: str, short: str, ips: list[str]) -> tuple[str, int]:
    """This operator's addresses replaced by ``ips`` (one line), the others kept: addresses shared with other operators
    stay for them, addresses without a code stay for every operator without its own. Returns (text, groups kept)."""
    lines = [f"{','.join(ips)} {short}"] if ips else []
    kept = 0
    for hosts, codes in auto_ip_selector.parse_operator_groups(current or ""):
        others = [c for c in codes if c != short]
        if others:
            lines.append(f"{','.join(hosts)} {','.join(c for c in others if c != auto_ip_selector.OTHER_OPERATOR)}".strip())
            kept += 1
    return "\n".join(lines), kept


def _server_ipv4() -> str:
    from hiddifypanel.hutils.network import get_ips

    try:
        ips = get_ips(4)
    except Exception:
        ips = []
    return str(ips[0]) if ips else ""


#: The most a command takes: IP ranges (CIDRs), SNI names to test.
MAX_RANGES = 200
MAX_SNIS = 1000
#: The most spare REALITY SNIs kept (a pasted list of a hundred or two fits).
MAX_SPARES = 300
_HOSTNAME = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def _ranges(value) -> list[str]:
    """The IPv4 CIDRs to pick IPs from (Cloudflare's when none is valid)."""
    out = []
    for item in value if isinstance(value, list) else []:
        try:
            net = ipaddress.IPv4Network(str(item).strip(), strict=False)
        except ValueError:
            continue
        if net.prefixlen <= 30:
            out.append(str(net))
    return list(dict.fromkeys(out))[:MAX_RANGES] or CLOUDFLARE_RANGES


def _snis(value) -> list[str]:
    """Valid hostnames from the admin's list (lowercase, no duplicates)."""
    names = (str(x).strip().lower().rstrip(".") for x in (value if isinstance(value, list) else []))
    return list(dict.fromkeys(n for n in names if _HOSTNAME.match(n)))[:MAX_SNIS]


def _int(value, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(int(value), hi))
    except (TypeError, ValueError):
        return default


class CleanIpTokenApi(MethodView):
    decorators = [login_required(ROLES)]

    def post(self):
        """Scanner: a one-day command for another device: the IP full test (``kind`` "ip", with upload) or the REALITY
        SNI test (``kind`` "sni", super admins)"""
        body = request.get_json(silent=True) or {}
        token = secrets.token_urlsafe(18)
        if body.get("kind") == "sni":
            if g.account.role != Role.super_admin:
                abort(403, "Only the owner can test the REALITY SNIs")
            # the names to test, and where: this server, as REALITY clients reach it
            # the REALITY SNIs in use and spare (their status is recorded), then the admin's candidates (only shown)
            watched = reality_watch.targets()
            candidates = [n for n in _snis(body.get("snis")) if n not in watched]
            data = {"kind": "sni", "snis": watched + candidates, "watched": watched, "server_ip": _server_ipv4(), "control": request.host.split(":")[0]}
        else:
            domain = _cdn_domain(body.get("domain_id"))
            data = {
                "kind": "ip",
                "domain_id": domain.id,
                "size": _int(body.get("size"), 5000, 1000, 64000),
                "per_range": _int(body.get("per_range"), 8, 1, 64),
                "per_isp": _int(body.get("per_isp"), 3, 1, 20),
                "ranges": _ranges(body.get("ranges")),
            }
        _store(token, {**data, "reports": []})
        url = f"https://{request.host}/{g.proxy_path}/api/v2/admin/clean-ip/run/{token}/script.py"
        template = script_template(TemplateCore.sni_scanner if data["kind"] == "sni" else TemplateCore.ip_scanner)
        return {
            "token": token,
            "expires_in": TOKEN_TTL,
            "script_url": url,
            "template_id": template.id if template else None,
            "commands": {"unix": f"curl -fsSL '{url}' | python3 -", "windows": f"irm '{url}' | python -"},
        }


class CleanIpTokenStatusApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self, token: str):
        """Clean IP scanner: the reports sent with this command so far"""
        data = _load(token)
        if data is None:
            abort(404, "Expired")
        return {"reports": data.get("reports", [])}


def script_template(core: TemplateCore) -> ProxyBaseConfig | None:
    """The scanner script's base config row (editable on the Base configs page)."""
    return ProxyBaseConfig.query.filter(ProxyBaseConfig.child_id == 0, ProxyBaseConfig.side == BaseConfigSide.server, ProxyBaseConfig.core == core).first()


def render_script(core: TemplateCore, variables: dict) -> str:
    """A scanner script from its base config (the admin's edit, else the built-in file), with this command's values."""
    from hiddifypanel.proxy_v3.config_builder.base_config import resolve_base_config_content
    from hiddifypanel.proxy_v3.config_builder.jinja_render import render_template_text
    from hiddifypanel.proxy_v3.context_vars.version import TemplateVersion
    from hiddifypanel.proxy_v3.template_catalog.base_configs import default_base_content

    text = resolve_base_config_content(0, BaseConfigSide.server, core, TemplateVersion("0.0.0")) or default_base_content("server", core.value)
    if not text:
        return f"print('The {core.value} template is missing: restore it on the Base configs page.')\n"
    try:
        return render_template_text(text, 0, variables)
    except Exception as e:
        logger.warning(f"scanner: the {core.value} template does not render: {e}")
        return f"print({json.dumps(f'The {core.value} template has an error (Base configs page): {e}')})\n"


class CleanIpScriptApi(MethodView):
    """The script (the token in the path is its only key: it can only add IPs to one CDN domain, for a day)."""

    def get(self, token: str):
        data = _load(token)
        if data is None:
            return Response("print('This command has expired: make a new one on the Scanner page.')\n", mimetype="text/x-python")
        base = f"/{g.proxy_path}/api/v2/admin/clean-ip/run/{token}"
        report = f"https://{request.host}{base}/report/"
        if data.get("kind") == "sni":
            text = render_script(TemplateCore.sni_scanner, {
                "report_url": report,
                "snis": data.get("snis") or [],
                "watched": data.get("watched", data.get("snis")) or [],
                "server_ip": data.get("server_ip") or "",
                "control": data.get("control") or request.host.split(":")[0],
            })
            return Response(text, mimetype="text/x-python")
        domain = Domain.query.filter(Domain.id == data.get("domain_id")).first()
        if domain is None:
            abort(404)
        text = render_script(TemplateCore.ip_scanner, {
            "host": domain.domain,
            "probe_path": f"{base}/probe/",
            "marker": PROBE_MARKER,
            "report_url": report,
            "size": int(data["size"]),
            "per_range": int(data["per_range"]),
            "ranges": data.get("ranges") or CLOUDFLARE_RANGES,
        })
        return Response(text, mimetype="text/x-python")


#: What the probe answers, so the script knows the upload reached this panel (not a Cloudflare or ISP error page).
PROBE_MARKER = "hiddify-scan-ok"
#: The largest upload the probe takes (the IP test's maximum size).
PROBE_MAX = 64000


class SniCandidatesApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        """Scanner: SNI names to test (sites OONI saw reachable in Iran), cached for an hour"""
        return {"snis": _sni_candidates()}


@cache.cache(3600)
def _sni_candidates() -> list[str]:
    from hiddifypanel.hutils.network import get_random_domains

    return get_random_domains(MAX_SNIS)


class CleanIpProbeApi(MethodView):
    """The IP test's target, reached through each Cloudflare IP: answers with how many bytes of the upload arrived."""

    def post(self, token: str):
        if _load(token) is None:
            abort(404, "Expired")
        received = len(request.get_data(cache=False)[: PROBE_MAX + 1])
        return Response(f"{PROBE_MARKER} {received}", mimetype="text/plain", headers={"Cache-Control": "no-store"})


class CleanIpReportApi(MethodView):
    """The script's result: saved for the ISP the request comes from (the device that ran the test)."""

    def post(self, token: str):
        data = _load(token)
        if data is None:
            abort(404, "Expired")
        body = request.get_json(silent=True) or {}
        info = maxmind.get_ip_info(auto_ip_selector.get_real_user_ip())
        short = str(info.short_name)
        report = {
            "at": int(time.time()),
            "short_name": short,
            "asn": str(info.asn),
            "org": str(info.asn_org),
            "country": str(info.country).lower(),
        }
        if data.get("kind") == "sni":
            message = _record_snis(body, short, report, data.get("watched"))
        else:
            message = _save_ips(body, data, short, report)
        data["reports"] = (data.get("reports") or [])[-19:] + [report]
        _store(token, data)
        return {"short_name": short, "message": message, "saved": report.get("saved", [])}


def _record_snis(body: dict, short: str, report: dict, watched: list[str] | None) -> str:
    """The REALITY SNI test: only when the server answered with its own name (else the address is blocked, not the SNIs).

    The REALITY SNIs in use and spare (``watched``; all of them in commands older than the candidates) are recorded for
    the ISP; of the candidates, the report keeps the ones that work (to add as spares) and how many were tested."""
    results = [{"sni": str(r.get("sni") or ""), "ok": bool(r.get("ok"))} for r in (body.get("snis") or [])[: MAX_SNIS + 100] if isinstance(r, dict)]
    watched_set = set(watched if watched is not None else [r["sni"] for r in results])
    report["snis"] = [r for r in results if r["sni"] in watched_set]
    candidates = [r for r in results if r["sni"] not in watched_set]
    report["candidates_tested"] = len(candidates)
    report["candidates_ok"] = [r["sni"] for r in candidates if r["ok"]]
    report["control"] = bool(body.get("sni_control"))
    if not report["control"]:
        return "The server did not answer: its address is blocked or down on this ISP, so the SNIs say nothing."
    found = f" {len(report['candidates_ok'])} of {len(candidates)} candidate SNIs work." if candidates else ""
    if short == "unknown":
        return "Hiddify has no name for this ISP: the REALITY SNIs are not recorded." + found
    report["switches"] = reality_watch.record(short, report["snis"])
    filtered = sum(1 for r in report["snis"] if not r["ok"])
    return f"Recorded for {short}: {filtered} of {len(report['snis'])} REALITY SNIs filtered." + found


def _save_ips(body: dict, data: dict, short: str, report: dict) -> str:
    """The IP full test: the working IPs saved on the CDN domain for this ISP."""
    found = []
    for row in (body.get("ips") or [])[:200]:
        try:
            ip = str(ipaddress.IPv4Address(str(row.get("ip"))))
            loss = max(0, min(int(row.get("loss") or 0), 100))  # % of the retries that failed
            found.append({"ip": ip, "ms": int(row.get("ms") or 0), "loss": loss, "colo": str(row.get("colo") or "")[:8]})
        except (ValueError, AttributeError, TypeError):
            continue
    found.sort(key=lambda r: (r["loss"], r["ms"]))  # reliable first, then fast
    report.update({
        "tested": _int(body.get("tested"), 0, 0, 100000),
        "size": _int(body.get("size"), 0, 0, 100000),
        "ips": found[:50],
        "saved": [],
    })
    # An operator Hiddify has no name for is saved under its AS number ("AS12880")
    key = auto_ip_selector.operator_key(short, report["asn"])
    report["saved_for"] = key
    if key and found:
        from .domains_page_api import _save

        domain = Domain.query.filter(Domain.id == data["domain_id"]).first()
        if domain is not None:
            ips = [r["ip"] for r in found[: data["per_isp"]]]
            domain.cdn_ip, _kept = merge_cdn_ip(domain.cdn_ip, key, ips)
            _save(domain, is_created=False)
            report["saved"] = ips
            message = f"Saved {len(ips)} IPs for {key} on {domain.domain}."
        else:
            message = "The domain is gone; nothing saved."
    elif not found:
        message = "No working IP: nothing saved."
    else:
        message = "The ISP is unknown (no AS number either): nothing saved. Pick the ISP on the Scanner page and save the IPs from there."
    return message


# ---------------------------------------------------------------------------------------------- REALITY SNI watch


def _reality_state() -> dict:
    data = reality_watch.status()
    return {
        "domains": [{"id": d.id, "sni": d.domain, "status": data.get(d.domain.lower(), {})} for d in reality_watch.reality_domains()],
        "spares": [{"sni": s, "status": data.get(s, {})} for s in reality_watch.spares()],
        "auto": reality_watch.settings()["auto"],
        "events": reality_watch.events()[::-1],
    }


class RealitySniApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        """REALITY SNI watch: each SNI's status per ISP (from full tests run in Iran), the spares and the switches"""
        return _reality_state()

    def put(self):
        """REALITY SNI watch: the spare SNIs and the automatic switch"""
        body = request.get_json(silent=True) or {}
        spares = body.get("spares") or []
        if isinstance(spares, str):
            spares = spares.split()
        reality_watch.save_settings([str(x) for x in spares][:MAX_SPARES], bool(body.get("auto")))
        return _reality_state()


class RealitySniSwitchApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def post(self, domain_id: int):
        """REALITY SNI watch: switch this REALITY domain to another SNI (it must suit REALITY)"""
        domain = Domain.query.filter(Domain.id == domain_id).first()
        if domain is None:
            abort(404)
        try:
            reality_watch.switch(domain, str((request.get_json(silent=True) or {}).get("sni") or ""))
        except reality_watch.WatchError as e:
            abort(400, str(e))
        return _reality_state()
