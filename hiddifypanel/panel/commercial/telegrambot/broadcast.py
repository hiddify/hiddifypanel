"""A message from the admin (the Send Message key): to all their users who have the bot, or to one of them found by
name. Written like any message (text, photo, video, file, voice), shown back with who will get it, sent only after
"Send"."""

from __future__ import annotations

import time

from loguru import logger
from telebot import types

from hiddifypanel.models import AdminUser, User

from . import bot, menukey
from .texts import T
from .ui import Cb, Ctx, Screen, Style, background, btn, h, keyboard, route, with_retry

AWAITING = "broadcast"
#: Waiting for the name of the one user to write to
AWAITING_USER = "bc_user"
#: Telegram takes about 30 messages a second from a bot: a little under it
_PAUSE_S = 0.05


def targets(admin: AdminUser) -> list[int]:
    """The Telegram chats of the admin's users (and of the admins under them), each once."""
    rows = admin.recursive_users_query().filter(User.telegram_id.isnot(None), User.telegram_id != 0).with_entities(User.telegram_id).all()
    return sorted({int(r[0]) for r in rows if r[0]})


def choose_screen(ctx: Ctx) -> Screen:
    return Screen(
        f"✉️ <b>{ctx.tr(T.bc_menu_title)}</b>\n\n{ctx.tr(T.bc_menu_pick)}",
        keyboard([btn(ctx.tr(T.bc_to_all), Cb.broadcast, "all")], [btn(ctx.tr(T.bc_to_one), Cb.broadcast, "one")], [btn(ctx.tr(T.back), Cb.back)]),
    )


@route(Cb.broadcast, admin=True)
def show_broadcast(ctx: Ctx, args: list[str]) -> None:
    admin = ctx.admin
    assert admin
    if not args:
        ctx.state.update(awaiting=None, bc_message=None, bc_target=None, bc_chat=None)
        ctx.show(choose_screen(ctx))
        return ctx.toast()
    if args[:1] == ["go"]:
        return _send(ctx)
    if args[:1] == ["one"]:
        return _ask_user(ctx)
    if args[:1] == ["to"]:
        return _pick_user(ctx, int(args[1]) if len(args) > 1 and args[1].isdigit() else 0)
    if args[:1] == ["x"]:
        ctx.state.update(awaiting=None, bc_message=None, bc_target=None, bc_chat=None)
        ctx.toast(ctx.tr(T.sp_cancelled))
        return menukey.tell(ctx, f"✖️ {ctx.tr(T.sp_cancelled)}")
    # "all": everybody
    ctx.state.update(bc_target=None, bc_chat=None)
    n = len(targets(admin))
    ctx.toast()
    text = f"📣 <b>{ctx.tr(T.bc_title)}</b>\n\n{ctx.tr(T.bc_count, n=n)}"
    if not n:
        return ctx.show(Screen(f"{text}\n\n<i>{ctx.tr(T.bc_nobody)}</i>", keyboard([btn(ctx.tr(T.back), Cb.back)])))
    ctx.state.update(awaiting=AWAITING, bc_message=None)
    ctx.show(Screen(f"{text}\n\n✍️ {ctx.tr(T.bc_write)}", keyboard([btn(ctx.tr(T.back), Cb.back)])))
    menukey.prompt(ctx, f"👇 {ctx.tr(T.bc_write_hint)}", ctx.tr(T.bc_placeholder))


def _ask_user(ctx: Ctx, note: str = "") -> None:
    """Which user: their name, typed (a part of it is enough)."""
    ctx.state.update(awaiting=AWAITING_USER, bc_target=None, bc_chat=None, bc_message=None)
    ctx.toast()
    text = f"👤 <b>{ctx.tr(T.bc_one_title)}</b>\n\n{ctx.tr(T.bc_one_ask)}"
    if note:
        text += f"\n\n⚠️ <i>{note}</i>"
    ctx.show(Screen(text, keyboard([btn(ctx.tr(T.back), Cb.broadcast)])))
    if not note:
        menukey.prompt(ctx, f"👇 {ctx.tr(T.bc_one_hint)}", ctx.tr(T.bc_one_placeholder))


def _visible(ctx: Ctx, user_id: int) -> User | None:
    from . import accounts

    assert ctx.admin
    return accounts.get_visible(ctx.admin, user_id) if user_id else None


def _pick_user(ctx: Ctx, user_id: int) -> None:
    """The user to write to is known: ask for the message."""
    user = _visible(ctx, user_id)
    if user is None or not user.telegram_id:
        return _ask_user(ctx, ctx.tr(T.bc_one_no_bot, name=h(user.name)) if user is not None else ctx.tr(T.gone))
    ctx.state.update(awaiting=AWAITING, bc_target=user.id, bc_chat=None, bc_message=None)
    ctx.toast()
    ctx.show(Screen(f"👤 <b>{h(user.name)}</b>\n\n✍️ {ctx.tr(T.bc_one_write, name=h(user.name))}", keyboard([btn(ctx.tr(T.back), Cb.broadcast, "one")])))
    menukey.prompt(ctx, f"👇 {ctx.tr(T.bc_write_hint)}", ctx.tr(T.bc_placeholder))


def _chat_target(ctx: Ctx, chats: list[int]) -> bool:
    """Telegram chats (by ID or @username): one of the admin's users, else someone who wrote to this admin. True when
    one was taken."""
    from hiddifypanel.models.message import Conversation

    assert ctx.admin
    for chat in chats:
        user = ctx.admin.recursive_users_query().filter(User.telegram_id == chat).first()
        if user is not None:
            _pick_user(ctx, user.id)
            return True
    for chat in chats:
        conv = Conversation.query.filter(Conversation.admin_id == ctx.admin.id, Conversation.telegram_id == chat).first()
        if conv is not None:
            _pick_chat(ctx, chat, conv.name or (f"@{conv.username}" if conv.username else str(chat)))
            return True
    return False


def _pick_chat(ctx: Ctx, chat: int, label: str) -> None:
    """Someone without an account here who wrote to this admin: the message goes to their chat."""
    ctx.state.update(awaiting=AWAITING, bc_target=None, bc_chat=[int(chat), label[:60]], bc_message=None)
    ctx.toast()
    ctx.show(Screen(f"👤 <b>{h(label)}</b>\n\n✍️ {ctx.tr(T.bc_one_write, name=h(label))}", keyboard([btn(ctx.tr(T.back), Cb.broadcast, "one")])))
    menukey.prompt(ctx, f"👇 {ctx.tr(T.bc_write_hint)}", ctx.tr(T.bc_placeholder))


def _find_user(ctx: Ctx, text: str) -> None:
    """What was typed: a Telegram @username, a Telegram ID, or (a part of) the name in the panel. One match is the
    user; several are offered as buttons; none asks again."""
    from . import accounts, usernames

    assert ctx.admin
    typed = text.strip()[:100]
    if typed.startswith("@"):
        if not _chat_target(ctx, usernames.chats_of(typed)):
            _ask_user(ctx, ctx.tr(T.bc_one_no_username, q=h(typed[:40])))
        return
    if typed.isdigit() and _chat_target(ctx, [int(typed)]):
        return
    found = accounts.search_page(ctx.admin, typed, 0, 8)
    if not found.total and _chat_target(ctx, usernames.chats_of(typed)):  # a username typed without @
        return
    exact = [u for u in found.users if (u.name or "").strip().casefold() == text.strip().casefold()]
    if len(exact) == 1 or found.total == 1:
        return _pick_user(ctx, (exact or found.users)[0].id)
    if not found.total:
        return _ask_user(ctx, ctx.tr(T.bc_one_none, q=h(text.strip()[:40])))
    ctx.state.update(awaiting=AWAITING_USER)
    rows = [[btn(f"{'✉️' if u.telegram_id else '⚪️'} {u.name}"[:60], Cb.broadcast, "to", u.id)] for u in found.users]
    ctx.show(Screen(f"👤 <b>{ctx.tr(T.bc_one_title)}</b>\n\n{ctx.tr(T.bc_one_many, n=found.total)}", keyboard(*rows, [btn(ctx.tr(T.back), Cb.broadcast)])))


def _target(ctx: Ctx) -> User | None:
    target = ctx.state.get("bc_target")
    return _visible(ctx, int(target)) if target else None


def _chats(ctx: Ctx) -> list[int]:
    """Who gets the message: the one user, or everybody."""
    assert ctx.admin
    if ctx.state.get("bc_target"):
        user = _target(ctx)
        return [int(user.telegram_id)] if user is not None and user.telegram_id else []
    if chat := ctx.state.get("bc_chat"):
        return [int(chat[0])]
    return targets(ctx.admin)


def writing(ctx: Ctx) -> bool:
    return ctx.state.get("awaiting") in (AWAITING, AWAITING_USER)


def take(ctx: Ctx, message: types.Message) -> bool:
    """The admin's message while writing one to everybody: kept (it stays in their chat, as the preview) and the
    question to send it. Cancel drops it. False when the admin is not writing one."""
    awaiting = ctx.state.get("awaiting")
    if awaiting not in (AWAITING, AWAITING_USER):
        return False
    ctx.state.update(awaiting=None)
    if (message.text or "").strip() == ctx.tr(T.sp_cancel):
        ctx.state.update(bc_target=None)
        menukey.tell(ctx, f"✖️ {ctx.tr(T.sp_cancelled)}")
        return True
    if awaiting == AWAITING_USER:  # the user's name
        try:
            bot.delete_message(ctx.chat_id, message.message_id)
        except Exception:
            pass
        if not (message.text or "").strip():
            _ask_user(ctx, ctx.tr(T.bc_one_ask))
        else:
            _find_user(ctx, message.text)
        return True
    assert ctx.admin
    one = _target(ctx) if ctx.state.get("bc_target") else None
    one_name = one.name if one is not None else (ctx.state.get("bc_chat") or [None, None])[1]
    n = len(_chats(ctx))
    ctx.state.update(bc_message=message.message_id)
    menukey.tell(ctx, f"👆 {ctx.tr(T.bc_preview)}")
    ctx.message_id = None
    if one_name:
        title, send = ctx.tr(T.bc_confirm_one, name=h(one_name)), ctx.tr(T.bc_send_one, name=one_name[:30])
    else:
        title, send = ctx.tr(T.bc_confirm, n=n), ctx.tr(T.bc_send, n=n)
    ctx.show(
        Screen(
            f"{'👤' if one_name else '📣'} <b>{title}</b>\n<i>{ctx.tr(T.bc_confirm_hint)}</i>",
            keyboard([btn(send, Cb.broadcast, "go", style=Style.success)], [btn(ctx.tr(T.cancel), Cb.broadcast, "x")]),
        )
    )
    return True


def _send(ctx: Ctx) -> None:
    admin = ctx.admin
    assert admin
    message_id = ctx.state.get("bc_message")
    if not message_id:
        return ctx.toast(ctx.tr(T.gone), alert=True)
    chats = _chats(ctx)
    ctx.state.update(bc_message=None, bc_target=None, bc_chat=None)
    ctx.toast(ctx.tr(T.bc_sending, n=len(chats)))
    ctx.show(Screen(f"📤 {ctx.tr(T.bc_sending, n=len(chats))}"))
    chat_id, panel = ctx.chat_id, ctx.message_id
    tr = ctx.tr

    def run() -> None:
        sent = failed = 0
        for chat in chats:
            try:
                with_retry(lambda: bot.copy_message(chat, chat_id, int(message_id)))
                sent += 1
            except Exception as e:
                failed += 1
                logger.info(f"tgbot broadcast: not delivered to {chat}: {e}")
            time.sleep(_PAUSE_S)
        report = f"✅ <b>{tr(T.bc_done)}</b>\n{tr(T.bc_report, sent=sent, failed=failed)}"
        if failed:
            report += f"\n<i>{h(tr(T.bc_failed_hint))}</i>"
        try:
            bot.edit_message_text(report, chat_id, panel)
        except Exception:
            bot.send_message(chat_id, report)

    background(run)
