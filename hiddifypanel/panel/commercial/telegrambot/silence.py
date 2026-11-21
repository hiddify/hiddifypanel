"""Silent chats: an admin can have the bot's messages arrive without a sound (Telegram's ``disable_notification``).
Every request goes through ``apihelper._make_request``; a message sent to a silent chat gets the flag there, so no
sender has to know about it."""

from __future__ import annotations

import time

from loguru import logger

PREF = "silent"
_TTL = 60.0
#: chat id → (silent, when it was read): a send needs no database read each time
_cache: dict[int, tuple[bool, float]] = {}


def is_silent(chat_id: int) -> bool:
    now = time.monotonic()
    hit = _cache.get(chat_id)
    if hit and now - hit[1] < _TTL:
        return hit[0]
    try:
        from hiddifypanel.models import BotPref

        value = BotPref.get(chat_id, PREF) == "1"
    except Exception as e:  # outside the app (no database): as before, with a sound
        logger.debug(f"tgbot: silent pref not read for {chat_id}: {e}")
        return False
    _cache[chat_id] = (value, now)
    return value


def set_silent(chat_id: int, on: bool) -> None:
    """Kept in the chat's settings (committed by the caller) and known at once."""
    from hiddifypanel.models import BotPref

    BotPref.put(chat_id, PREF, "1" if on else "0")
    _cache[chat_id] = (on, time.monotonic())


def _is_send(method_name: str) -> bool:
    return method_name in ("copyMessage", "forwardMessage") or (method_name.startswith("send") and method_name not in ("sendChatAction", "sendMessageDraft"))


def install() -> None:
    from telebot import apihelper

    original = apihelper._make_request
    if getattr(original, "_hiddify_silence", False):
        return

    def quiet(token, method_name, method="get", params=None, files=None):
        if params and _is_send(method_name) and "disable_notification" not in params:
            try:
                chat = int(params.get("chat_id"))
            except (TypeError, ValueError):
                chat = 0
            if chat and is_silent(chat):
                params = {**params, "disable_notification": True}
        return original(token, method_name, method, params, files)

    quiet._hiddify_silence = True  # type: ignore[attr-defined]
    apihelper._make_request = quiet
