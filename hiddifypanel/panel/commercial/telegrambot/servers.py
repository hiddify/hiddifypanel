"""Advanced mode: the panel's servers and domains in the bot.

- Nodes: every server of the panel (this one and its remote nodes), up or not, and how busy each is.
- Domains: each domain of the panel, whether its name points to this server and how long its certificate lasts.
- Node alerts: a node that does not answer for a while is told to the operators at once, and again when it is back.
- Morning report: each admin's day in one message (their users, yesterday's traffic, and for operators the
  services, the nodes and the certificates), every morning; each admin can turn theirs off in Settings.

All of it only while the owner keeps Advanced on; agents (resellers) see only the morning report of their users.
"""

from __future__ import annotations

import datetime
import json
import time
from concurrent.futures import ThreadPoolExecutor

from loguru import logger

from hiddifypanel.cache import redis_client
from hiddifypanel.models import AdminMode, AdminUser, BotPref, ConfigEnum, hconfig

from . import advanced, bot
from .texts import T, t
from .ui import RULE, Cb, Ctx, Screen, Style, btn, h, keyboard, lang_of, level_dot, route, tg_time, with_retry

#: A node that fails this many checks in a row (one every few minutes) is down: a slow answer is not an outage.
NODE_FAILS = 2
#: Certificates ending this soon are named (the morning report, the domains screen).
CERT_SOON = datetime.timedelta(days=14)
#: The morning report's hour (the server's time).
MORNING_HOUR = 8
#: Bot preference of an admin who turned their morning report off ("0"); on by default.
MORNING_PREF = "adv_morning"
MAX_DOMAINS = 40

_DOWN = "tgbot:nodes:down"  # json {node id: since (unix time)}
_FAILS = "tgbot:nodes:fails"  # json {node id: failed checks in a row}
_KEEP = 7 * 24 * 3600


def _operator(admin: AdminUser | None) -> bool:
    return admin is not None and admin.mode != AdminMode.agent


# --------------------------------------------------------------------------- nodes


def _nodes():
    """Every server of the panel with its numbers (this one first)."""
    from hiddifypanel.hutils.node_system import collect_system_stats

    return collect_system_stats(None, process_limit=0).node_stats


def _flag(code: str) -> str:
    from .status import flag

    return flag(code)


def node_lines(ctx: Ctx, nodes) -> list[str]:
    lines = []
    for n in nodes:
        name = h(n.name if n.id else (n.name if n.name not in ("", "this-server") else ctx.tr(T.nd_this)))
        place = f" {_flag(n.country)}" if n.country else ""
        if not n.ok:
            reason = h(n.error_code or n.error or ctx.tr(T.unknown))[:80]
            lines += [f"🔴 <b>{name}</b>{place}", f"<i>{ctx.tr(T.nd_no_answer)}: {reason}</i>", ""]
            continue
        cpu = n.cpu.percent if n.cpu else 0.0
        mem = n.memory.percent if n.memory else 0.0
        disk = n.disk.percent if n.disk else 0.0
        worst = max(cpu, mem, disk) / 100
        version = getattr(n.host, "panel_version", "") if n.host else ""
        lines += [
            f"{level_dot(worst)} <b>{name}</b>{place}" + (f"  <i>v{h(version)}</i>" if version else ""),
            f"CPU {cpu:.0f}% · RAM {mem:.0f}% · {ctx.tr(T.nd_disk)} {disk:.0f}%",
            "",
        ]
    return lines


def nodes_screen(ctx: Ctx) -> Screen:
    try:
        nodes = _nodes()
    except Exception as e:
        logger.warning(f"tgbot: nodes not read: {e}")
        nodes = []
    up = sum(1 for n in nodes if n.ok)
    lines = [f"🖥 <b>{ctx.tr(T.nd_title)}</b>", RULE, ctx.tr(T.nd_summary, up=up, n=len(nodes)), "", *node_lines(ctx, nodes)]
    now = datetime.datetime.now()
    lines.append(f"<i>{ctx.tr(T.updated_at, time=tg_time(now, 'T', now.strftime('%H:%M:%S')))}</i>")
    return Screen("\n".join(lines), keyboard([btn(ctx.tr(T.refresh), Cb.nodes), btn(f"🌐 {ctx.tr(T.nd_domains)}", Cb.domains)], [btn(ctx.tr(T.back), Cb.back)]))


@route(Cb.nodes, admin=True)
def show_nodes(ctx: Ctx, _args: list[str]) -> None:
    if not advanced.is_on() or not _operator(ctx.admin):
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    ctx.toast(ctx.tr(T.nd_checking))
    ctx.show(nodes_screen(ctx))


# --------------------------------------------------------------------------- domains


def _server_ips() -> set[str]:
    from hiddifypanel.hutils.network import get_ips

    try:
        return {str(ip) for ip in get_ips()}
    except Exception:
        return set()


def _resolve(name: str) -> set[str]:
    from hiddifypanel.hutils.network import get_domain_ips

    try:
        return {str(ip) for ip in get_domain_ips(name, retry=1)}
    except Exception:
        return set()


def domain_rows() -> list[dict]:
    """This server's domains (not the nodes'), each with where its name points and its certificate."""
    from hiddifypanel.models import Domain, DomainType

    domains = Domain.query.filter(Domain.child_id == 0).order_by(Domain.sort_order, Domain.id).limit(MAX_DOMAINS).all()
    real = [d for d in domains if d.mode in (DomainType.direct, DomainType.cdn, DomainType.sub_link_only, DomainType.relay) and "*" not in d.domain]
    with ThreadPoolExecutor(max_workers=8) as pool:
        resolved = dict(zip([d.id for d in real], pool.map(lambda d: _resolve(d.domain), real)))
    mine = _server_ips()
    rows = []
    for d in domains:
        ips = resolved.get(d.id)
        cert = d.certificate
        rows.append(
            {
                "name": d.domain,
                "mode": str(d.mode),
                # direct names must point here; a CDN's points to the CDN (it only has to resolve)
                "dns": None if ips is None else (bool(ips) and (d.mode != DomainType.direct or bool(ips & mine) or not mine)),
                "expires": cert.expires_at if cert and cert.expires_at and not cert.self_signed else None,
                "error": bool(cert and cert.last_renewal_error),
            }
        )
    return rows


def _cert_text(ctx: Ctx, expires: datetime.datetime | None) -> str:
    if expires is None:
        return ""
    left = (expires - datetime.datetime.utcnow()).days
    mark = "🔒" if left > CERT_SOON.days else ("⚠️" if left >= 0 else "⛔️")
    return f"{mark} {ctx.tr(T.dm_cert_days, days=max(left, 0))}"


def domains_screen(ctx: Ctx) -> Screen:
    try:
        rows = domain_rows()
    except Exception as e:
        logger.warning(f"tgbot: domains not read: {e}")
        rows = []
    good = sum(1 for r in rows if r["dns"] is not False)
    lines = [f"🌐 <b>{ctx.tr(T.dm_title)}</b>", RULE, ctx.tr(T.dm_summary, ok=good, n=len(rows)), ""]
    for r in rows:
        mark = {True: "🟢", False: "🔴", None: "⚪️"}[r["dns"]]
        parts = [f"{mark} <code>{h(r['name'])}</code>", f"<i>{h(r['mode'])}</i>"]
        if cert := _cert_text(ctx, r["expires"]):
            parts.append(cert)
        if r["error"]:
            parts.append(f"⚠️ {ctx.tr(T.dm_renew_failed)}")
        lines.append(" · ".join(parts))
    if not rows:
        lines.append(ctx.tr(T.dm_none))
    lines += ["", f"<i>{ctx.tr(T.dm_legend)}</i>"]
    return Screen("\n".join(lines), keyboard([btn(ctx.tr(T.refresh), Cb.domains), btn(f"🖥 {ctx.tr(T.nd_title)}", Cb.nodes)], [btn(ctx.tr(T.back), Cb.back)]))


@route(Cb.domains, admin=True)
def show_domains(ctx: Ctx, _args: list[str]) -> None:
    if not advanced.is_on() or not _operator(ctx.admin):
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    ctx.toast(ctx.tr(T.nd_checking))
    ctx.show(domains_screen(ctx))


def status_rows(ctx: Ctx) -> list[list]:
    """The status screen's keys to these screens (Advanced, operators)."""
    if not advanced.is_on() or not _operator(ctx.admin):
        return []
    from .ops import status_rows as ops_rows

    return [[btn(f"🖥 {ctx.tr(T.nd_title)}", Cb.nodes), btn(f"🌐 {ctx.tr(T.nd_domains)}", Cb.domains)], *ops_rows(ctx)]


# --------------------------------------------------------------------------- node alerts


def _load(key: str) -> dict[str, float]:
    raw = redis_client.get(key)
    try:
        return {str(k): float(v) for k, v in json.loads(raw).items()} if raw else {}
    except (TypeError, ValueError):
        return {}


def _operators() -> list[AdminUser]:
    return AdminUser.query.filter(AdminUser.telegram_id.isnot(None), AdminUser.telegram_id != 0, AdminUser.deleted.is_(False), AdminUser.mode != AdminMode.agent).all()


def _tell(chat_id: int, text: str, markup) -> None:
    try:
        with_retry(lambda: bot.send_message(chat_id, text, reply_markup=markup), attempts=3)
    except Exception as e:
        logger.debug(f"tgbot nodes: {chat_id} not told: {e}")


def watch_nodes() -> None:
    """Scheduled every few minutes (one worker): remote nodes that stop answering, and that come back."""
    from hiddifypanel import hutils

    if not hconfig(ConfigEnum.telegram_bot_token) or not advanced.is_on() or not hutils.node.is_parent():
        return
    try:
        nodes = [n for n in _nodes() if n.id > 0]
    except Exception as e:
        logger.debug(f"tgbot nodes: not checked: {e}")
        return
    fails, down = _load(_FAILS), _load(_DOWN)
    went, back = [], []
    now = time.time()
    for n in nodes:
        key = str(n.id)
        if n.ok:
            fails.pop(key, None)
            if key in down:
                back.append((n, down.pop(key)))
            continue
        fails[key] = fails.get(key, 0) + 1
        if fails[key] >= NODE_FAILS and key not in down:
            down[key] = now
            went.append(n)
    known = {str(n.id) for n in nodes}  # a node deleted while down is forgotten
    down = {k: v for k, v in down.items() if k in known}
    redis_client.set(_FAILS, json.dumps({k: v for k, v in fails.items() if k in known}), ex=_KEEP)
    redis_client.set(_DOWN, json.dumps(down), ex=_KEEP)
    if not went and not back:
        return
    for admin in _operators():
        lang = lang_of(admin, admin=True)
        for n in went:
            _tell(admin.telegram_id, f"🚨 {t(T.nd_down, lang, name=h(n.name), reason=h(n.error_code or n.error or '?')[:80])}", keyboard([btn(f"🖥 {t(T.nd_title, lang)}", Cb.nodes, style=Style.primary)]))
        for n, since in back:
            _tell(admin.telegram_id, f"✅ {t(T.nd_back, lang, name=h(n.name), minutes=max(round((now - since) / 60), 1))}", None)
    logger.info(f"tgbot nodes: down {[n.name for n in went]}, back {[n.name for n, _ in back]}")


# --------------------------------------------------------------------------- morning report


def morning_on(admin: AdminUser) -> bool:
    try:
        return BotPref.get(admin.telegram_id or 0, MORNING_PREF) != "0"
    except Exception as e:  # no database (a test, a script): the default
        logger.debug(f"tgbot: morning report preference not read: {e}")
        return True


def report_text(admin: AdminUser, lang: str) -> str:
    from hiddifypanel.models import DailyUsage, User

    from . import accounts
    from .status import service_states
    from .ui import fmt_bytes

    users = User.query.filter(User.deleted.is_(False), User.added_by.in_(admin.recursive_sub_admins_ids())).all()
    expiring = sum(1 for u in users if accounts.is_expiring(u))
    ended = sum(1 for u in users if accounts.matches(u, accounts.Filter.ended))
    stats = DailyUsage.get_dashboard_stats(admin_id=admin.id, series_days=2)
    today = datetime.date.today()
    lines = [
        f"☀️ <b>{t(T.mr_title, lang)}</b>  {tg_time(today, 'D', today.isoformat())}",
        RULE,
        f"👥 {t(T.users_line, lang, total=stats.users.total, active=stats.users.active)}",
        f"🟢 {t(T.mr_online, lang, n=stats.users.online.today)}",
        f"⏳ {t(T.mr_expiring, lang, n=expiring)}",
        f"⛔️ {t(T.mr_ended, lang, n=ended)}",
        f"📊 {t(T.traffic_yesterday, lang)}: <b>{fmt_bytes(stats.usage.totals.yesterday, lang)}</b>",
    ]
    if _operator(admin):
        states = service_states()
        running = sum(1 for s in states.values() if s == "active")
        lines += ["", f"{'✅' if running == len(states) else '⚠️'} {t(T.mr_services, lang, ok=running, n=len(states))}"]
        down = _load(_DOWN)
        if down:
            lines.append(f"🔴 {t(T.mr_nodes_down, lang, n=len(down))}")
        soon = _certs_ending()
        if soon:
            lines.append(f"🔒 {t(T.mr_certs, lang, n=len(soon), names=h(', '.join(soon[:3])))}")
    return "\n".join(lines)


def _certs_ending() -> list[str]:
    from hiddifypanel.models import Domain

    limit = datetime.datetime.utcnow() + CERT_SOON
    return [d.domain for d in Domain.query.filter(Domain.child_id == 0).all() if d.certificate and d.certificate.expires_at and not d.certificate.self_signed and d.certificate.expires_at < limit]


def morning_report() -> None:
    """Scheduled every morning; the redis key keeps a second worker (or a restart) from sending twice."""
    if not hconfig(ConfigEnum.telegram_bot_token) or not advanced.is_on():
        return
    if not redis_client.set(f"tgbot:morning:{datetime.date.today()}", 1, nx=True, ex=36 * 3600):
        return
    from . import register_bot

    if not bot.username:
        register_bot()
    admins = AdminUser.query.filter(AdminUser.telegram_id.isnot(None), AdminUser.telegram_id != 0, AdminUser.deleted.is_(False)).all()
    sent = 0
    for admin in admins:
        if not morning_on(admin):
            continue
        lang = lang_of(admin, admin=True)
        try:
            text = report_text(admin, lang)
        except Exception as e:
            logger.warning(f"tgbot: morning report of admin {admin.id} failed: {e}")
            continue
        rows = [[btn(f"⏳ {t(T.f_expiring, lang)}", Cb.users, "s", 0), btn(f"📊 {t(T.status_title, lang)}", Cb.status)]]
        _tell(admin.telegram_id, text, keyboard(*rows))
        sent += 1
    logger.info(f"tgbot: morning report to {sent} admins")


def settings_lines(ctx: Ctx) -> list[str]:
    if not advanced.is_on() or ctx.admin is None:
        return []
    from .miniapp import locked

    on = morning_on(ctx.admin)
    return [
        f"☀️ {ctx.tr(T.mr_title)}: <b>{ctx.tr(T.on if on else T.off)}</b>",
        f"<i>{ctx.tr(T.mr_hint, hour=f'{MORNING_HOUR:02d}:00')}</i>",
        f"🔐 {ctx.tr(T.bl_title)}: <b>{len(locked(ctx.chat_id))}</b>",
    ]


def settings_rows(ctx: Ctx) -> list[list]:
    if not advanced.is_on() or ctx.admin is None:
        return []
    on = morning_on(ctx.admin)
    return [[btn(f"☀️ {ctx.tr(T.mr_title)}: {ctx.tr(T.turn_off if on else T.turn_on)}", Cb.morning, 0 if on else 1, style=None if on else Style.success)], [btn(f"🔐 {ctx.tr(T.bl_title)}", Cb.lock)]]


@route(Cb.morning, admin=True)
def set_morning(ctx: Ctx, args: list[str]) -> None:
    from hiddifypanel.database import db

    from .admin_settings import settings_screen

    if not advanced.is_on() or args[:1] not in (["0"], ["1"]):
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    BotPref.put(ctx.chat_id, MORNING_PREF, args[0])
    db.session.commit()
    ctx.toast(ctx.tr(T.adv_saved))
    ctx.show(settings_screen(ctx))
