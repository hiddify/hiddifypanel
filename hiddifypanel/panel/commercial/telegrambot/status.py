"""A pocket dashboard: server health, users and traffic at a glance."""

from __future__ import annotations

import datetime
import json
import subprocess
import time

import requests
from loguru import logger

import hiddifypanel
from hiddifypanel.models import AdminMode, DailyUsage

from .texts import T
from .ui import RULE, bar, btn, Cb, Ctx, duration, fmt_bytes, fmt_gb, h, keyboard, level_dot, route, Screen, tg_time


def _meter(label: str, percent: float, detail: str) -> list[str]:
    ratio = percent / 100
    return [f"{level_dot(ratio)} <b>{label}</b>  {percent:.0f}%  <i>{detail}</i>", f"<code>{bar(ratio, 14)}</code>"]


def _cpu_model() -> str:
    """The processor's name from /proc/cpuinfo ("" when it cannot be read)."""
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith(("model name", "Model", "Hardware")):
                    return " ".join(line.split(":", 1)[1].split())
    except OSError:
        pass
    return ""


def sample(seconds: float = 1.0) -> tuple[float, float, float] | None:
    """The CPU use and the bytes per second received and sent, over a short sample (a CPU reading needs two points
    in time: the first one alone always says 0%); None when they cannot be measured."""
    try:
        import psutil

        psutil.cpu_percent(None)
        first = psutil.net_io_counters()
        time.sleep(seconds)
        second = psutil.net_io_counters()
        return psutil.cpu_percent(None), (second.bytes_recv - first.bytes_recv) / seconds, (second.bytes_sent - first.bytes_sent) / seconds
    except Exception as e:
        logger.debug(f"tgbot: sampling failed: {e}")
        return None


def _process_name(name: str) -> str:
    """A process by its program's name only: no path, no arguments (they can hold addresses)."""
    first = (name or "").split()[0] if (name or "").split() else "?"
    return first.rsplit("/", 1)[-1][:24]


#: Names easier to read than their unit's
_SERVICE_NAME = {"wg-quick@hiddifywg": "wireguard"}


def _rate(value: float, lang: str) -> str:
    """A speed, in the unit that fits it."""
    for unit, size in (("GB/s", 1024**3), ("MB/s", 1024**2), ("KB/s", 1024)):
        if value >= size:
            return f"{value / size:.1f} {unit}"
    return f"{value:.0f} B/s"


def _server_lines(ctx: Ctx) -> list[str]:
    """The server: what it is, how busy it is, its network and where it is."""
    from hiddifypanel.hutils import system_metrics

    lang = ctx.lang
    m = system_metrics.snapshot(process_limit=3)
    host, cpu, mem, disk, net = m.host, m.cpu, m.memory, m.disk, m.network
    now = sample()
    cpu_percent = now[0] if now else cpu.percent
    about = [
        f"{ctx.tr(T.st_os)}: {h(host.os_pretty or host.os_name or '—')}",
        f"{ctx.tr(T.st_kernel)}: {h(host.kernel or '—')}" + (f" · {h(host.arch)}" if host.arch else ""),
        f"{ctx.tr(T.st_cpu_model)}: {h(_cpu_model() or '—')} · {ctx.tr(T.cores, n=cpu.cores)}",
        f"{ctx.tr(T.st_panel)}: v{h(hiddifypanel.__version__)}",
        f"{ctx.tr(T.uptime)}: {duration(host.uptime_s, lang)}",
    ]
    lines = [f"🖥 <b>{ctx.tr(T.st_server)}</b>", "<blockquote expandable>" + "\n".join(about) + "</blockquote>", f"📈 <b>{ctx.tr(T.st_resources)}</b>"]
    load = " ".join(f"{x:.2f}" for x in cpu.load_avg[:3])
    lines += _meter(ctx.tr(T.cpu), cpu_percent, ctx.tr(T.st_load, load=load) if load else ctx.tr(T.cores, n=cpu.cores))
    lines += _meter(ctx.tr(T.ram), mem.percent, f"{fmt_gb(mem.used_gb, lang)} / {fmt_gb(mem.total_gb, lang)}")
    if mem.swap_total_gb:
        lines += _meter(ctx.tr(T.st_swap), mem.swap_percent, f"{fmt_gb(mem.swap_used_gb, lang)} / {fmt_gb(mem.swap_total_gb, lang)}")
    lines += _meter(ctx.tr(T.disk), disk.percent, f"{fmt_gb(disk.used_gb, lang)} / {fmt_gb(disk.total_gb, lang)}")
    if m.processes.cpu:
        busy = [f"{h(_process_name(p.name))} {p.percent:.0f}%" for p in m.processes.cpu[:3]]
        lines.append(f"🔥 <i>{ctx.tr(T.st_top)}: {' · '.join(busy)}</i>")

    lines += ["", f"🌐 <b>{ctx.tr(T.st_network)}</b>"]
    if now:
        lines.append(f"{ctx.tr(T.st_speed)}: ⬇️ <b>{_rate(now[1], lang)}</b> · ⬆️ <b>{_rate(now[2], lang)}</b>")
    lines.append(f"🔌 {ctx.tr(T.st_conns, n=net.connections, ips=net.unique_ips)}")
    lines.append(f"{ctx.tr(T.st_since_boot)}: ⬇️ {fmt_gb(net.recv_gb, lang)} · ⬆️ {fmt_gb(net.sent_gb, lang)}")
    lines.append(_place_line(ctx))
    return lines


def _users_lines(ctx: Ctx) -> list[str]:
    admin = ctx.admin
    assert admin
    lang = ctx.lang
    stats = DailyUsage.get_dashboard_stats(admin_id=admin.id, series_days=30)
    users, totals = stats.users, stats.usage.totals
    traffic = [
        f"{ctx.tr(T.traffic_today)}  <b>{fmt_bytes(totals.today, lang)}</b>",
        f"{ctx.tr(T.traffic_yesterday)}  {fmt_bytes(totals.yesterday, lang)}",
        f"{ctx.tr(T.traffic_week)}  {fmt_bytes(totals.week, lang)}",
        f"{ctx.tr(T.traffic_month)}  {fmt_bytes(totals.month, lang)}",
        f"{ctx.tr(T.traffic_total)}  {fmt_bytes(totals.total, lang)}",
    ]
    return [
        f"👥 <b>{ctx.tr(T.users_block)}</b>",
        ctx.tr(T.users_line, total=users.total, active=users.active),
        ctx.tr(T.online_line, now=users.online.m5, today=users.online.today),
        "",
        f"📊 <b>{ctx.tr(T.traffic)}</b>",
        "<blockquote expandable>" + "\n".join(traffic) + "</blockquote>",
    ]


def status_screen(ctx: Ctx) -> Screen:
    """The whole server on one screen: what it is and how busy, its network and place, every service of the panel,
    then the users and the traffic. The long parts fold (a tap opens them). Agents see only their users."""
    admin = ctx.admin
    assert admin
    lines = [f"📊 <b>{ctx.tr(T.status_title)}</b>", RULE]
    # Server health is the operators' business, not resellers'.
    if admin.mode != AdminMode.agent:
        try:
            lines += _server_lines(ctx)
        except Exception as e:
            logger.warning(f"tgbot: system stats failed: {e}")
        lines += ["", *_services_lines(ctx), ""]
    lines += _users_lines(ctx)
    now = datetime.datetime.now()
    lines.append(f"<i>{ctx.tr(T.updated_at, time=tg_time(now, 'T', now.strftime('%H:%M:%S')))}</i>")
    return Screen("\n".join(lines), keyboard([btn(ctx.tr(T.refresh), Cb.status), btn(ctx.tr(T.back), Cb.back)]))


@route(Cb.status, admin=True)
def show_status(ctx: Ctx, _args: list[str]) -> None:
    ctx.toast()
    ctx.show(status_screen(ctx))


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


def service_details(units=SERVICES) -> list[dict[str, str]]:
    """Every installed unit's state, how long it has run, its memory and restarts, in one ``systemctl show`` call."""
    props = "Id,LoadState,ActiveState,SubState,ActiveEnterTimestampMonotonic,MemoryCurrent,NRestarts"
    try:
        out = subprocess.run(["systemctl", "show", "-p", props, *units], capture_output=True, text=True, timeout=10).stdout
    except Exception as e:
        logger.warning(f"tgbot: systemctl show failed: {e}")
        return [{"Id": u, "ActiveState": state, "LoadState": "loaded"} for u, state in service_states(units).items()]
    found = []
    for block in out.strip().split("\n\n"):
        unit = dict(line.split("=", 1) for line in block.splitlines() if "=" in line)
        if unit.get("Id") and unit.get("LoadState") != "not-found":
            found.append(unit)
    return found


def _monotonic_now_us() -> int:
    return int(time.monotonic() * 1_000_000)


def _services_lines(ctx: Ctx) -> list[str]:
    """A line per service of the panel: its state, for how long, its memory and its restarts; all folded under a
    count of the running ones."""
    units = service_details()
    rows, running = [], 0
    for u in units:
        state = u.get("ActiveState", "unknown")
        mark = _STATE_MARK.get(state, "❌")
        running += state == "active"
        unit = u["Id"].removesuffix(".service")
        name = _SERVICE_NAME.get(unit, unit.removeprefix("hiddify-"))
        parts = [f"{mark} <b>{h(name)}</b>"]
        if state == "active":
            since = int(u.get("ActiveEnterTimestampMonotonic") or 0)
            if since:
                parts.append(duration(max(_monotonic_now_us() - since, 0) // 1_000_000, ctx.lang))
            mem = u.get("MemoryCurrent") or ""
            if mem.isdigit() and int(mem) < 1 << 60:  # "[not set]" or the max value when not counted
                parts.append(_rate(int(mem), ctx.lang).removesuffix("/s"))
        else:
            parts.append(h(f"{state} ({u.get('SubState', '')})".replace(" ()", "")))
        restarts = u.get("NRestarts") or "0"
        if restarts.isdigit() and int(restarts):
            parts.append(f"↻ {restarts}")
        rows.append(" · ".join(parts))
    head = f"🧩 <b>{ctx.tr(T.check_services)}</b>  {'✅' if running == len(units) else '⚠️'} {ctx.tr(T.st_running, ok=running, n=len(units))}"
    return [head, "<blockquote expandable>" + "\n".join(rows) + "</blockquote>"] if rows else [head]


def _place_line(ctx: Ctx) -> str:
    """The server's address and where it is, in one line."""
    from hiddifypanel.hutils.network import get_ip_str

    ip = get_ip_str(4) or get_ip_str(6) or ""
    geo = _geo(ip) if ip else {}
    where = ", ".join(p for p in (geo.get("country"), geo.get("city")) if p)
    parts = [f"📍 <code>{h(ip or '—')}</code>"]
    if where:
        parts.append(f"{flag(geo.get('code', ''))} {h(where)}".strip())
    if geo.get("org"):
        parts.append(h(geo["org"]))
    return " · ".join(parts)


def check_text(ctx: Ctx) -> str:
    """The server's public address and where it is, then every service; only the service table is monospaced
    (its unit names are English), so the labels read right in every language."""
    from hiddifypanel.hutils.network import get_ip_str

    ip = get_ip_str(4) or get_ip_str(6) or ""
    geo = _geo(ip) if ip else {}
    country = " ".join(p for p in (geo.get("country") or "—", flag(geo.get("code", ""))) if p)
    place = [
        f"{ctx.tr(T.check_country)}: {h(country)}",
        f"{ctx.tr(T.check_city)}: {h(geo.get('city') or '—')}",
        f"{ctx.tr(T.check_org)}: {h(geo.get('org') or '—')}",
        f"IP: <code>{h(ip or '—')}</code>",
    ]
    width = max(len(u) for u in SERVICES) + 2
    units = "\n".join(f"{unit.ljust(width)}{_STATE_MARK.get(state, '❌')}" for unit, state in service_states().items())
    return "\n".join(
        [
            f"🌐 <b>{ctx.tr(T.check_ip)}</b>",
            "<blockquote>" + "\n".join(place) + "</blockquote>",
            f"🧩 <b>{ctx.tr(T.check_services)}</b>",
            f"<pre>{h(units)}</pre>",
        ]
    )


@route(Cb.check, admin=True)
def show_check(ctx: Ctx, args: list[str]) -> None:
    """Check Status is part of the status screen now (old messages may still hold its button)."""
    show_status(ctx, args)
