"""The keyboard that always stays by the message box (a persistent reply keyboard). For a person with an account it
holds their everyday screens (setup guide, connection check, usage chart, support, settings) and Menu; for admins and
for someone without an account, Menu only. A key is plain text: pressing it opens that screen. Set once per chat
(again when the language or the kind of chat changes); a Cancel key replaces it for a moment while writing."""

from __future__ import annotations

from functools import cache

from loguru import logger
from telebot import types

from hiddifypanel.database import db
from hiddifypanel.models import BotPref

from . import bot
from .texts import LANGUAGES, T, t
from .ui import Cb

PREF = "menu_key"
HINT_PREF = "menu_key_msg"
#: Raise it to send the keyboard again to every chat (a new look).
VERSION = "12"  # 12: the Menu key is blue
#: The line that carries the keyboard (the same in every language: Hiddify's tagline)
TAGLINE = "🎉 Hiddify, Internet Freedom Solution"

#: A person's keyboard, row by row: the key's text and the screen it opens (with its arguments). Menu is Cb.me.
PERSON_ROWS: tuple[tuple[tuple[T, Cb, tuple], ...], ...] = (
    ((T.guide, Cb.guide, ()), (T.doctor, Cb.doctor, ())),
    ((T.chart, Cb.chart, ()), (T.support, Cb.support, ())),
    ((T.hist_key, Cb.history, ()), (T.settings, Cb.settings, ())),
    ((T.menu_key, Cb.me, ()),),
)
#: An admin's keyboard: their home screen's buttons (Server Status holds the services; Settings the language and backup).
ADMIN_ROWS: tuple[tuple[tuple[T, Cb, tuple], ...], ...] = (
    ((T.btn_users, Cb.users, ("a", "0")), (T.btn_new, Cb.new, ("0", "0", "0"))),
    ((T.btn_status, Cb.status, ()), (T.btn_bandwidth, Cb.bandwidth, ())),
    ((T.btn_chats, Cb.chats, ()), (T.btn_broadcast, Cb.broadcast, ())),
    ((T.btn_free, Cb.free_link, ()), (T.btn_settings, Cb.admin_settings, ())),
    ((T.menu_key, Cb.home, ()),),
)


def admin_mode(admin) -> str | None:
    """An admin's level for their keyboard ("super_admin", "admin", "agent"), None for anyone else."""
    if admin is None:
        return None
    mode = getattr(admin, "mode", None)
    return str(getattr(mode, "value", mode) or "admin")


def _admin_rows(mode: str | None) -> list[list[tuple[T, Cb, tuple]]]:
    rows = []
    for row in ADMIN_ROWS:
        keep = [k for k in row if not (k[1] is Cb.backup and mode != "super_admin")]
        if keep:
            rows.append(keep)
    return rows


def _key(label: T, lang: str) -> types.KeyboardButton:
    """A key by the message box; Menu is blue (white text: a keyboard here draws blue well)."""
    return types.KeyboardButton(t(label, lang), style="primary" if label is T.menu_key else None)


def keyboard_for(lang: str, person: bool = False, admin_mode: str | None = None) -> types.ReplyKeyboardMarkup:
    """``person``: the full keyboard of someone with an account; ``admin_mode``: an admin's; else Menu only."""
    keys = types.ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
    rows = PERSON_ROWS if person else _admin_rows(admin_mode) if admin_mode else ()
    if rows:
        for row in rows:
            keys.row(*(_key(label, lang) for label, _kind, _args in row))
    else:
        keys.add(_key(T.menu_key, lang))
    return keys


#: Keys renamed since: their old text still opens their screen
_OLD_LABELS = {"💬 Chats": Cb.chats, "💬 گفتگوها": Cb.chats, "📣 Message All": Cb.broadcast, "📣 پیام به همه": Cb.broadcast}


@cache
def _actions(admin: bool) -> dict[str, tuple[Cb, tuple]]:
    """Every key's text in every language (a chat may keep an older keyboard) → the screen it opens, for one role: an
    admin's and a person's keys can share a text (Settings), and each must open its own screen."""
    found: dict[str, tuple[Cb, tuple]] = {}
    if admin:  # labels a key had before (a chat may still show them until its keyboard is sent again)
        found.update({text: (kind, ()) for text, kind in _OLD_LABELS.items()})
    rows = ADMIN_ROWS if admin else PERSON_ROWS
    for code in LANGUAGES:
        for row in rows:
            for label, kind, args in row:
                found.setdefault(t(label, code), (kind, args))  # the first key with a text keeps it
    return found


#: The screens each kind of chat may open from a key (a key's text alone must never open another role's screen).
PERSON_KINDS = frozenset(k for row in PERSON_ROWS for _label, k, _args in row)
ADMIN_KINDS = frozenset(k for row in ADMIN_ROWS for _label, k, _args in row)


def action(text: str, admin: bool = False) -> Cb | None:
    """The screen a key opens for this role, or None for any other text."""
    found = _actions(admin).get(text.strip())
    return found[0] if found else None


def action_args(text: str, admin: bool = False) -> list[str]:
    found = _actions(admin).get(text.strip())
    return list(found[1]) if found else []


def is_menu(text: str) -> bool:
    return action(text) is Cb.me


def ensure(chat_id: int, lang: str, person: bool = False, force: bool = False, admin_mode: str | None = None) -> None:
    """The right keyboard is in this chat, in this language. ``force``: send it even if the chat had it (a cleared
    chat loses it with its message, and the bot cannot tell). Never raises."""
    try:
        want = f"{VERSION}:{lang}:{'p' if person else 'a-' + admin_mode if admin_mode else 'm'}"
        if not force and BotPref.get(chat_id, PREF) == want:
            return
        sent = bot.send_message(chat_id, TAGLINE, reply_markup=keyboard_for(lang, person, admin_mode))
        # One such line in the chat: the one before goes (the keyboard stays with the new one)
        old = BotPref.get(chat_id, HINT_PREF)
        if old.isdigit() and int(old) != sent.message_id:
            try:
                bot.delete_message(chat_id, int(old))
            except Exception:
                pass
        _forget_cancel(chat_id)
        BotPref.put(chat_id, PREF, want)
        BotPref.put(chat_id, HINT_PREF, str(sent.message_id))
        db.session.commit()
    except Exception as e:
        # No rollback: it would undo the caller's own changes in this session too
        logger.debug(f"tgbot: menu keyboard not set in {chat_id}: {e}")


def say(chat_id: int, lang: str, text: str, person: bool = False, admin_mode: str | None = None) -> None:
    """A line in the chat that also brings the keyboard back (after a Cancel key). Never raises."""
    try:
        bot.send_message(chat_id, text, reply_markup=keyboard_for(lang, person, admin_mode))
        _forget_cancel(chat_id)
    except Exception as e:
        logger.debug(f"tgbot: line not sent to {chat_id}: {e}")


def tell(ctx, text: str) -> None:
    """``say`` in this chat, with the keyboard of whoever it is (an admin's, a person's, or Menu only)."""
    say(ctx.chat_id, ctx.lang, text, person=ctx.person, admin_mode=admin_mode(ctx.admin))


# --------------------------------------------------------------------------- the Cancel keyboard while writing

#: Set while a Cancel keyboard (writing a message, a name…) has taken the menu's place in the chat
CANCEL_FLAG = "cancel_keys"
#: The line that came with it ("write your message below…"): it goes when the writing ends
CANCEL_MSG = "cancel_msg"


def cancel_keys(ctx, placeholder: str) -> types.ReplyKeyboardMarkup:
    """Only Cancel by the message box, with a hint in it; remembered, so any other button brings the menu back."""
    ctx.state.update(**{CANCEL_FLAG: 1})
    keys = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, input_field_placeholder=placeholder[:64])
    keys.add(types.KeyboardButton(t(T.sp_cancel, ctx.lang)))
    return keys


def prompt(ctx, text: str, placeholder: str):
    """The line asking to write, with the Cancel keyboard; it is deleted when the writing ends. Returns the message."""
    before = ctx.state.get(CANCEL_MSG)
    sent = bot.send_message(ctx.chat_id, text, reply_markup=cancel_keys(ctx, placeholder))
    ctx.state.update(**{CANCEL_MSG: sent.message_id})
    if before:  # one such line at a time (the name, then the message)
        try:
            bot.delete_message(ctx.chat_id, int(before))
        except Exception:
            pass
    return sent


def restore(ctx) -> bool:
    """Another button was pressed while writing: the writing stops and the menu keyboard comes back."""
    try:
        if not ctx.state.get(CANCEL_FLAG):
            return False
        line = ctx.state.get(CANCEL_MSG)
        ctx.state.update(awaiting=None, **{CANCEL_FLAG: None, CANCEL_MSG: None})
    except Exception as e:  # the chat's state cannot be read: the button itself still works
        logger.debug(f"tgbot: writing state not read: {e}")
        return False
    if line:  # "write your message below…" is over
        try:
            bot.delete_message(ctx.chat_id, int(line))
        except Exception:
            pass
    ensure(ctx.chat_id, ctx.lang, person=ctx.person, force=True, admin_mode=admin_mode(ctx.admin))
    return True


def _forget_cancel(chat_id: int) -> None:
    """The writing is over: its line goes, and the flag."""
    try:
        from .ui import ChatState

        state = ChatState(chat_id)
        line = state.get(CANCEL_MSG)
        state.update(**{CANCEL_FLAG: None, CANCEL_MSG: None})
        if line:
            bot.delete_message(chat_id, int(line))
    except Exception:
        pass
