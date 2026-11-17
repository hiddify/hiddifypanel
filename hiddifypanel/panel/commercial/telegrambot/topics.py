"""Topics in the private chat (Bot API 9.3/9.4): when the bot's owner turned on topic mode in @BotFather, the
messages the bot sends by itself go into threads of their own, "Alerts" and "Support", and the main chat keeps the
account and the menus. Without topic mode nothing changes. A topic the person deleted is made again."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from loguru import logger

from hiddifypanel.cache import redis_client
from hiddifypanel.database import db
from hiddifypanel.models import BotPref

from . import bot
from .texts import T, t

_ENABLED = "tgbot:topics:enabled"
_ENABLED_TTL = 3600
#: key → (its name, its icon colour: one of Telegram's six)
TOPICS: dict[str, tuple[T, int]] = {
    "alerts": (T.topic_alerts, 16766590),  # yellow
    "support": (T.topic_support, 7322096),  # blue
}


def enabled() -> bool:
    """The bot has topic mode in private chats (getMe, checked once an hour)."""
    try:
        cached = redis_client.get(_ENABLED)
    except Exception as e:  # without redis, no topics (and no getMe on every message)
        logger.debug(f"tgbot topics: redis: {e}")
        return False
    if cached is not None:
        return cached in (b"1", "1")
    try:
        on = bool(getattr(bot.get_me(), "has_topics_enabled", False))
    except Exception as e:
        logger.debug(f"tgbot topics: getMe failed: {e}")
        return False
    redis_client.set(_ENABLED, "1" if on else "0", ex=_ENABLED_TTL)
    return on


def thread(chat_id: int, key: str, lang: str) -> int | None:
    """The topic ``key`` of this chat (made the first time), or None without topic mode."""
    if not enabled():
        return None
    pref = f"topic_{key}"
    kept = BotPref.get(chat_id, pref)
    if kept.isdigit():
        return int(kept)
    name, color = TOPICS[key]
    try:
        topic = bot.create_forum_topic(chat_id, t(name, lang), icon_color=color)
    except Exception as e:
        logger.debug(f"tgbot topics: {key} not made in {chat_id}: {e}")
        return None
    BotPref.put(chat_id, pref, str(topic.message_thread_id))
    db.session.commit()
    return int(topic.message_thread_id)


def _forget(chat_id: int, key: str) -> None:
    BotPref.put(chat_id, f"topic_{key}", "")
    db.session.commit()


def deliver(chat_id: int, key: str, lang: str, send: Callable[[dict[str, Any]], Any]) -> Any:
    """``send(extra)`` with the topic's thread in ``extra`` when there is one. A topic the person deleted is
    forgotten and the message goes again, into a new one."""
    tid = thread(chat_id, key, lang)
    if tid is None:
        return send({})
    try:
        return send({"message_thread_id": tid})
    except Exception as e:
        if "thread" not in str(e).lower() and "topic" not in str(e).lower():
            raise
        logger.info(f"tgbot topics: {key} of {chat_id} is gone: {e}")
        _forget(chat_id, key)
        tid = thread(chat_id, key, lang)
        return send({"message_thread_id": tid} if tid else {})
