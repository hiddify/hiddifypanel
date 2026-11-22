"""Advanced mode, its own switch: the subscribers group. A Telegram group only the panel's active users are in (a
channel cannot be one: its posts do not say who sent them, so the owner cannot be checked).

- The owner makes the bot an admin of the group (with "add members" and "ban users"), turns on "Approve new
  members", and sends /guard there: that group is the subscribers group from then on.
- A request to join is approved when the person's Telegram account is linked to an active user (or an admin) of the
  panel, and declined otherwise (they hear how to link their account).
- Active users get a "Join the group" key in the bot (an invite link that asks to join, so it can be checked).
- Every day, the users whose package ended are taken out of the group (they can come back when they renew), and told.
"""

from __future__ import annotations

import datetime

from loguru import logger
from telebot import types

from hiddifypanel.cache import redis_client
from hiddifypanel.models import AdminUser, BotPref, ConfigEnum, User, hconfig

from . import accounts, advanced, bot
from .texts import T, t
from .ui import lang_of, url_btn, with_retry

_PANEL = 0
_CHAT = "adv_guard_chat"
_LINK = "adv_guard_link"
#: Users checked in the group each day at most (one Telegram call each)
MAX_CHECKS = 2000


def allowed() -> bool:
    return advanced.feature(advanced.SUBSCRIBERS_GROUP)


def group_id() -> int | None:
    try:
        raw = BotPref.get(_PANEL, _CHAT)
    except Exception:
        return None
    return int(raw) if raw and raw.lstrip("-").isdigit() else None


def _active_account(tg_id: int) -> bool:
    if AdminUser.query.filter(AdminUser.telegram_id == tg_id, AdminUser.deleted.is_(False), AdminUser.enable.is_(True)).first():
        return True
    user = User.query.filter(User.telegram_id == tg_id, User.deleted.is_(False)).first()
    return user is not None and accounts.status(user) is accounts.Status.active


# --------------------------------------------------------------------------- connecting the group


def connect(message: types.Message) -> None:
    """/guard in a group: only the panel's owner (their linked Telegram account) can make it the subscribers group."""
    from hiddifypanel.database import db

    if not allowed() or message.chat.type not in ("group", "supergroup"):
        return
    owner = AdminUser.get_super_admin()
    sender = message.from_user.id if message.from_user else 0
    if not owner or owner.telegram_id != sender:
        return
    lang = lang_of(owner, admin=True)
    try:
        link = bot.create_chat_invite_link(message.chat.id, name="Hiddify", creates_join_request=True).invite_link
    except Exception as e:  # not an admin with "add members": say what is missing
        logger.info(f"tgbot guard: no invite link in {message.chat.id}: {e}")
        with_retry(lambda: bot.send_message(message.chat.id, f"⚠️ {t(T.gd_need_admin, lang)}"), attempts=2)
        return
    BotPref.put(_PANEL, _CHAT, str(message.chat.id))
    BotPref.put(_PANEL, _LINK, link)
    db.session.commit()
    with_retry(lambda: bot.send_message(message.chat.id, f"✅ {t(T.gd_connected, lang)}"), attempts=2)


def join_row(lang: str, user: User | None) -> list:
    """The user's key to the group (an active user, a connected group)."""
    if not allowed() or user is None or accounts.status(user) is not accounts.Status.active:
        return []
    try:
        link = BotPref.get(_PANEL, _LINK)
    except Exception:
        return []
    return [url_btn(t(T.gd_join, lang), link)] if link and group_id() else []


# --------------------------------------------------------------------------- requests to join


def on_join_request(request: types.ChatJoinRequest) -> None:
    gid = group_id()
    if not allowed() or gid is None or request.chat.id != gid:
        return
    tg_id = request.from_user.id
    lang = request.from_user.language_code or str(hconfig(ConfigEnum.lang) or "en")
    try:
        if _active_account(tg_id):
            bot.approve_chat_join_request(gid, tg_id)
        else:
            bot.decline_chat_join_request(gid, tg_id)
            # Telegram lets the bot write to someone who asked to join, for a while (user_chat_id)
            with_retry(lambda: bot.send_message(getattr(request, "user_chat_id", None) or tg_id, f"🔒 {t(T.gd_declined, lang)}"), attempts=2)
    except Exception as e:
        logger.debug(f"tgbot guard: join request of {tg_id}: {e}")


# --------------------------------------------------------------------------- the daily check


def sweep() -> None:
    """Scheduled daily (one worker): users linked to Telegram whose package ended leave the group."""
    if not hconfig(ConfigEnum.telegram_bot_token) or not allowed():
        return
    gid = group_id()
    if gid is None or not redis_client.set(f"tgbot:guard:{datetime.date.today()}", 1, nx=True, ex=36 * 3600):
        return
    removed = 0
    linked = User.query.filter(User.deleted.is_(False), User.telegram_id.isnot(None), User.telegram_id != 0).order_by(User.id).all()
    ended = [u for u in linked if accounts.status(u) is not accounts.Status.active][:MAX_CHECKS]
    for user in ended:
        if AdminUser.query.filter(AdminUser.telegram_id == user.telegram_id, AdminUser.deleted.is_(False)).first():
            continue  # an admin who is also a user stays
        try:
            member = bot.get_chat_member(gid, user.telegram_id)
            if member.status not in ("member", "restricted"):
                continue
            bot.ban_chat_member(gid, user.telegram_id)
            bot.unban_chat_member(gid, user.telegram_id, only_if_banned=True)  # out, but free to ask again after renewing
            removed += 1
            lang = lang_of(user, admin=False)
            with_retry(lambda: bot.send_message(user.telegram_id, f"🔒 {t(T.gd_removed, lang)}"), attempts=2)
        except Exception as e:
            logger.debug(f"tgbot guard: {user.id} not checked: {e}")
    logger.info(f"tgbot guard: {removed} ended users left the subscribers group")
