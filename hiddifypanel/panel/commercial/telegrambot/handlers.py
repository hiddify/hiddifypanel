"""Telegram updates in: ``/start`` links a chat to an admin or a user, typed text answers prompts (or searches),
and every button goes through one dispatcher that checks who may press it."""

from __future__ import annotations

import re

from loguru import logger
from telebot import types
from telebot.apihelper import ApiTelegramException

from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, User

from . import accounts, admin, bot, status, user  # noqa: F401  (status registers its routes)
from .texts import T, t
from .ui import ROUTES, Cb, Ctx, Screen, btn, keyboard, lang_of

_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)


def context(chat_id: int, message_id: int | None = None, call_id: str | None = None) -> Ctx:
    """The admin linked to this chat, else the user, else a stranger."""
    if found_admin := AdminUser.query.filter(AdminUser.telegram_id == chat_id, AdminUser.deleted.is_(False)).first():
        return Ctx(chat_id, lang_of(found_admin, admin=True), admin=found_admin, message_id=message_id, call_id=call_id)
    found_user = User.query.filter(User.telegram_id == chat_id, User.deleted.is_(False)).first()
    return Ctx(chat_id, lang_of(found_user, admin=False), user=found_user, message_id=message_id, call_id=call_id)


def _link_admin(chat_id: int, uuid: str) -> AdminUser | None:
    found = AdminUser.by_uuid(uuid)
    if found:
        found.telegram_id = chat_id
        db.session.commit()
    return found


def _link_user(chat_id: int, uuid: str) -> User | None:
    found = User.by_uuid(uuid)
    if found:
        found.telegram_id = chat_id
        db.session.commit()
    return found


def _open_home(ctx: Ctx) -> None:
    """A fresh panel message at the bottom of the chat, plus the Mini App button by the message box."""
    ctx.message_id = None
    if ctx.admin:
        user.set_menu_button(ctx.chat_id, ctx.tr(T.panel), accounts.panel_app_url())
        ctx.show(admin.home_screen(ctx))
    elif ctx.user:
        user.set_menu_button(ctx.chat_id, ctx.tr(T.my_page), accounts.links(ctx.user).home)
        ctx.show(user.home(ctx))
    else:
        ctx.show(Screen(ctx.tr(T.welcome)))


def _delete(chat_id: int, message_id: int) -> None:
    try:
        bot.delete_message(chat_id, message_id)
    except ApiTelegramException:
        pass


@bot.message_handler(commands=["start", "menu"], chat_types=["private"])
def on_start(message: types.Message) -> None:
    chat_id = message.chat.id
    payload = (message.text or "").partition(" ")[2].strip()
    if payload.startswith("admin_") and (match := _UUID.search(payload)):
        _link_admin(chat_id, match.group(0).lower())
    elif match := _UUID.search(payload):
        _link_user(chat_id, match.group(0).lower())
    ctx = context(chat_id)
    if payload and (ctx.admin or ctx.user):
        bot.send_message(chat_id, f"✅ {ctx.tr(T.linked)}")
    _open_home(ctx)


@bot.message_handler(content_types=["text"], chat_types=["private"])
def on_text(message: types.Message) -> None:
    chat_id = message.chat.id
    text = message.text or ""
    ctx = context(chat_id)
    if ctx.admin:
        # Keep the chat to one message: drop what was typed and update the panel.
        _delete(chat_id, message.message_id)
        ctx.message_id = ctx.state.get("panel")
        admin.on_text(ctx, text)
        return
    if match := _UUID.search(text):
        if _link_user(chat_id, match.group(0).lower()):
            ctx = context(chat_id)
            bot.send_message(chat_id, f"✅ {ctx.tr(T.linked)}")
    _open_home(ctx)


@bot.callback_query_handler(func=lambda call: True)
def on_button(call: types.CallbackQuery) -> None:
    message = call.message
    if message is None or not call.data:
        return
    kind_raw, *args = call.data.split(":")
    ctx = context(message.chat.id, message.message_id, call.id)
    try:
        kind = Cb(kind_raw)
    except ValueError:
        # A button from the old bot: replace that message with the current home.
        ctx.toast()
        _open_home(ctx)
        return
    if kind is Cb.close:
        ctx.toast()
        _delete(message.chat.id, message.message_id)
        return
    target = ROUTES.get(kind)
    if target is None or (target.admin and not ctx.admin) or (not target.admin and not ctx.user):
        ctx.toast(ctx.tr(T.not_allowed), alert=True)
        return
    # A message too old for Telegram to show us (48 h+), or a file: answer under it. A photo is a card: its caption
    # can change.
    if not isinstance(message, types.Message) or message.content_type not in ("text", "photo"):
        ctx.message_id = None
    else:
        ctx.on_photo = message.content_type == "photo"
    try:
        target.handler(ctx, args)
    except Exception as e:
        logger.exception(f"tgbot: {call.data}: {e}")
        db.session.rollback()
        ctx.toast(f"⚠️ {e}"[:200], alert=True)
    finally:
        ctx.toast()


@bot.message_handler(func=lambda message: True, content_types=["photo", "document", "sticker", "voice", "video", "audio"])
def on_other(message: types.Message) -> None:
    ctx = context(message.chat.id)
    bot.send_message(message.chat.id, t(T.unknown, ctx.lang), reply_markup=keyboard([btn(ctx.tr(T.menu), Cb.home if ctx.admin else Cb.me)]))
