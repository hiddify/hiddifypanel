"""Telegram usernames (@name) of the people who use the bot: a bot cannot look one up in Telegram, so it keeps
those it has seen (and the ones its conversations hold), to find a chat by @username."""

from __future__ import annotations

from loguru import logger
from telebot import types

from hiddifypanel.cache import redis_client
from hiddifypanel.database import db

PREF = "tg_user"
_SEEN = "tgbot:un:{}"


def remember(person: types.User | None) -> None:
    """Keep this person's @username (when it changes; checked in redis first, so no write on every update)."""
    name = (getattr(person, "username", None) or "").lower()
    if not person or not name:
        return
    try:
        key = _SEEN.format(person.id)
        if (redis_client.get(key) or b"").decode() == name:
            return
        from hiddifypanel.models import BotPref

        BotPref.put(person.id, PREF, name)
        db.session.commit()
        redis_client.set(key, name, ex=24 * 3600)
    except Exception as e:
        db.session.rollback()
        logger.debug(f"tgbot: username of {getattr(person, 'id', '?')} not kept: {e}")


def normal(text: str) -> str:
    return text.strip().lstrip("@").lower()


def chats_of(username: str) -> list[int]:
    """The chats known by this @username: seen by the bot, or in a conversation."""
    from hiddifypanel.models import BotPref
    from hiddifypanel.models.message import Conversation

    name = normal(username)
    if not name:
        return []
    chats = {int(r.chat_id) for r in BotPref.query.filter(BotPref.key == PREF, BotPref.value == name).all()}
    chats |= {int(c.telegram_id) for c in Conversation.query.filter(Conversation.username.isnot(None)).all() if normal(c.username or "") == name}
    return sorted(chats)
