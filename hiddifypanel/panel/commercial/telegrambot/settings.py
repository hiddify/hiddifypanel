"""The person's own settings in the bot: the language it speaks (kept on their account, or for someone the bot does
not know yet, by their chat), and the bot's command list in every language."""

from __future__ import annotations

from loguru import logger
from telebot import types

from hiddifypanel.cache import redis_client
from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, Lang, User

from . import bot
from .texts import LANGUAGES, T, supported, t
from .ui import SELECTED, btn, Cb, Ctx, keyboard, lang_of, off_btn, route, Screen, Style

_CHAT_LANG = "tgbot:lang:{}"
_CHAT_LANG_TTL = 180 * 24 * 3600
_SEEN_LANG = "tgbot:tglang:{}"


def chat_lang(chat_id: int) -> str | None:
    """The language someone the bot does not know yet chose in it."""
    code = _decode(redis_client.get(_CHAT_LANG.format(chat_id)))
    return code if code in LANGUAGES else None


def _decode(raw: bytes | str | None) -> str | None:
    return raw.decode() if isinstance(raw, bytes) else raw


def remember_telegram_lang(chat_id: int, code: str | None) -> None:
    """The Telegram language of someone the bot does not know yet, for the messages sent to them later, outside
    an update (the admin's answer, a declined request)."""
    lang = supported(code)
    if lang and _decode(redis_client.get(_SEEN_LANG.format(chat_id))) != lang:
        redis_client.set(_SEEN_LANG.format(chat_id), lang, ex=_CHAT_LANG_TTL)


def person_lang(chat_id: int, account: AdminUser | User | None = None) -> str:
    """The language to write to this chat in, without an update at hand: the account's, else the one chosen in the
    bot, else their Telegram language, else the panel default."""
    if account is not None and getattr(account, "lang", None):
        return lang_of(account, admin=isinstance(account, AdminUser))
    return lang_of(None, admin=False, telegram=chat_lang(chat_id) or _decode(redis_client.get(_SEEN_LANG.format(chat_id))))


def language_screen(ctx: Ctx) -> Screen:
    """Every language in its own name, two to a row; the one spoken now is blue."""
    buttons = [off_btn(SELECTED + name, otherwise=btn(SELECTED + name, Cb.lang, code)) if code == ctx.lang else btn(name, Cb.lang, code) for code, name in LANGUAGES.items()]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    back = Cb.back if (ctx.admin or ctx.user) else None
    if back:
        rows.append([btn(ctx.tr(T.back), back)])
    return Screen(f"🌐 <b>{ctx.tr(T.language_title)}</b>", keyboard(*rows))


@route(Cb.lang, admin=False, anyone=True)
def choose_language(ctx: Ctx, args: list[str]) -> None:
    code = args[0] if args else ""
    if code not in LANGUAGES:
        ctx.show(language_screen(ctx))
        return ctx.toast()
    account = ctx.admin or ctx.user
    if account is not None:
        account.lang = Lang[code]
        db.session.commit()
    else:
        redis_client.set(_CHAT_LANG.format(ctx.chat_id), code, ex=_CHAT_LANG_TTL)
    ctx.lang = code
    ctx.toast(ctx.tr(T.language_set))
    # Home again, in the new language (a fresh message: the user's home is a photo card, this screen a text)
    from .handlers import _delete, open_home

    if ctx.message_id:
        _delete(ctx.chat_id, ctx.message_id)
    open_home(ctx)


def settings_screen(ctx: Ctx) -> Screen:
    """A user's settings: the language the bot speaks and the usage alerts."""
    from .notify import ALERTS_PREF, alerts_on

    on = alerts_on(ctx.chat_id)
    lines = [
        f"⚙️ <b>{ctx.tr(T.settings_title)}</b>",
        "",
        f"🌐 {ctx.tr(T.language_title)}: <b>{LANGUAGES.get(ctx.lang, ctx.lang)}</b>",
        f"🔔 {ctx.tr(T.alerts)}: <b>{ctx.tr(T.on if on else T.off)}</b>",
        f"<i>{ctx.tr(T.alerts_hint)}</i>",
    ]
    toggle = btn(ctx.tr(T.alerts_turn_off if on else T.alerts_turn_on), Cb.pref, ALERTS_PREF, 0 if on else 1, "s", style=None if on else Style.success)
    return Screen("\n".join(lines), keyboard([btn(ctx.tr(T.language), Cb.lang)], [toggle], [btn(ctx.tr(T.back), Cb.back)]))


@route(Cb.settings, admin=False)
def show_settings(ctx: Ctx, _args: list[str]) -> None:
    ctx.show(settings_screen(ctx))
    ctx.toast()


@route(Cb.pref, admin=False, anyone=True)
def set_pref(ctx: Ctx, args: list[str]) -> None:
    """One setting from a button (in the settings screen, or under an alert)."""
    from hiddifypanel.models import BotPref

    from .notify import ALERTS_PREF

    key, value, where = (args + ["", "", ""])[:3]
    if key != ALERTS_PREF or value not in ("0", "1"):
        return ctx.toast()
    BotPref.put(ctx.chat_id, key, value)
    db.session.commit()
    ctx.toast(ctx.tr(T.alerts_now_on if value == "1" else T.alerts_now_off), alert=value == "0")
    if where == "s" and ctx.user:  # pressed in the settings screen: show the new state there
        ctx.show(settings_screen(ctx))


def set_commands() -> None:
    """The command list Telegram shows (the "/" menu: start, menu, language) for admins and users alike, in every language the bot speaks; English for the rest."""
    for code in (None, *LANGUAGES):
        lang = code or "en"
        commands = [types.BotCommand("start", t(T.cmd_start, lang)), types.BotCommand("menu", t(T.cmd_menu, lang)), types.BotCommand("language", t(T.cmd_language, lang))]
        try:
            bot.set_my_commands(commands, language_code=code)
        except Exception as e:
            logger.debug(f"tgbot: commands for {code} not set: {e}")
        # In groups only /me, answered for the asker's eyes only (an ephemeral message)
        try:
            bot.set_my_commands([types.BotCommand("me", t(T.cmd_me, lang), is_ephemeral=True)], scope=types.BotCommandScopeAllGroupChats(), language_code=code)
        except Exception as e:
            logger.debug(f"tgbot: group commands for {code} not set: {e}")
