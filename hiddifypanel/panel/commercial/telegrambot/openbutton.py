"""The bot's "Open" button (Telegram's Main Mini App, by the bot's name in the chat list and on its profile).

Telegram has no API to set it: only @BotFather does. A panel started on a new server (a new bot) has none, and the
owner had to find the steps deep in Settings. Now the bot asks Telegram (getMe's has_main_web_app) and, while it is
missing, the owner's home screen says so, with a screen of the steps and the exact link to give @BotFather.
"""

from __future__ import annotations

from loguru import logger

from hiddifypanel.cache import redis_client
from hiddifypanel.models import AdminMode

from . import bot
from .texts import T
from .ui import RULE, Cb, Ctx, Screen, Style, btn, copy_btn, h, keyboard, route

_KEY = "tgbot:main_app:{}"
#: Known to be set: asked again after a day; missing: after a few minutes (the owner is likely setting it up)
_SET_TTL = 24 * 3600
_MISSING_TTL = 300


def has_open_button(*, fresh: bool = False) -> bool | None:
    """Whether the bot has its "Open" button; None when Telegram could not be asked."""
    key = _KEY.format(bot.username or "bot")
    if not fresh:
        cached = redis_client.get(key)
        if cached in (b"1", b"0", "1", "0"):
            return cached in (b"1", "1")
    try:
        found = bool(getattr(bot.get_me(), "has_main_web_app", False))
    except Exception as e:
        logger.debug(f"tgbot: getMe failed: {e}")
        return None
    redis_client.set(key, "1" if found else "0", ex=_SET_TTL if found else _MISSING_TTL)
    return found


def _owner_here(ctx: Ctx) -> bool:
    from hiddifypanel.panel.commercial.restapi.v1.tgbot import managed_bot

    return ctx.admin is not None and ctx.admin.mode == AdminMode.super_admin and managed_bot.get() is None


def home_notice(ctx: Ctx) -> tuple[list[str], list[list]]:
    """The owner's home screen: a line and a key while the button is missing."""
    from .accounts import panel_app_url

    if not _owner_here(ctx) or not panel_app_url() or has_open_button() is not False:
        return [], []
    return ["", f"⚠️ <i>{ctx.tr(T.oa_missing)}</i>"], [[btn(ctx.tr(T.oa_setup), Cb.open_help, style=Style.primary)]]


def settings_line(ctx: Ctx) -> list[str]:
    from .accounts import panel_app_url

    if not _owner_here(ctx) or not panel_app_url():
        return []
    state = has_open_button()
    mark = {True: f"✅ {ctx.tr(T.oa_ok)}", False: f"⚠️ {ctx.tr(T.oa_missing)}", None: "—"}[state]
    return ["", f"🚀 <b>{ctx.tr(T.as_main_app)}</b>: {mark}"]


def help_screen(ctx: Ctx, note: str | None = None) -> Screen:
    from .accounts import panel_app_url

    url = panel_app_url() or ""
    state = has_open_button()
    lines = [f"🚀 <b>{ctx.tr(T.as_main_app)}</b>", RULE]
    if state:
        lines.append(f"✅ {ctx.tr(T.oa_ok)}")
    else:
        lines += [ctx.tr(T.oa_steps, bot=f"@{h(bot.username)}" if bot.username else ""), "", f"<code>{h(url)}</code>"]
    if note:
        lines += ["", f"<i>{h(note)}</i>"]
    rows = []
    if not state:
        rows.append([copy_btn(ctx.tr(T.oa_copy), url), btn(ctx.tr(T.oa_check), Cb.open_help, "check")])
    rows.append([btn(ctx.tr(T.back), Cb.back)])
    return Screen("\n".join(lines), keyboard(*rows))


@route(Cb.open_help, admin=True)
def show_help(ctx: Ctx, args: list[str]) -> None:
    """oh → the steps · oh:check → ask Telegram again."""
    if not _owner_here(ctx):
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    note = None
    if args[:1] == ["check"]:
        found = has_open_button(fresh=True)
        note = ctx.tr(T.oa_ok) if found else ctx.tr(T.oa_still_missing)
    ctx.toast(note)
    ctx.show(help_screen(ctx, None if note == ctx.tr(T.oa_ok) else note))
