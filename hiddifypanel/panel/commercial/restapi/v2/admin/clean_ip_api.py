"""Clean IP scanner (Admin V2): the visitor's network, so a scan done in their browser can be saved for their ISP.

The scan itself runs in the browser of whoever opens the page (the panel's server is abroad and can not test the
internet in Iran). The page saves the result as "IP SHORT" pairs in a CDN domain's CDN IP field, through the
domains page API; Hiddify then gives each user the IP of their own ISP (hutils.network.auto_ip_selector).

A browser can not test uploads (see clean_ip_script.py), so the page also makes a one-day command for the full test:
the admin runs it on a computer / phone in Iran, and the script sends its result back here, where it is saved for the
ISP the report comes from.
"""

from __future__ import annotations

import ipaddress
import json
import secrets
import time

from apiflask import abort
from flask import Response, request
from flask.views import MethodView

from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.cache import redis_client
from hiddifypanel.hutils.network import auto_ip_selector, maxmind
from hiddifypanel.models import ConfigEnum, Domain, Role, hconfig

from hiddifypanel.panel import reality_watch

from .clean_ip_script import SCRIPT

ROLES = {Role.super_admin, Role.admin}
TOKEN_TTL = 24 * 3600
_KEY = "hiddify:clean-ip:{}"
# https://www.cloudflare.com/ips-v4/
CLOUDFLARE_RANGES = [
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22", "141.101.64.0/18", "108.162.192.0/18",
    "190.93.240.0/20", "188.114.96.0/20", "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
]


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
    """This ISP's pairs replaced by ``ips``, the other ISPs' pairs kept (a plain IP list, without ISP names, is
    replaced: the two forms can not be mixed). Returns (text, how many other pairs were kept)."""
    lines = [f"{ip} {short}" for ip in ips]
    text = (current or "").strip()
    tokens = auto_ip_selector.split_pattern.split(text) if text else []
    kept = 0
    if tokens and len(tokens) % 2 == 0 and any(x in maxmind.ASN_SHORT_NAMES for x in tokens):
        for i in range(0, len(tokens), 2):
            if tokens[i + 1] != short:
                lines.append(f"{tokens[i]} {tokens[i + 1]}")
                kept += 1
    return "\n".join(lines), kept


def _server_ipv4() -> str:
    from hiddifypanel.hutils.network import get_ips

    try:
        ips = get_ips(4)
    except Exception:
        ips = []
    return str(ips[0]) if ips else ""


def _int(value, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(int(value), hi))
    except (TypeError, ValueError):
        return default


class CleanIpTokenApi(MethodView):
    decorators = [login_required(ROLES)]

    def post(self):
        """Clean IP scanner: a one-day command for the full test (with upload) on another device"""
        body = request.get_json(silent=True) or {}
        domain = _cdn_domain(body.get("domain_id"))
        token = secrets.token_urlsafe(18)
        _store(token, {
            "domain_id": domain.id,
            "size": _int(body.get("size"), 5000, 1000, 64000),
            "per_range": _int(body.get("per_range"), 8, 1, 64),
            "per_isp": _int(body.get("per_isp"), 3, 1, 20),
            "reports": [],
            # REALITY SNI watch: the names to test, and where (this server, as REALITY clients reach it)
            "snis": reality_watch.targets(),
            "server_ip": _server_ipv4(),
            "control": request.host.split(":")[0],
        })
        url = f"https://{request.host}/{g.proxy_path}/api/v2/admin/clean-ip/run/{token}/script.py"
        return {
            "token": token,
            "expires_in": TOKEN_TTL,
            "script_url": url,
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


class CleanIpScriptApi(MethodView):
    """The script (the token in the path is its only key: it can only add IPs to one CDN domain, for a day)."""

    def get(self, token: str):
        data = _load(token)
        if data is None:
            return Response("print('This command has expired: make a new one on the Clean IP page.')\n", mimetype="text/x-python")
        domain = Domain.query.filter(Domain.id == data["domain_id"]).first()
        if domain is None:
            abort(404)
        report = f"https://{request.host}/{g.proxy_path}/api/v2/admin/clean-ip/run/{token}/report/"
        text = (
            SCRIPT.replace("__HOST__", json.dumps(domain.domain))
            .replace("__REPORT__", json.dumps(report))
            .replace("__SIZE__", str(int(data["size"])))
            .replace("__PER_RANGE__", str(int(data["per_range"])))
            .replace("__RANGES__", json.dumps(CLOUDFLARE_RANGES))
            .replace("__SNIS__", json.dumps(data.get("snis") or []))
            .replace("__SERVER_IP__", json.dumps(data.get("server_ip") or ""))
            .replace("__CONTROL__", json.dumps(data.get("control") or request.host.split(":")[0]))
        )
        return Response(text, mimetype="text/x-python")


class CleanIpReportApi(MethodView):
    """The script's result: saved for the ISP the request comes from (the device that ran the test)."""

    def post(self, token: str):
        data = _load(token)
        if data is None:
            abort(404, "Expired")
        body = request.get_json(silent=True) or {}
        found = []
        for row in (body.get("ips") or [])[:200]:
            try:
                ip = str(ipaddress.IPv4Address(str(row.get("ip"))))
                found.append({"ip": ip, "ms": int(row.get("ms") or 0), "colo": str(row.get("colo") or "")[:8]})
            except (ValueError, AttributeError, TypeError):
                continue
        found.sort(key=lambda r: r["ms"])
        info = maxmind.get_ip_info(auto_ip_selector.get_real_user_ip())
        short = str(info.short_name)
        report = {
            "at": int(time.time()),
            "short_name": short,
            "asn": str(info.asn),
            "org": str(info.asn_org),
            "country": str(info.country).lower(),
            "tested": _int(body.get("tested"), 0, 0, 100000),
            "size": _int(body.get("size"), 0, 0, 100000),
            "ips": found[:50],
            "saved": [],
        }
        if short in maxmind.ASN_SHORT_NAMES and found:
            from .domains_page_api import _save

            domain = Domain.query.filter(Domain.id == data["domain_id"]).first()
            if domain is not None:
                ips = [r["ip"] for r in found[: data["per_isp"]]]
                domain.cdn_ip, _kept = merge_cdn_ip(domain.cdn_ip, short, ips)
                _save(domain, is_created=False)
                report["saved"] = ips
                message = f"Saved {len(ips)} IPs for {short} on {domain.domain}."
            else:
                message = "The domain is gone; nothing saved."
        elif not found:
            message = "No working IP: nothing saved."
        else:
            message = "Hiddify has no name for this ISP: nothing saved. Pick the ISP on the Clean IP page and save the IPs from there."
        # REALITY SNIs: only when the server answered with its own name (else the address is blocked, not the SNIs)
        sni_results = [r for r in (body.get("snis") or []) if isinstance(r, dict)][:50]
        if body.get("sni_control") and sni_results and short != "unknown":
            report["snis"] = [{"sni": str(r.get("sni") or ""), "ok": bool(r.get("ok"))} for r in sni_results]
            report["switches"] = reality_watch.record(short, report["snis"])
        data["reports"] = (data.get("reports") or [])[-19:] + [report]
        _store(token, data)
        return {"short_name": short, "message": message, "saved": report["saved"]}


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
        reality_watch.save_settings([str(x) for x in spares][:50], bool(body.get("auto")))
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
