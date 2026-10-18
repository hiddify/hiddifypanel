"""A pocket dashboard: server health, users and traffic at a glance."""

from __future__ import annotations

import datetime

from loguru import logger

from hiddifypanel.models import AdminMode, DailyUsage

from .texts import T
from .ui import RULE, Cb, Ctx, Screen, bar, btn, duration, fmt_bytes, fmt_gb, keyboard, level_dot, route


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
