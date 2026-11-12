"""The free test in the bot (see ``hiddifypanel.free_test``): the offer someone sees after opening an admin's link, the
request and the account they get, their messages to the admin, and the admin's side: requests to approve or decline,
replies, and its own link."""

from __future__ import annotations

from loguru import logger
from telebot import types

from hiddifypanel import free_test
from hiddifypanel.cache import redis_client
from hiddifypanel.database import db
from hiddifypanel.free_test import FreeTestError
from hiddifypanel.models import AdminUser, User
from hiddifypanel.models.message import Conversation, FreeStatus, Sender

from . import bot
from . import user as user_screens
from .texts import T, t
from .ui import RULE, Cb, Ctx, Screen, btn, fmt_data, h, keyboard, lang_of, route, send_card

#: Messages a chat may send to an admin per minute.
RATE_PER_MINUTE = 10


def _person(tg_user: types.User | None) -> tuple[str, str | None]:
    if tg_user is None:
        return "", None
    return " ".join(p for p in (tg_user.first_name, tg_user.last_name) if p).strip(), tg_user.username


def _who(conv: Conversation) -> str:
    return f"<b>{h(conv.name)}</b>" + (f" (@{h(conv.username)})" if conv.username else "")


def _package_lines(package: free_test.Package, lang: str) -> str:
    return f"<blockquote>⏳ {t(T.free_days, lang, n=package.days)}\n📦 {t(T.free_data, lang, amount=fmt_data(package.usage_gb, lang))}</blockquote>"


# --------------------------------------------------------------------------- the person asking


def offer_screen(conv: Conversation, lang: str) -> Screen:
    """The package and the one thing to do next, by where this chat's free test stands."""
    admin = AdminUser.by_id(conv.admin_id)
    package = free_test.package_of(admin, conv.free_package_id) if admin else None
    write = btn(t(T.free_write, lang), Cb.free_write, conv.id)
    if admin is None or package is None or not package.enabled:
        return Screen(f"🎁 <b>{t(T.free_title, lang)}</b>\n\n{t(T.free_off, lang)}", keyboard([write]))

    head = [
        f"🎁 <b>{t(T.free_title, lang)}</b>  ·  🏷 <b>{t(T.free_tag, lang)}</b>",
        "",
        _package_lines(package, lang),
        "",
    ]
    if conv.free_status == FreeStatus.pending:
        return Screen("\n".join([*head, f"⏳ <b>{t(T.free_pending, lang)}</b>", t(T.free_wait, lang)]), keyboard([btn(t(T.refresh, lang), Cb.free, conv.id)], [write]))
    if not free_test.can_ask(conv):
        return Screen("\n".join([*head, f"✖️ {t(T.free_declined, lang)}"]), keyboard([write]))
    if not free_test.is_first_time(conv):
        rows = [[btn(t(T.free_again, lang), Cb.free_ask, conv.id)], [write]]
        if free_test.has_account(conv.telegram_id):
            rows.insert(0, [btn(t(T.account_title, lang), Cb.me)])
        return Screen("\n".join([*head, f"<i>{t(T.free_hint_used, lang)}</i>"]), keyboard(*rows))
    if package.approval == "auto":
        return Screen("\n".join([*head, f"<i>{t(T.free_hint_auto, lang)}</i>"]), keyboard([btn(t(T.free_get, lang), Cb.free_ask, conv.id)], [write]))
    return Screen("\n".join([*head, f"<i>{t(T.free_hint_manual, lang)}</i>"]), keyboard([btn(t(T.free_request, lang), Cb.free_ask, conv.id)], [write]))


def open_offer(ctx: Ctx, admin: AdminUser, tg_user: types.User | None, package_id: str | None = None) -> None:
    """``/start free_<code>``: this chat now talks to ``admin``, and sees its offer: the default package, or the
    private one its link names (``package_id``)."""
    name, username = _person(tg_user)
    conv = free_test.conversation(admin, ctx.chat_id, name=name, username=username)
    if conv.free_status != FreeStatus.pending:  # a request waiting keeps the package it asked for
        conv.free_package_id = package_id
    db.session.commit()
    ctx.message_id = None
    ctx.show(offer_screen(conv, ctx.lang))


def _own(ctx: Ctx, args: list[str]) -> Conversation | None:
    """The conversation a button names, only for the chat it belongs to."""
    conv = db.session.get(Conversation, int(args[0])) if args and args[0].isdigit() else None
    return conv if conv is not None and conv.telegram_id == ctx.chat_id else None


@route(Cb.free, admin=False, anyone=True)
def show_offer(ctx: Ctx, args: list[str]) -> None:
    if conv := _own(ctx, args):
        ctx.show(offer_screen(conv, ctx.lang))
    ctx.toast()


@route(Cb.free_write, admin=False, anyone=True)
def show_write_hint(ctx: Ctx, args: list[str]) -> None:
    ctx.toast(ctx.tr(T.free_write_hint), alert=True)


@route(Cb.free_ask, admin=False, anyone=True)
def ask(ctx: Ctx, args: list[str]) -> None:
    conv = _own(ctx, args)
    if conv is None:
        return ctx.toast(ctx.tr(T.gone), alert=True)
    try:
        account = free_test.ask(conv)
    except FreeTestError:
        ctx.toast(ctx.tr(T.free_off if free_test.can_ask(conv) else T.free_pending), alert=True)
        ctx.show(offer_screen(conv, ctx.lang))
        return
    if account is None:
        ctx.toast(ctx.tr(T.free_pending))
        ctx.show(offer_screen(conv, ctx.lang))
        notify_request(conv)
        return
    ctx.toast(ctx.tr(T.free_ready))
    ctx.show(Screen(f"🎉 <b>{ctx.tr(T.free_ready)}</b>"))
    send_account(conv, account)
    notify_request(conv, given=True)


def send_account(conv: Conversation, account: User) -> None:
    """The new account's card (QR code, links) in the chat, and its page on the menu button."""
    lang = lang_of(account, admin=False)
    screen = user_screens.home(Ctx(conv.telegram_id, lang, user=account), note=t(T.free_ready, lang))
    try:
        send_card(conv.telegram_id, screen)
        from . import accounts

        user_screens.set_menu_button(conv.telegram_id, t(T.my_page, lang), accounts.links(account).home)
    except Exception as e:
        logger.warning(f"tgbot: free test account not sent to {conv.telegram_id}: {e}")


def tell_declined(conv: Conversation) -> None:
    lang = lang_of(None, admin=False)
    try:
        bot.send_message(conv.telegram_id, f"✖️ {t(T.free_declined, lang)}", reply_markup=keyboard([btn(t(T.free_write, lang), Cb.free_write, conv.id)]))
    except Exception as e:
        logger.debug(f"tgbot: decline not sent to {conv.telegram_id}: {e}")


def on_user_text(ctx: Ctx, message: types.Message) -> bool:
    """Text from someone who is not an admin goes to the admin they talk to. False when they talk to nobody yet."""
    conv = free_test.current_conversation(ctx.chat_id, ctx.user)
    if conv is None:
        return False
    key = f"tgbot:msg-rate:{ctx.chat_id}"
    sent = redis_client.incr(key)
    if sent == 1:
        redis_client.expire(key, 60)
    if sent > RATE_PER_MINUTE:
        db.session.rollback()
        bot.send_message(ctx.chat_id, f"⏳ {ctx.tr(T.msg_slow)}")
        return True
    name, username = _person(message.from_user)
    if name:
        conv.name = name[:128]
    if username:
        conv.username = username[:64]
    text = (message.text or "").strip()
    free_test.add_message(conv, Sender.user, text)
    db.session.commit()
    notify_message(conv, text)
    _acknowledge(ctx, message)
    return True


def _acknowledge(ctx: Ctx, message: types.Message) -> None:
    """A quiet 👍 on the message; a line of text where reactions are not available."""
    try:
        bot.set_message_reaction(ctx.chat_id, message.message_id, [types.ReactionTypeEmoji("👍")])
    except Exception:
        try:
            bot.send_message(ctx.chat_id, f"✉️ {ctx.tr(T.msg_sent)}")
        except Exception as e:
            logger.debug(f"tgbot: no acknowledgement to {ctx.chat_id}: {e}")


# --------------------------------------------------------------------------- the admin


def _notify(conv: Conversation, build) -> None:
    """One message to the conversation's admin, when it is on Telegram (the inbox has it either way)."""
    admin = AdminUser.by_id(conv.admin_id)
    if admin is None or not admin.telegram_id:
        return
    lang = lang_of(admin, admin=True)
    try:
        text, markup = build(admin, lang)
        bot.send_message(admin.telegram_id, text, reply_markup=markup)
    except Exception as e:
        logger.debug(f"tgbot: admin {admin.id} not notified: {e}")


def _reply_row(conv: Conversation, lang: str) -> list[types.InlineKeyboardButton]:
    return [btn(t(T.reply, lang), Cb.reply, conv.id)]


def notify_request(conv: Conversation, *, given: bool = False) -> None:
    """A request to approve or decline; ``given``: it was given at once (automatic approval), for the record."""

    def build(admin: AdminUser, lang: str):
        package = free_test.package_of(admin, conv.free_package_id)
        lines = [f"🎁 <b>{t(T.req_auto if given else T.req_title, lang)}</b>", f"👤 {_who(conv)}", _package_lines(package, lang)]
        if given:
            return "\n".join(lines), keyboard(_reply_row(conv, lang))
        if not free_test.is_first_time(conv):
            lines.append(f"<i>{t(T.free_hint_used, lang)}</i>")
        if not admin.can_have_more_users():
            lines.append(f"⚠️ {t(T.req_no_room, lang)}")
        buttons = [btn(t(T.req_approve, lang), Cb.free_answer, conv.id, "a"), btn(t(T.req_decline, lang), Cb.free_answer, conv.id, "d")]
        return "\n".join(lines), keyboard(buttons, _reply_row(conv, lang))

    _notify(conv, build)


def notify_message(conv: Conversation, text: str) -> None:
    _notify(conv, lambda _admin, lang: (f"💬 {t(T.msg_new, lang, name=_who(conv))}\n\n{h(text)}", keyboard(_reply_row(conv, lang))))


def _mine(ctx: Ctx, args: list[str]) -> Conversation | None:
    conv = db.session.get(Conversation, int(args[0])) if args and args[0].isdigit() else None
    return conv if conv is not None and ctx.admin is not None and conv.admin_id == ctx.admin.id else None


@route(Cb.free_answer, admin=True)
def answer(ctx: Ctx, args: list[str]) -> None:
    conv = _mine(ctx, args)
    if conv is None:
        return ctx.toast(ctx.tr(T.gone), alert=True)
    if conv.free_status != FreeStatus.pending:
        ctx.toast(ctx.tr(T.req_done), alert=True)
        return _settle(ctx, conv, f"☑️ {ctx.tr(T.req_done)}\n👤 {_who(conv)}")
    if len(args) > 1 and args[1] == "a":
        try:
            account = free_test.grant(conv)
        except FreeTestError as e:
            return ctx.toast(ctx.tr(T.read_only_node if e.code == "read_only" else T.req_no_room), alert=True)
        send_account(conv, account)
        text = f"✅ {ctx.tr(T.req_approved, name=_who(conv))}"
    else:
        free_test.decline(conv)
        tell_declined(conv)
        text = f"✖️ {ctx.tr(T.req_declined, name=_who(conv))}"
    ctx.toast(ctx.tr(T.done))
    _settle(ctx, conv, text)


def _settle(ctx: Ctx, conv: Conversation, text: str) -> None:
    """The request's message becomes its outcome (it is not the admin's panel message: that one stays)."""
    markup = keyboard(_reply_row(conv, ctx.lang))
    try:
        if ctx.message_id:
            bot.edit_message_text(text, ctx.chat_id, ctx.message_id, reply_markup=markup)
            return
    except Exception as e:
        logger.debug(f"tgbot: cannot edit {ctx.message_id}: {e}")
    bot.send_message(ctx.chat_id, text, reply_markup=markup)


@route(Cb.reply, admin=True)
def ask_reply(ctx: Ctx, args: list[str]) -> None:
    conv = _mine(ctx, args)
    if conv is None:
        return ctx.toast(ctx.tr(T.gone), alert=True)
    ctx.state.update(awaiting="reply", reply_to=conv.id)
    ctx.toast(ctx.tr(T.reply_prompt, name=conv.name), alert=True)


def deliver(conv: Conversation, text: str) -> None:
    """The admin's message to the chat (from the inbox or from Telegram), kept in the conversation. Raises when Telegram
    refuses it (the person blocked the bot). Commits."""
    lang = lang_of(None, admin=False)
    # The person is never shown who the admin is: the answer comes from "support".
    bot.send_message(conv.telegram_id, f"💬 <b>{t(T.msg_from, lang)}</b>\n\n{h(text)}")
    free_test.add_message(conv, Sender.admin, text)
    conv.unread = 0
    db.session.commit()


def admin_reply(ctx: Ctx, text: str) -> None:
    """The text an admin typed after pressing "reply"."""
    admin = ctx.admin
    conv = db.session.get(Conversation, int(ctx.state.get("reply_to") or 0))
    ctx.state.update(reply_to=None)
    menu = keyboard([btn(ctx.tr(T.menu), Cb.home)])
    if admin is None or conv is None or conv.admin_id != admin.id:
        return ctx.show(Screen(f"⚠️ {ctx.tr(T.gone)}", menu))
    try:
        deliver(conv, text.strip()[: free_test.MAX_TEXT])
    except Exception as e:
        db.session.rollback()
        return ctx.show(Screen(f"⚠️ {ctx.tr(T.reply_failed, name=h(conv.name))}\n<code>{h(e)}</code>", menu))
    ctx.show(Screen(f"✅ {ctx.tr(T.reply_sent, name=h(conv.name))}", menu))


def link_of(admin: AdminUser) -> str | None:
    return f"https://t.me/{bot.username}?start={free_test.start_payload(admin)}" if bot.username else None


@route(Cb.free_link, admin=True)
def show_link(ctx: Ctx, _args: list[str]) -> None:
    admin = ctx.admin
    assert admin
    package = free_test.package_of(admin)
    lines = [f"🎁 <b>{ctx.tr(T.free_link_title)}</b>  ·  🏷 <b>{ctx.tr(T.free_tag)}</b>", RULE]
    if not package.enabled:
        lines.append(f"⚪️ {ctx.tr(T.free_link_off)}")
    else:
        lines += [_package_lines(package, ctx.lang), ctx.tr(T.free_link_auto if package.approval == "auto" else T.free_link_manual)]
        if package.owner is not None and package.owner.id != admin.id:
            lines.append(ctx.tr(T.free_link_inherited, name=h(package.owner.name)))
        if link := link_of(admin):
            lines += ["", f"🔗 <code>{h(link)}</code>", f"<i>{ctx.tr(T.free_link_share)}</i>"]
    waiting = free_test.counts(admin)["pending"]
    if waiting:
        lines += ["", f"📨 {ctx.tr(T.free_link_waiting, n=waiting)}"]
    ctx.show(Screen("\n".join(lines), keyboard([btn(ctx.tr(T.menu), Cb.home)])))
    ctx.toast()
