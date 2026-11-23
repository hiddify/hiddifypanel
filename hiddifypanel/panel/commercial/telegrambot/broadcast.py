"""A message from the admin (the Send Message key): to their users or to the admins under them (all of them, or one
found by name, Telegram ID or @username). Written like any message (text, photo, video, file, voice), shown back with
who will get it, sent only after "Send"."""

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
#: Waiting for the name of the one admin to write to
AWAITING_ADMIN = "bc_admin"
_RESET = dict(awaiting=None, bc_message=None, bc_target=None, bc_chat=None, bc_admin=None, bc_aud=None)
#: Telegram takes about 30 messages a second from a bot: a little under it
_PAUSE_S = 0.05


def targets(admin: AdminUser) -> list[int]:
    """The Telegram chats of the admin's users (and of the admins under them), each once."""
    rows = admin.recursive_users_query().filter(User.telegram_id.isnot(None), User.telegram_id != 0).with_entities(User.telegram_id).all()
    return sorted({int(r[0]) for r in rows if r[0]})


def admin_targets(admin: AdminUser) -> list[int]:
    """The Telegram chats of the admins under ``admin`` (not ``admin`` itself), each once."""
    return sorted({int(a.telegram_id) for a in _admins_under(admin) if a.telegram_id})


def _admins_under(admin: AdminUser) -> list[AdminUser]:
    ids = set(admin.recursive_sub_admins_ids()) - {admin.id}
    return AdminUser.query.filter(AdminUser.id.in_(ids), AdminUser.deleted.is_(False)).order_by(AdminUser.name).all() if ids else []


def audience_screen(ctx: Ctx) -> Screen:
    """Who it is for: the users, or the admins."""
    return Screen(
        f"✉️ <b>{ctx.tr(T.bc_menu_title)}</b>\n\n{ctx.tr(T.bc_menu_pick)}",
        keyboard([btn(ctx.tr(T.bc_to_users), Cb.broadcast, "u")], [btn(ctx.tr(T.bc_to_admins), Cb.broadcast, "a")], [btn(ctx.tr(T.back), Cb.back)]),
    )


def admins_screen(ctx: Ctx) -> Screen:
    return Screen(
        f"🧑‍💼 <b>{ctx.tr(T.bc_admins_menu)}</b>\n\n{ctx.tr(T.bc_menu_pick)}",
        keyboard([btn(ctx.tr(T.bc_to_all_admins), Cb.broadcast, "aall")], [btn(ctx.tr(T.bc_to_one_admin), Cb.broadcast, "aone")], [btn(ctx.tr(T.back), Cb.back)]),
    )


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
        ctx.state.update(**_RESET)
        ctx.show(audience_screen(ctx))
        return ctx.toast()
    if args[:1] == ["u"]:
        ctx.state.update(**_RESET)
        ctx.show(choose_screen(ctx))
        return ctx.toast()
    if args[:1] == ["a"]:
        ctx.state.update(**_RESET)
        ctx.show(admins_screen(ctx))
        return ctx.toast()
    if args[:1] == ["aone"]:
        return _ask_admin(ctx)
    if args[:1] == ["ato"]:
        return _pick_admin(ctx, int(args[1]) if len(args) > 1 and args[1].isdigit() else 0)
    if args[:1] == ["aall"]:
        return _all_admins(ctx)
    if args[:1] == ["go"]:
        return _send(ctx)
    if args[:1] == ["one"]:
        return _ask_user(ctx)
    if args[:1] == ["to"]:
        return _pick_user(ctx, int(args[1]) if len(args) > 1 and args[1].isdigit() else 0)
    if args[:1] == ["x"]:
        ctx.state.update(**_RESET)
        ctx.toast(ctx.tr(T.sp_cancelled))
        return menukey.tell(ctx, f"✖️ {ctx.tr(T.sp_cancelled)}")
    # "all": everybody
    ctx.state.update(bc_target=None, bc_chat=None, bc_admin=None, bc_aud=None)
    n = len(targets(admin))
    ctx.toast()
    text = f"📣 <b>{ctx.tr(T.bc_title)}</b>\n\n{ctx.tr(T.bc_count, n=n)}"
    if not n:
        return ctx.show(Screen(f"{text}\n\n<i>{ctx.tr(T.bc_nobody)}</i>", keyboard([btn(ctx.tr(T.back), Cb.back)])))
    ctx.state.update(awaiting=AWAITING, bc_message=None)
    ctx.show(Screen(f"{text}\n\n✍️ {ctx.tr(T.bc_write)}", keyboard([btn(ctx.tr(T.back), Cb.back)])))
    menukey.prompt(ctx, f"👇 {ctx.tr(T.bc_write_hint)}", ctx.tr(T.bc_placeholder))


def _all_admins(ctx: Ctx) -> None:
    """All the admins under this one: how many have the bot, then the message."""
    assert ctx.admin
    ctx.state.update(bc_target=None, bc_chat=None, bc_admin=None, bc_aud="a")
    n = len(admin_targets(ctx.admin))
    ctx.toast()
    text = f"📣 <b>{ctx.tr(T.bc_admins_title)}</b>\n\n{ctx.tr(T.bc_admins_count, n=n)}"
    if not n:
        return ctx.show(Screen(f"{text}\n\n<i>{ctx.tr(T.bc_admins_nobody)}</i>", keyboard([btn(ctx.tr(T.back), Cb.back)])))
    ctx.state.update(awaiting=AWAITING, bc_message=None)
    ctx.show(Screen(f"{text}\n\n✍️ {ctx.tr(T.bc_write)}", keyboard([btn(ctx.tr(T.back), Cb.back)])))
    menukey.prompt(ctx, f"👇 {ctx.tr(T.bc_write_hint)}", ctx.tr(T.bc_placeholder_admins))


def _ask_admin(ctx: Ctx, note: str = "") -> None:
    """Which admin: their name (a part is enough), Telegram ID or @username."""
    ctx.state.update(awaiting=AWAITING_ADMIN, bc_target=None, bc_chat=None, bc_admin=None, bc_aud=None, bc_message=None)
    ctx.toast()
    text = f"👤 <b>{ctx.tr(T.bc_one_admin_title)}</b>\n\n{ctx.tr(T.bc_one_admin_ask)}"
    if note:
        text += f"\n\n⚠️ <i>{note}</i>"
    ctx.show(Screen(text, keyboard([btn(ctx.tr(T.back), Cb.broadcast, "a")])))
    if not note:
        menukey.prompt(ctx, f"👇 {ctx.tr(T.bc_one_hint)}", ctx.tr(T.bc_one_placeholder))


def _visible_admin(ctx: Ctx, admin_id: int) -> AdminUser | None:
    assert ctx.admin
    return next((a for a in _admins_under(ctx.admin) if a.id == admin_id), None) if admin_id else None


def _pick_admin(ctx: Ctx, admin_id: int) -> None:
    """The admin to write to is known: ask for the message."""
    target = _visible_admin(ctx, admin_id)
    if target is None or not target.telegram_id:
        return _ask_admin(ctx, ctx.tr(T.bc_one_no_bot, name=h(target.name)) if target is not None else ctx.tr(T.gone))
    ctx.state.update(awaiting=AWAITING, bc_admin=target.id, bc_target=None, bc_chat=None, bc_aud=None, bc_message=None)
    ctx.toast()
    ctx.show(Screen(f"🧑‍💼 <b>{h(target.name)}</b>\n\n✍️ {ctx.tr(T.bc_one_write, name=h(target.name))}", keyboard([btn(ctx.tr(T.back), Cb.broadcast, "aone")])))
    menukey.prompt(ctx, f"👇 {ctx.tr(T.bc_write_hint)}", ctx.tr(T.bc_placeholder_admins))


def _find_admin(ctx: Ctx, text: str) -> None:
    """What was typed: an @username, a Telegram ID or (a part of) the admin's name. One match is the admin; several
    are offered as buttons; none asks again."""
    from . import usernames

    assert ctx.admin
    typed = text.strip()[:100]
    people = _admins_under(ctx.admin)
    chats: list[int] = []
    if typed.startswith("@"):
        chats = usernames.chats_of(typed)
    elif typed.isdigit():
        chats = [int(typed)]
    if chats:
        found = [a for a in people if a.telegram_id and int(a.telegram_id) in chats]
    else:
        q = typed.casefold()
        exact = [a for a in people if (a.name or "").strip().casefold() == q]
        found = exact or [a for a in people if q and q in (a.name or "").casefold()]
        if not found:
            found = [a for a in people if a.telegram_id and int(a.telegram_id) in usernames.chats_of(typed)]
    if len(found) == 1:
        return _pick_admin(ctx, found[0].id)
    if not found:
        return _ask_admin(ctx, ctx.tr(T.bc_one_admin_none, q=h(typed[:40])))
    ctx.state.update(awaiting=AWAITING_ADMIN)
    rows = [[btn(f"{'✉️' if a.telegram_id else '⚪️'} {a.name}"[:60], Cb.broadcast, "ato", a.id)] for a in found[:8]]
    ctx.show(Screen(f"👤 <b>{ctx.tr(T.bc_one_admin_title)}</b>\n\n{ctx.tr(T.bc_one_admin_many, n=len(found))}", keyboard(*rows, [btn(ctx.tr(T.back), Cb.broadcast, "a")])))


def _ask_user(ctx: Ctx, note: str = "") -> None:
    """Which user: their name, typed (a part of it is enough)."""
    ctx.state.update(awaiting=AWAITING_USER, bc_target=None, bc_chat=None, bc_admin=None, bc_aud=None, bc_message=None)
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
    ctx.state.update(awaiting=AWAITING, bc_target=user.id, bc_chat=None, bc_admin=None, bc_aud=None, bc_message=None)
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
    ctx.state.update(awaiting=AWAITING, bc_target=None, bc_chat=[int(chat), label[:60]], bc_admin=None, bc_aud=None, bc_message=None)
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
    """Who gets the message: the one admin, all admins, the one user, or all users."""
    assert ctx.admin
    if admin_id := ctx.state.get("bc_admin"):
        target = _visible_admin(ctx, int(admin_id))
        return [int(target.telegram_id)] if target is not None and target.telegram_id else []
    if ctx.state.get("bc_aud") == "a":
        return admin_targets(ctx.admin)
    if ctx.state.get("bc_target"):
        user = _target(ctx)
        return [int(user.telegram_id)] if user is not None and user.telegram_id else []
    if chat := ctx.state.get("bc_chat"):
        return [int(chat[0])]
    return targets(ctx.admin)


def writing(ctx: Ctx) -> bool:
    return ctx.state.get("awaiting") in (AWAITING, AWAITING_USER, AWAITING_ADMIN)


def take(ctx: Ctx, message: types.Message) -> bool:
    """The admin's message while writing one to everybody: kept (it stays in their chat, as the preview) and the
    question to send it. Cancel drops it. False when the admin is not writing one."""
    awaiting = ctx.state.get("awaiting")
    if awaiting not in (AWAITING, AWAITING_USER, AWAITING_ADMIN):
        return False
    ctx.state.update(awaiting=None)
    if (message.text or "").strip() == ctx.tr(T.sp_cancel):
        ctx.state.update(bc_target=None, bc_admin=None, bc_aud=None)
        menukey.tell(ctx, f"✖️ {ctx.tr(T.sp_cancelled)}")
        return True
    if awaiting == AWAITING_ADMIN:  # the admin's name
        try:
            bot.delete_message(ctx.chat_id, message.message_id)
        except Exception:
            pass
        if not (message.text or "").strip():
            _ask_admin(ctx, ctx.tr(T.bc_one_admin_ask))
        else:
            _find_admin(ctx, message.text)
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
    one_admin = _visible_admin(ctx, int(ctx.state.get("bc_admin"))) if ctx.state.get("bc_admin") else None
    one_name = one.name if one is not None else (one_admin.name if one_admin is not None else (ctx.state.get("bc_chat") or [None, None])[1])
    to_admins = ctx.state.get("bc_aud") == "a"
    n = len(_chats(ctx))
    ctx.state.update(bc_message=message.message_id)
    menukey.tell(ctx, f"👆 {ctx.tr(T.bc_preview)}")
    ctx.message_id = None
    if one_name:
        title, send = ctx.tr(T.bc_confirm_one, name=h(one_name)), ctx.tr(T.bc_send_one, name=one_name[:30])
    elif to_admins:
        title, send = ctx.tr(T.bc_confirm_admins, n=n), ctx.tr(T.bc_send_admins, n=n)
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
    sending = ctx.tr(T.bc_sending_admins if ctx.state.get("bc_aud") == "a" else T.bc_sending, n=len(chats))
    ctx.state.update(bc_message=None, bc_target=None, bc_chat=None, bc_admin=None, bc_aud=None)
    ctx.toast(sending)
    ctx.show(Screen(f"📤 {sending}"))
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
