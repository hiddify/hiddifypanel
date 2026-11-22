"""Telegram updates in: ``/start`` links a chat to an admin or a user, typed text answers prompts (or searches),
and every button goes through one dispatcher that checks who may press it."""

from __future__ import annotations

import re

from loguru import logger
from telebot import types
from telebot.apihelper import ApiTelegramException

from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, User

from hiddifypanel import free_test

from . import accounts, admin, admin_settings, admins, bulk, cfgfile, miniapp, openbutton, ops, resellers, bandwidth, bot, broadcast, chart, chats, doctor, free, groups, guide, menukey, nav, servers, settings, status, support, user, usernames, widget  # noqa: F401  (they register their routes)
from .texts import T, t
from .ui import BRAND, ROUTES, Cb, Ctx, Screen, btn, keyboard, lang_of

_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)


def context(chat_id: int, message_id: int | None = None, call_id: str | None = None, telegram_lang: str | None = None) -> Ctx:
    """The admin linked to this chat, else the user, else a stranger. ``telegram_lang`` is the person's Telegram
    language (their ``language_code``): spoken when no language was chosen for them."""
    from .resellers import admin_in_scope, user_in_scope

    found_admin = AdminUser.query.filter(AdminUser.telegram_id == chat_id, AdminUser.deleted.is_(False)).first()
    if found_admin and admin_in_scope(found_admin):
        return Ctx(chat_id, lang_of(found_admin, admin=True, telegram=telegram_lang), admin=found_admin, message_id=message_id, call_id=call_id)
    found_user = User.query.filter(User.telegram_id == chat_id, User.deleted.is_(False)).first()
    if found_user is not None and not user_in_scope(found_user):  # an agent's bot: not one of theirs
        found_user = None
    if found_user is None:
        settings.remember_telegram_lang(chat_id, telegram_lang)
        telegram_lang = settings.chat_lang(chat_id) or telegram_lang
    return Ctx(chat_id, lang_of(found_user, admin=False, telegram=telegram_lang), user=found_user, message_id=message_id, call_id=call_id)


def _tg_lang(person: types.User | None) -> str | None:
    return getattr(person, "language_code", None) if person else None


def _link_admin(chat_id: int, uuid: str) -> AdminUser | None:
    """One chat is one admin: linking here unlinks it from any other admin (the bot would otherwise keep answering
    as whichever admin it found first)."""
    from .resellers import admin_in_scope

    found = AdminUser.by_uuid(uuid)
    if found and not admin_in_scope(found):
        return None
    if found:
        AdminUser.query.filter(AdminUser.telegram_id == chat_id, AdminUser.id != found.id).update({AdminUser.telegram_id: None})
        found.telegram_id = chat_id
        db.session.commit()
    return found


def _link_user(chat_id: int, uuid: str) -> User | None:
    """One chat is one user account, the same way."""
    from .resellers import user_in_scope

    found = User.by_uuid(uuid)
    if found and not user_in_scope(found):
        return None
    if found:
        User.query.filter(User.telegram_id == chat_id, User.id != found.id).update({User.telegram_id: None})
        found.telegram_id = chat_id
        db.session.commit()
    return found


def open_home(ctx: Ctx, *, keys: bool = False) -> None:
    """A fresh panel message at the bottom of the chat, plus the Mini App button and the keyboard by the message box.
    ``keys``: send the keyboard again even if the chat had it (/start: the chat may have been cleared, and the
    keyboard went with its message)."""
    ctx.message_id = None
    menukey.ensure(ctx.chat_id, ctx.lang, person=ctx.person, force=keys, admin_mode=menukey.admin_mode(ctx.admin))
    if ctx.admin:
        user.set_menu_button(ctx.chat_id, BRAND, accounts.panel_app_url())
        ctx.show(admin.home_screen(ctx))
    elif ctx.user:
        user.set_menu_button(ctx.chat_id, BRAND, accounts.links(ctx.user).home)
        ctx.show(user.home(ctx))
    else:
        ctx.show(Screen(ctx.tr(T.welcome)))


def _open_admin_key(ctx: Ctx, kind: Cb, args: list[str]) -> None:
    """An admin's key: the screen comes at the bottom of the chat and the old panel message goes."""
    old = ctx.state.get("panel")
    target = ROUTES.get(kind)
    if kind is Cb.home or kind not in menukey.ADMIN_KINDS or target is None:
        nav.reset(ctx)
        open_home(ctx)
    else:
        nav.reset(ctx, kind, args)  # a first step: Back goes to the start
        ctx.message_id = None
        try:
            target.handler(ctx, args)
        except Exception as e:
            logger.exception(f"tgbot: admin key {kind}: {e}")
            db.session.rollback()
            bot.send_message(ctx.chat_id, f"⚠️ {ctx.tr(T.error_generic)}")
            return
    new = ctx.state.get("panel")
    if old and new and int(old) != int(new):
        _delete(ctx.chat_id, int(old))


def _open_key(ctx: Ctx, kind: Cb, args: list[str] | None = None) -> None:
    """A key of the keyboard: its screen as a new message (Menu: the menu)."""
    if ctx.admin:
        return _open_admin_key(ctx, kind, args or [])
    target = ROUTES.get(kind)
    if kind is Cb.me or kind not in menukey.PERSON_KINDS or ctx.user is None or target is None:
        nav.reset(ctx)
        return open_home(ctx)
    # A first step from the start: it takes the place of the screen shown now
    nav.reset(ctx, kind)
    ctx.on_panel()
    try:
        target.handler(ctx, [])
    except Exception as e:
        logger.exception(f"tgbot: key {kind}: {e}")
        db.session.rollback()
        bot.send_message(ctx.chat_id, f"⚠️ {ctx.tr(T.error_generic)}")


def _how_to_write(ctx: Ctx, typed: int | None = None) -> None:
    """Something typed (or sent) outside "Write a Message": it is not sent to support; one line says how to, with
    Support (the line becomes the support screen) and Back (the line and what was typed go, the screen stays)."""
    if free_test.current_conversation(ctx.chat_id, ctx.user) is None:  # no support to write to: the start screen
        return open_home(ctx)
    extra = [typed] if typed else []
    bot.send_message(ctx.chat_id, f"💡 {ctx.tr(T.sp_how_to_write)}", reply_markup=keyboard([btn(ctx.tr(T.support), Cb.support, "h", *extra), btn(ctx.tr(T.back), Cb.close, *extra)]))


def _delete(chat_id: int, message_id: int) -> None:
    try:
        bot.delete_message(chat_id, message_id)
    except ApiTelegramException:
        pass


@bot.message_handler(commands=["start", "menu"], chat_types=["private"])
def on_start(message: types.Message) -> None:
    usernames.remember(message.from_user)
    chat_id = message.chat.id
    payload = (message.text or "").partition(" ")[2].strip()
    if payload.startswith("free_"):
        # An admin's free test link: the offer, for anyone (an admin sees what its customers see).
        host, package_id = free_test.resolve_payload(payload.removeprefix("free_"))
        if host:
            return free.open_offer(context(chat_id, telegram_lang=_tg_lang(message.from_user)), host, message.from_user, package_id)
    if payload.startswith("admin_") and (match := _UUID.search(payload)):
        _link_admin(chat_id, match.group(0).lower())
    elif match := _UUID.search(payload):
        _link_user(chat_id, match.group(0).lower())
    ctx = context(chat_id, telegram_lang=_tg_lang(message.from_user))
    if payload and (ctx.admin or ctx.user):
        bot.send_message(chat_id, f"✅ {ctx.tr(T.linked)}")
    open_home(ctx, keys=True)


@bot.message_handler(commands=["language"], chat_types=["private"])
def on_language(message: types.Message) -> None:
    """The languages, as a new message at the bottom of the chat."""
    ctx = context(message.chat.id, telegram_lang=_tg_lang(message.from_user))
    ctx.show(settings.language_screen(ctx))


@bot.message_handler(content_types=["text"], chat_types=["private"])
def on_text(message: types.Message) -> None:
    usernames.remember(message.from_user)
    chat_id = message.chat.id
    text = message.text or ""
    ctx = context(chat_id, telegram_lang=_tg_lang(message.from_user))
    if (kind := menukey.action(text, admin=ctx.admin is not None)) is not None:  # a key of the keyboard by the message box
        _delete(chat_id, message.message_id)
        ctx.state.update(awaiting=None)
        return _open_key(ctx, kind, menukey.action_args(text, admin=ctx.admin is not None))
    if ctx.admin and broadcast.take(ctx, message):  # a message to all users: it stays (it is what gets copied)
        return
    if ctx.admin:
        # Keep the chat to one message: drop what was typed and update the panel.
        _delete(chat_id, message.message_id)
        ctx.message_id = ctx.state.get("panel")
        admin.on_text(ctx, text)
        return
    if match := _UUID.search(text):
        if _link_user(chat_id, match.group(0).lower()):
            ctx = context(chat_id, telegram_lang=_tg_lang(message.from_user))
            bot.send_message(chat_id, f"✅ {ctx.tr(T.linked)}")
            return open_home(ctx)
    # A message to support, only while writing one ("Write a Message"); anything else says how to write one
    if not free.on_user_text(ctx, message):
        _how_to_write(ctx, message.message_id)


@bot.callback_query_handler(func=lambda call: True)
def on_button(call: types.CallbackQuery) -> None:
    usernames.remember(call.from_user)
    message = call.message
    if message is None or not call.data:
        return
    kind_raw, *args = call.data.split(":")
    ctx = context(message.chat.id, message.message_id, call.id, telegram_lang=_tg_lang(call.from_user))
    try:
        kind = Cb(kind_raw)
    except ValueError:
        # A button from the old bot: replace that message with the current home.
        ctx.toast()
        open_home(ctx)
        return
    if kind is Cb.close:
        ctx.toast()
        _delete(message.chat.id, message.message_id)
        for extra in args[:1]:  # a message of this chat that goes with it (what was typed, under "how to write")
            if extra.isdigit():
                _delete(message.chat.id, int(extra))
        return
    target = ROUTES.get(kind)
    if target is None or (target.admin and not ctx.admin) or (not target.admin and not target.anyone and not ctx.user):
        ctx.toast(ctx.tr(T.not_allowed), alert=True)
        return
    # A message too old for Telegram to show us (48 h+), or a file: answer under it. A photo is a card: its caption
    # can change.
    if not isinstance(message, types.Message) or message.content_type not in ("text", "photo"):
        ctx.message_id = None
    else:
        ctx.on_photo = message.content_type == "photo"
    # A button while writing (a message, a name): the writing stops and the menu keyboard comes back, unless the
    # button is the next step of that same writing (picking the user to write to)
    if not (kind is Cb.broadcast and args[:1] in (["to"], ["one"], ["all"])) and menukey.restore(ctx):
        # The menu came back with a line under the screen: the screen comes again under it (the old one goes)
        ctx.message_id, ctx.on_photo = None, False
    if ctx.person:  # a person's path, for Back
        if kind is Cb.me:
            nav.reset(ctx)
        elif nav.is_screen(kind, args):
            nav.push(ctx, kind, args)
    elif ctx.admin:  # an admin's path too
        if kind is Cb.home:
            nav.reset(ctx)
        elif nav.is_admin_screen(kind, args):
            nav.push(ctx, kind, args)
    try:
        target.handler(ctx, args)
    except Exception as e:
        logger.exception(f"tgbot: {call.data}: {e}")
        db.session.rollback()
        # The details are in the log; the person gets a plain sentence in their language, never a stack message.
        ctx.toast(f"⚠️ {ctx.tr(T.error_generic)}", alert=True)
    finally:
        ctx.toast()


# Private chats only: in a group the bot stays quiet (it answered every sticker there)
@bot.message_handler(func=lambda message: True, content_types=["photo", "document", "sticker", "voice", "video", "audio", "video_note"], chat_types=["private"])
def on_other(message: types.Message) -> None:
    usernames.remember(message.from_user)
    ctx = context(message.chat.id, telegram_lang=_tg_lang(message.from_user))
    # A photo, file or voice is a message for support (or, from an admin answering someone, the answer)
    if ctx.admin:
        if broadcast.take(ctx, message):
            return
        if support.admin_media(ctx, message):
            _delete(message.chat.id, message.message_id)
            return
    elif support.relay_media(ctx, message):
        return
    else:
        return _how_to_write(ctx, message.message_id)
    bot.send_message(message.chat.id, t(T.unknown, ctx.lang), reply_markup=keyboard([btn(ctx.tr(T.menu), Cb.home if ctx.admin else Cb.me)]))


# --------------------------------------------------------------------------- agents' own bots (resellers.py)


class _Made:
    """Who made which bot (the update and the service message say it the same way)."""

    def __init__(self, user, made):
        self.user, self.bot = user, made


@bot.managed_bot_handler()
def on_managed_bot(update) -> None:
    from . import resellers

    resellers.on_managed_bot(update)


@bot.message_handler(content_types=["managed_bot_created"], chat_types=["private"])
def on_managed_bot_created(message) -> None:
    """The service message in the agent's chat (it comes even when the update above is not sent)."""
    from . import resellers

    created = getattr(message, "managed_bot_created", None)
    if created is not None and resellers.find(created.bot.id) is None:
        resellers.on_managed_bot(_Made(message.from_user, created.bot))


# --------------------------------------------------------------------------- the subscribers group (guard.py)


@bot.message_handler(commands=["guard"], chat_types=["group", "supergroup"])
def on_guard(message) -> None:
    from . import guard

    guard.connect(message)


@bot.chat_join_request_handler()
def on_join_request(request) -> None:
    from . import guard

    guard.on_join_request(request)
