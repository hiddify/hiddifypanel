"""The account card (a QR code with the account as its caption) and what a user sees: their card and their links.
The admin side sends the same card for each user it creates."""

from __future__ import annotations

import datetime

from loguru import logger
from telebot import types

from hiddifypanel.models import User

from . import accounts, bot
from .accounts import Status
from .texts import T, t
from .ui import Cb, Ctx, Screen, ago, app_row, bar, btn, can_open_as_app, fmt_gb, h, keyboard, route

_STATUS_TEXT: dict[Status, T] = {
    Status.active: T.status_active,
    Status.disabled: T.status_disabled,
    Status.expired: T.status_expired,
    Status.no_data: T.status_no_data,
}
BAR = 16


def account_card(user: User, lang: str, *, note: str | None = None) -> str:
    """The account at a glance: name and state, data and time as bars, links. Fits a photo caption."""
    st = accounts.status(user)
    online = accounts.is_online(user)
    head = f"{accounts.STATUS_ICON[st]} {t(_STATUS_TEXT[st], lang)}" + (f"  ·  ⚡️ {t(T.online_now, lang)}" if online else "")

    used, total = user.current_usage_GB, user.usage_limit_GB
    ratio = accounts.usage_ratio(user)
    data = [
        f"📦 <b>{t(T.data, lang)}</b>",
        f"<code>{bar(ratio, BAR)}</code>  <b>{min(round(ratio * 100), 999)}%</b>",
        t(T.used_of, lang, used=fmt_gb(used, lang), total=fmt_gb(total, lang), left=fmt_gb(max(total - used, 0), lang)),
    ]

    days_total = user.package_days or 0
    if user.start_date is None:
        time = [f"⏳ <b>{t(T.time, lang)}</b>", f"<code>{bar(1, BAR)}</code>", t(T.days_not_started, lang, total=days_total)]
    elif user.remaining_days < 0:
        time = [f"⏳ <b>{t(T.time, lang)}</b>", f"<code>{bar(0, BAR)}</code>", t(T.days_expired, lang)]
    else:
        left = user.remaining_days
        end = user.start_date + datetime.timedelta(days=days_total)
        time = [
            f"⏳ <b>{t(T.time, lang)}</b>",
            f"<code>{bar(left / days_total if days_total else 0, BAR)}</code>  <b>{round(left / days_total * 100) if days_total else 0}%</b>",
            t(T.days_left, lang, left=left, total=days_total, date=end.isoformat()),
        ]

    lines = [f"✨ <b>{h(user.name)}</b>", head, "", "<blockquote>" + "\n".join(data) + "\n\n" + "\n".join(time) + "</blockquote>"]
    reset = user.days_to_reset()
    if isinstance(reset, int) and 0 <= reset < 500 and user.mode != "no_reset":
        lines.append(f"🔁 {t(T.resets_in, lang, n=reset)}")
    if not online:
        lines.append(f"🕒 {t(T.last_online, lang)}  ·  {ago(user.last_online, lang)}")
    links = accounts.links(user)
    lines += ["", f'🔗 <a href="{h(links.home)}">{t(T.link_home, lang)}</a>  ·  <a href="{h(links.sub)}">{t(T.link_sub, lang)}</a>']
    if note:
        lines += ["", f"✅ <i>{h(note)}</i>"]
    return "\n".join(lines)


def links_text(user: User, lang: str) -> str:
    links = accounts.links(user)
    return "\n".join(
        [
            f"🔗 <b>{t(T.links_title, lang)}</b>  ·  {h(user.name)}",
            "",
            f"🌐 <b>{t(T.link_home, lang)}</b>",
            f"<code>{h(links.home)}</code>",
            "",
            f"📥 <b>{t(T.link_sub, lang)}</b>",
            f"<code>{h(links.sub)}</code>",
            "",
            f"📱 <b>{t(T.link_hiddify, lang)}</b>",
            f"<code>{h(links.hiddify)}</code>",
            "",
            f"<i>{t(T.links_hint, lang)}</i>",
        ]
    )


# --------------------------------------------------------------------------- the card an admin shares


def share_screen(lang: str, user: User, note: str | None = None) -> Screen:
    """The card an admin forwards to a customer: refresh keeps it current, manage opens the user's controls."""
    links = accounts.links(user)
    return Screen(
        account_card(user, lang, note=note),
        keyboard(
            [btn(t(T.refresh, lang), Cb.share, user.id), btn(t(T.manage, lang), Cb.card, user.id)],
            app_row(t(T.my_page, lang), links.home),
        ),
        qr=links.sub,
    )


# --------------------------------------------------------------------------- the user's own screens


def home(ctx: Ctx, note: str | None = None) -> Screen:
    user = ctx.user
    assert user
    links = accounts.links(user)
    return Screen(
        account_card(user, ctx.lang, note=note),
        keyboard(
            [btn(ctx.tr(T.refresh), Cb.me), btn(ctx.tr(T.links), Cb.me_links)],
            app_row(ctx.tr(T.my_page), links.home),
        ),
        qr=links.sub,
    )


@route(Cb.me, admin=False)
def show_home(ctx: Ctx, _args: list[str]) -> None:
    ctx.show(home(ctx))
    ctx.toast(ctx.tr(T.updated))


@route(Cb.me_links, admin=False)
def show_links(ctx: Ctx, _args: list[str]) -> None:
    assert ctx.user
    ctx.show(Screen(links_text(ctx.user, ctx.lang), keyboard([btn(ctx.tr(T.back), Cb.me)]), qr=accounts.links(ctx.user).sub))
    ctx.toast()


def set_menu_button(chat_id: int, text: str, url: str | None) -> None:
    """The button next to the message box opens ``url`` as a Mini App."""
    if not can_open_as_app(url):
        return
    try:
        bot.set_chat_menu_button(chat_id, types.MenuButtonWebApp(text, types.WebAppInfo(url)))
    except Exception as e:
        logger.debug(f"tgbot: menu button not set: {e}")
