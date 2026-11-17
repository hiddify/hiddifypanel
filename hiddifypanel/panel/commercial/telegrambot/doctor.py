"""The connection doctor: "I can't connect" checks what the panel can see (the account, the person's last connection,
the server's services, the address in their links) and says in plain words where the problem is and what to do.
A problem on the server is also told to the admins (once in a while, not for every check)."""

from __future__ import annotations

import concurrent.futures
import random
import ipaddress
import socket
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from loguru import logger

from hiddifypanel.cache import redis_client
from hiddifypanel.models import AdminMode, AdminUser, User

from . import accounts, bot
from .accounts import Status
from .texts import T, t
from .ui import Cb, Ctx, Screen, Style, ago, btn, h, keyboard, lang_of, route

#: The services a proxy connection goes through; one the server does not use (not enabled) is not a problem.
PROXY_UNITS = ("hiddify-haproxy", "hiddify-xray", "hiddify-singbox", "hiddify-core")
CHECK_TIMEOUT = 3
ADMIN_ALERT_EVERY = 30 * 60
_ALERT_KEY = "tgbot:doctor:alerted"


class Level(StrEnum):
    ok = "ok"
    warn = "warn"
    bad = "bad"


MARK = {Level.ok: "✅", Level.warn: "⚠️", Level.bad: "❌"}


@dataclass(frozen=True, slots=True)
class Finding:
    level: Level
    text: str


@dataclass(frozen=True, slots=True)
class Diagnosis:
    account: Finding
    device: Finding
    server: Finding
    address: Finding
    #: Where the problem is: "account", "server", "address", or "" (nothing the panel can see).
    cause: str
    #: The server's units that should run and do not.
    down: tuple[str, ...] = ()


def down_units(units: tuple[str, ...] = PROXY_UNITS) -> tuple[str, ...]:
    """The units that are enabled (the server uses them) but not running."""
    try:
        enabled = subprocess.run(["systemctl", "is-enabled", *units], capture_output=True, text=True, timeout=CHECK_TIMEOUT).stdout.split()
        active = subprocess.run(["systemctl", "is-active", *units], capture_output=True, text=True, timeout=CHECK_TIMEOUT).stdout.split()
    except Exception as e:
        logger.warning(f"tgbot doctor: systemctl failed: {e}")
        return ()
    if len(enabled) != len(units) or len(active) != len(units):
        return ()
    return tuple(u for u, en, ac in zip(units, enabled, active) if en in ("enabled", "static", "alias") and ac != "active")


def address_answers(host: str) -> bool:
    """The address in the person's links resolves (an IP always does)."""
    if not host:
        return False
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        pass
    with concurrent.futures.ThreadPoolExecutor(1) as pool:
        try:
            return bool(pool.submit(socket.getaddrinfo, host, 443).result(timeout=CHECK_TIMEOUT))
        except Exception:
            return False


def diagnose(user: User, lang: str, progress: Callable[[list[Finding]], None] | None = None) -> Diagnosis:
    """The checks, quick ones first; ``progress`` sees the findings so far after each slow step."""
    st = accounts.status(user)
    account_text = {
        Status.active: T.dr_account_ok,
        Status.disabled: T.dr_account_disabled,
        Status.expired: T.dr_account_expired,
        Status.no_data: T.dr_account_no_data,
    }[st]
    account = Finding(Level.ok if st is Status.active else Level.bad, t(account_text, lang))

    if accounts.is_online(user):
        device = Finding(Level.ok, t(T.dr_device_now, lang))
    elif user.last_online and user.last_online.year > 2000:
        device = Finding(Level.warn, t(T.dr_device_ago, lang, when=ago(user.last_online, lang)))
    else:
        device = Finding(Level.warn, t(T.dr_device_never, lang))

    if progress:
        progress([account, device])
    down = down_units()
    server = Finding(Level.bad, t(T.dr_server_bad, lang)) if down else Finding(Level.ok, t(T.dr_server_ok, lang))

    if progress:
        progress([account, device, server])
    reachable = address_answers(accounts.user_host())
    address = Finding(Level.ok, t(T.dr_address_ok, lang)) if reachable else Finding(Level.bad, t(T.dr_address_bad, lang))

    cause = "account" if st is not Status.active else "server" if down else "address" if not reachable else ""
    return Diagnosis(account, device, server, address, cause, down)


def tell_admins(user: User, diagnosis: Diagnosis) -> None:
    """A server-side problem found by someone's check reaches the owners (at most every 30 minutes)."""
    if diagnosis.cause not in ("server", "address") or not redis_client.set(_ALERT_KEY, 1, nx=True, ex=ADMIN_ALERT_EVERY):
        return
    what = ", ".join(diagnosis.down) if diagnosis.down else accounts.user_host()
    for admin in AdminUser.query.filter(AdminUser.mode == AdminMode.super_admin, AdminUser.telegram_id.isnot(None), AdminUser.deleted.is_(False)).all():
        lang = lang_of(admin, admin=True)
        key = T.dr_admin_server if diagnosis.cause == "server" else T.dr_admin_address
        try:
            bot.send_message(admin.telegram_id, f"🩺 {t(key, lang, name=h(user.name), what=h(what))}")
        except Exception as e:
            logger.debug(f"tgbot doctor: admin {admin.id} not told: {e}")


def doctor_screen(ctx: Ctx, d: Diagnosis) -> Screen:
    rows = [f"{MARK[f.level]} {h(f.text)}" for f in (d.account, d.device, d.server, d.address)]
    verdict = {
        "account": T.dr_v_account,
        "server": T.dr_v_server,
        "address": T.dr_v_address,
    }.get(d.cause)
    if verdict:
        tail = f"<b>{ctx.tr(verdict)}</b>"
    else:
        tips = [ctx.tr(T.dr_tip_update), ctx.tr(T.dr_tip_network), ctx.tr(T.dr_tip_support)]
        tail = f"<b>{ctx.tr(T.dr_v_fine)}</b>\n" + "\n".join(f"{i}. {h(tip)}" for i, tip in enumerate(tips, 1))
    text = "\n".join([f"🩺 <b>{ctx.tr(T.dr_title)}</b>", "", "<blockquote>" + "\n".join(rows) + "</blockquote>", "", tail])
    return Screen(
        text,
        keyboard(
            [btn(ctx.tr(T.dr_again), Cb.doctor, style=Style.primary), btn(ctx.tr(T.support), Cb.support)],
            [btn(ctx.tr(T.guide), Cb.guide)] if not d.cause else [],
            [btn(ctx.tr(T.back), Cb.back)],
        ),
    )


def _progress_text(ctx: Ctx, found: list[Finding]) -> str:
    rows = "\n".join(f"{MARK[f.level]} {h(f.text)}" for f in found)
    quote = f"<blockquote>{rows}</blockquote>\n" if rows else ""
    return f"🩺 <b>{ctx.tr(T.dr_title)}</b>\n\n{quote}<i>{ctx.tr(T.dr_running)}</i>"


@route(Cb.doctor, admin=False)
def run_doctor(ctx: Ctx, _args: list[str]) -> None:
    user = ctx.user
    assert user
    ctx.toast()
    # Each check shows up as it is done: as a draft (Bot API 9.3) when the result comes as a new message under the
    # card, else by editing this message. A draft Telegram refuses falls back to the edits.
    drafts = {"on": ctx.on_photo or not ctx.message_id, "id": random.randint(1, 2**31 - 1)}

    def show(found: list[Finding]) -> None:
        text = _progress_text(ctx, found)
        if drafts["on"]:
            try:
                bot.send_message_draft(ctx.chat_id, drafts["id"], text, parse_mode="HTML")
                return
            except Exception as e:
                logger.debug(f"tgbot doctor: draft refused: {e}")
                drafts["on"] = False
        ctx.show(Screen(text))

    show([])
    diagnosis = diagnose(user, ctx.lang, show)
    ctx.show(doctor_screen(ctx, diagnosis))
    tell_admins(user, diagnosis)


