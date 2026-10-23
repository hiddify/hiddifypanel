"""A pocket dashboard: server health, users and traffic at a glance."""

from __future__ import annotations

import datetime
import json
import subprocess

import requests
from loguru import logger

from hiddifypanel.models import AdminMode, DailyUsage

from .texts import T
from .ui import RULE, Cb, Ctx, Screen, bar, btn, duration, fmt_bytes, fmt_gb, h, keyboard, level_dot, route


def _meter(label: str, percent: float, detail: str) -> list[str]:
    ratio = percent / 100
    return [f"{level_dot(ratio)} <b>{label}</b>  {percent:.0f}%  <i>{detail}</i>", f"<code>{bar(ratio, 14)}</code>"]


def status_screen(ctx: Ctx) -> Screen:
    admin = ctx.admin
    assert admin
    lang = ctx.lang
    lines = [f"📊 <b>{ctx.tr(T.status_title)}</b>", RULE]

    # Server health is the operators' business, not resellers'.
    if admin.mode != AdminMode.agent:
        try:
            from hiddifypanel.hutils import node_system

            system = node_system.collect_system_stats(None, process_limit=0).system
            lines += _meter(f"🖥 {ctx.tr(T.cpu)}", system.cpu.percent, f"{system.cpu.cores} cores")
            lines += _meter(f"🧠 {ctx.tr(T.ram)}", system.memory.percent, f"{fmt_gb(system.memory.used_gb, lang)} / {fmt_gb(system.memory.total_gb, lang)}")
            lines += _meter(f"💾 {ctx.tr(T.disk)}", system.disk.percent, f"{fmt_gb(system.disk.used_gb, lang)} / {fmt_gb(system.disk.total_gb, lang)}")
            lines.append(f"⏱ <b>{ctx.tr(T.uptime)}</b>  {duration(system.host.uptime_s, lang)}")
            lines.append("")
        except Exception as e:
            logger.warning(f"tgbot: system stats failed: {e}")

    stats = DailyUsage.get_dashboard_stats(admin_id=admin.id, series_days=30)
    users, totals = stats.users, stats.usage.totals
    lines += [
        f"👥 <b>{ctx.tr(T.users_block)}</b>",
        ctx.tr(T.users_line, total=users.total, active=users.active),
        ctx.tr(T.online_line, now=users.online.m5, today=users.online.today),
        "",
        f"📈 <b>{ctx.tr(T.traffic)}</b>",
        f"{ctx.tr(T.traffic_today)}  <b>{fmt_bytes(totals.today, lang)}</b>",
        f"{ctx.tr(T.traffic_yesterday)}  {fmt_bytes(totals.yesterday, lang)}",
        f"{ctx.tr(T.traffic_week)}  {fmt_bytes(totals.week, lang)}",
        f"{ctx.tr(T.traffic_month)}  {fmt_bytes(totals.month, lang)}",
        f"{ctx.tr(T.traffic_total)}  {fmt_bytes(totals.total, lang)}",
        "",
        f"<i>{ctx.tr(T.updated_at, time=datetime.datetime.now().strftime('%H:%M:%S'))}</i>",
    ]
    return Screen("\n".join(lines), keyboard([btn(ctx.tr(T.refresh), Cb.status)], [btn(ctx.tr(T.menu), Cb.home)]))


@route(Cb.status, admin=True)
def show_status(ctx: Ctx, _args: list[str]) -> None:
    ctx.show(status_screen(ctx))
    ctx.toast()


# --------------------------------------------------------------------------- check status: the address and the services

#: The services of a Hiddify server, in the order they are listed
SERVICES = (
    "hiddify-haproxy",
    "hiddify-core",
    "hiddify-redis",
    "hiddify-panel",
    "hiddify-telegram-proxy",
    "hiddify-xray",
    "hiddify-mysql",
    "wg-quick@hiddifywg",
    "hiddify-rpxy-l4",
)
#: ``systemctl is-active``: running, starting (or stopping), anything else (failed, inactive, not installed)
_STATE_MARK = {"active": "✅", "activating": "⚠️", "reloading": "⚠️", "deactivating": "⚠️"}
_LINE = "-" * 45


def flag(country_code: str) -> str:
    """The flag emoji of a two-letter country code (regional indicator letters); '' when it is not one."""
    code = (country_code or "").upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code)


def _geo_lookup(ip: str) -> dict[str, str]:
    """Country, its code, city and organisation of ``ip``: ipwho.is, else ip-api.com, else the panel's own MaxMind data."""
    try:
        data = requests.get(f"https://ipwho.is/{ip}", timeout=5).json()
        if data.get("success"):
            return {"country": data.get("country") or "", "code": data.get("country_code") or "", "city": data.get("city") or "", "org": (data.get("connection") or {}).get("org") or ""}
    except Exception as e:
        logger.debug(f"tgbot: ipwho.is failed: {e}")
    try:
        data = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,org,isp", timeout=5).json()
        if data.get("status") == "success":
            return {"country": data.get("country") or "", "code": data.get("countryCode") or "", "city": data.get("city") or "", "org": data.get("org") or data.get("isp") or ""}
    except Exception as e:
        logger.debug(f"tgbot: ip-api.com failed: {e}")
    from hiddifypanel.hutils.network import maxmind

    info = maxmind.get_ip_info(ip)
    known = lambda v: "" if v == "unknown" else v  # noqa: E731
    return {"country": known(info.country), "code": known(info.country), "city": "", "org": known(info.asn_org)}


def _geo(ip: str) -> dict[str, str]:
    """The lookup, kept for an hour (the server does not move; every press would ask the service again)."""
    from hiddifypanel.cache import redis_client

    key = f"tgbot:geo:{ip}"
    raw = redis_client.get(key)
    if raw:
        return json.loads(raw)
    geo = _geo_lookup(ip)
    if geo.get("country"):
        redis_client.set(key, json.dumps(geo), ex=3600)
    return geo


def service_states(units=SERVICES) -> dict[str, str]:
    """``systemctl is-active`` of every unit, in one call (one answer line per unit)."""
    try:
        out = subprocess.run(["systemctl", "is-active", *units], capture_output=True, text=True, timeout=10).stdout.split()
    except Exception as e:
        logger.warning(f"tgbot: systemctl failed: {e}")
        out = []
    return {unit: (out[i] if i < len(out) else "unknown") for i, unit in enumerate(units)}


def check_text() -> str:
    """The report, monospaced so its columns line up (Telegram's <pre>)."""
    from hiddifypanel.hutils.network import get_ip_str

    ip = get_ip_str(4) or get_ip_str(6) or ""
    geo = _geo(ip) if ip else {}
    country = " ".join(p for p in (geo.get("country") or "—", flag(geo.get("code", ""))) if p)
    rows = [
        _LINE,
        "Global IP",
        f"  Country :  {country}",
        f"  City    :  {geo.get('city') or '—'}",
        f"  Org     :  {geo.get('org') or '—'}",
        f"  IP      :  {ip or '—'}",
        _LINE,
        "Services Status",
    ]
    width = max(len(u) for u in SERVICES) + 2
    rows += [f"  {unit.ljust(width)}{_STATE_MARK.get(state, '❌')}" for unit, state in service_states().items()]
    rows.append(_LINE)
    return "<pre>" + h("\n".join(rows)) + "</pre>"


@route(Cb.check, admin=True)
def show_check(ctx: Ctx, _args: list[str]) -> None:
    admin = ctx.admin
    assert admin
    if admin.mode == AdminMode.agent:  # the server is the operators' business, not resellers'
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    ctx.toast()
    text = f"{check_text()}\n<i>{ctx.tr(T.updated_at, time=datetime.datetime.now().strftime('%H:%M:%S'))}</i>"
    ctx.show(Screen(text, keyboard([btn(ctx.tr(T.refresh), Cb.check)], [btn(ctx.tr(T.menu), Cb.home)])))
