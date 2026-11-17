"""Animated icons for the bot's buttons: a button whose label starts with an emoji ("👥 Users") shows that emoji's
animated custom emoji instead, from a list of custom emoji sets (the first set that has it wins).

Telegram allows button icons only when the bot's owner has Telegram Premium (or the bot has a username bought on
Fragment), so they are an option (``telegram_bot_animated_icons``) and a refusal turns them off by itself for a while:
the request is sent again with the plain emoji (``install_refusal_guard``).
"""

from __future__ import annotations

import json
import re

from loguru import logger

from hiddifypanel.cache import redis_client
from hiddifypanel.models import ConfigEnum, hconfig

#: Telegram's own animated versions of the standard emoji first (the same Apple-style faces and objects as the
#: labels), then animated icon sets for what it lacks.
DEFAULT_SETS = ("RestrictedEmoji", "PremiumIcons", "MajorEmojis", "emojipack_sm", "SparklesEmoji", "AnimatedIconsEmoji", "AdaptiveIcons", "AdaptiveLines")

#: An emoji no set animates borrows the icon of a close one (first found wins); the label keeps its own emoji, so
#: without icons nothing changes. An alias is never a label emoji itself (its icon would give the wrong one back).
ALIASES: dict[str, tuple[str, ...]] = {
    "🗑": ("❌", "🚫"),
    "⚠": ("❗", "‼", "🚨"),
    "⚙": ("🛠", "🔧", "🔩", "🎛", "⚒", "🪛", "🧰", "🔨", "⛏", "📝", "🎚"),
    "📅": ("📆", "🗓", "⏰"),
    "📦": ("💽", "📀", "🗃", "🗄", "📥", "💿", "🧳"),
    "🖥": ("⌨", "🖱", "🖲"),
    "⏸": ("⏹", "⛔"),
}

_MAP_KEY = "tgbot:icons:map:{}"
_MAP_TTL = 24 * 3600
_REFUSED_KEY = "tgbot:icons:refused"
_REFUSED_TTL = 24 * 3600

#: A label's leading emoji (with its variation selector / joiners), then a space.
_LEADING_EMOJI = re.compile(r"^((?:[\U0001F000-\U0001FAFF←-⯿⌀-⏿☀-➿⬀-⯿][️‍⃣]*)+)\s+(.*)$", re.S)


def _norm(emoji: str) -> str:
    return emoji.replace("️", "")


def sets() -> tuple[str, ...]:
    """The custom emoji sets to take icons from, in order: the panel setting (comma separated) or the defaults."""
    configured = str(hconfig(ConfigEnum.telegram_bot_icon_sets) or "").strip()
    names = tuple(n.strip() for n in configured.replace("\n", ",").split(",") if n.strip())
    return names or DEFAULT_SETS


def enabled() -> bool:
    return bool(hconfig(ConfigEnum.telegram_bot_animated_icons)) and not redis_client.get(_REFUSED_KEY)


def _load_map(names: tuple[str, ...]) -> dict[str, str]:
    """emoji → custom emoji id over ``names``, the first set that has an emoji wins (kept a day in redis)."""
    key = _MAP_KEY.format(",".join(names))
    cached = redis_client.get(key)
    if cached:
        try:
            return json.loads(cached)
        except ValueError:
            pass
    from . import bot

    found: dict[str, str] = {}
    for name in names:
        try:
            sticker_set = bot.get_sticker_set(name)
        except Exception as e:
            logger.debug(f"tgbot: icon set {name} unavailable: {e}")
            continue
        for sticker in sticker_set.stickers:
            emoji = _norm(getattr(sticker, "emoji", "") or "")
            custom_id = getattr(sticker, "custom_emoji_id", None)
            if emoji and custom_id and emoji not in found:
                found[emoji] = custom_id
    # An empty map is kept for less time: a set that failed to load is tried again soon.
    redis_client.set(key, json.dumps(found), ex=_MAP_TTL if found else 300)
    return found


def icon_map() -> dict[str, str]:
    return _load_map(sets())


def icon_for(emoji: str) -> str | None:
    """The animated icon for ``emoji`` (or for the first of its aliases a set has)."""
    found = icon_map()
    key = _norm(emoji)
    for candidate in (key, *ALIASES.get(key, ())):
        if custom_id := found.get(_norm(candidate)):
            return custom_id
    return None


def split(label: str) -> tuple[str | None, str]:
    """The animated icon for ``label``'s leading emoji and the label without it, or (None, label) when there is
    none (icons off, no leading emoji, or no set has it)."""
    if not enabled():
        return None, label
    match = _LEADING_EMOJI.match(label)
    if not match:
        return None, label
    custom_id = icon_for(match.group(1))
    if not custom_id:
        return None, label
    return custom_id, match.group(2)


def _emoji_for(custom_id: str) -> str | None:
    """The label emoji an icon stands for: an aliased one first (🗑 shown with ❌'s icon gets 🗑 back)."""
    for emoji in ALIASES:
        if icon_for(emoji) == custom_id:
            return emoji
    for emoji, cid in icon_map().items():
        if cid == custom_id:
            return emoji
    return None


def strip_icons(markup_json: str) -> str:
    """A reply_markup (JSON) without icons: each button's emoji is put back in front of its label."""
    try:
        markup = json.loads(markup_json)
    except ValueError:
        return markup_json
    for row in markup.get("inline_keyboard") or markup.get("keyboard") or []:
        for button in row:
            if isinstance(button, dict) and (custom_id := button.pop("icon_custom_emoji_id", None)):
                emoji = _emoji_for(custom_id)
                if emoji:
                    button["text"] = f"{emoji} {button.get('text', '')}"
    return json.dumps(markup, ensure_ascii=False)


def _is_icon_refusal(error: Exception) -> bool:
    text = str(getattr(error, "description", "") or error).lower()
    return getattr(error, "error_code", None) == 400 and ("emoji" in text or "icon" in text)


def _icons_dropped(result: object) -> bool:
    """A sent message (Telegram's answer) whose buttons came back without any icon."""
    if not isinstance(result, dict) or "message_id" not in result or not isinstance(result.get("chat"), dict):
        return False
    rows = (result.get("reply_markup") or {}).get("inline_keyboard")
    if not rows:
        return False
    return not any(isinstance(b, dict) and b.get("icon_custom_emoji_id") for row in rows for b in row)


def install_refusal_guard() -> None:
    """Every Telegram request goes through ``apihelper._make_request``: when Telegram refuses a button icon (the
    owner has no Premium any more…), send it again without icons, and leave icons off for a day."""
    from telebot import apihelper

    original = apihelper._make_request
    if getattr(original, "_hiddify_icon_guard", False):
        return

    def guarded(token, method_name, method="get", params=None, files=None):
        markup = (params or {}).get("reply_markup")
        with_icons = isinstance(markup, str) and "icon_custom_emoji_id" in markup
        try:
            result = original(token, method_name, method, params, files)
        except apihelper.ApiTelegramException as e:
            if not with_icons or not _is_icon_refusal(e):
                raise
            logger.warning(f"tgbot: Telegram refused the animated button icons ({e}); they stay off for a day")
            redis_client.set(_REFUSED_KEY, "1", ex=_REFUSED_TTL)
            params = {**params, "reply_markup": strip_icons(markup)}
            return original(token, method_name, method, params, files)
        # Without Premium Telegram takes the message but drops the icons silently (the buttons would lose their
        # emoji): the message it sent back tells. Put the plain emoji back on it, and leave icons off for a day.
        if with_icons and _icons_dropped(result):
            logger.warning("tgbot: Telegram dropped the animated button icons (the bot's owner has no Premium?); they stay off for a day")
            redis_client.set(_REFUSED_KEY, "1", ex=_REFUSED_TTL)
            try:
                original(token, "editMessageReplyMarkup", "post", {"chat_id": result["chat"]["id"], "message_id": result["message_id"], "reply_markup": strip_icons(markup)}, None)
            except Exception as e:
                logger.debug(f"tgbot: plain emoji not put back: {e}")
        return result

    guarded._hiddify_icon_guard = True  # type: ignore[attr-defined]
    apihelper._make_request = guarded
