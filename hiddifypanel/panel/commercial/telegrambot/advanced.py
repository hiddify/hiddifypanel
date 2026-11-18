"""Advanced mode: the bot as it is ("ideal 2") unless the panel's owner turns Advanced on in the bot's Settings; then
the newer features join (smart dates, greyed-out buttons, and what comes next). Two of them have their own switch
inside Advanced, off by default: reseller bots (a bot of their own for each agent) and the subscribers group.

Panel-wide, kept in bot_pref under chat 0 (no chat has that id), read through a short cache so a screen does not
ask the database for every button."""

from __future__ import annotations

import time

from loguru import logger

ADVANCED = "advanced"
RESELLER_BOTS = "adv_resellers"
SUBSCRIBERS_GROUP = "adv_guard"
#: What the owner can switch (the first is Advanced itself)
SWITCHES = (ADVANCED, RESELLER_BOTS, SUBSCRIBERS_GROUP)

_PANEL = 0
_TTL = 30.0
_cache: dict[str, tuple[bool, float]] = {}


def _read(key: str) -> bool:
    now = time.monotonic()
    hit = _cache.get(key)
    if hit and now - hit[1] < _TTL:
        return hit[0]
    try:
        from hiddifypanel.models import BotPref

        value = BotPref.get(_PANEL, key) == "1"
    except Exception as e:  # no database (a test, a script): the bot as it is
        logger.debug(f"tgbot: advanced switch {key} not read: {e}")
        return False
    _cache[key] = (value, now)
    return value


def is_on() -> bool:
    """Advanced mode."""
    return _read(ADVANCED)


def feature(key: str) -> bool:
    """A feature with its own switch inside Advanced: on only when Advanced is on too."""
    return is_on() and _read(key)


def set_switch(key: str, on: bool) -> None:
    """Kept (committed by the caller) and known at once in this process (others within the cache's 30 seconds)."""
    from hiddifypanel.models import BotPref

    if key not in SWITCHES:
        raise ValueError(key)
    BotPref.put(_PANEL, key, "1" if on else "0")
    _cache[key] = (on, time.monotonic())
