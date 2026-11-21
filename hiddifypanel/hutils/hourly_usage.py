"""The traffic of every hour, by the admin who owns the users, kept a few days in redis: the Telegram bot's
"last 24 hours" chart (the database keeps days only)."""

from __future__ import annotations

import datetime

from loguru import logger

KEEP_S = 3 * 24 * 3600
_KEY = "usage:hourly:{:%Y%m%d%H}"


def _hour(when: datetime.datetime) -> datetime.datetime:
    return when.replace(minute=0, second=0, microsecond=0)


def record(by_admin: dict[int | None, int], when: datetime.datetime | None = None) -> None:
    """Add bytes used (by admin id) to the hour of ``when``. Never raises: the usage itself is already saved."""
    used = {int(a or 0): int(n) for a, n in by_admin.items() if n and n > 0}
    if not used:
        return
    try:
        from hiddifypanel.cache import redis_client

        key = _KEY.format(_hour(when or datetime.datetime.now()))
        pipe = redis_client.pipeline()
        for admin_id, n in used.items():
            pipe.hincrby(key, str(admin_id), n)
        pipe.expire(key, KEEP_S)
        pipe.execute()
    except Exception as e:
        logger.debug(f"usage: hourly usage not kept: {e}")


def last_hours(admin_ids: list[int], hours: int = 24, now: datetime.datetime | None = None) -> list[tuple[datetime.datetime, int]]:
    """(hour, bytes) of the users of ``admin_ids`` for each of the last ``hours`` hours (the current one last), oldest
    first; 0 for an hour without traffic or not kept."""
    from hiddifypanel.cache import redis_client

    end = _hour(now or datetime.datetime.now())
    slots = [end - datetime.timedelta(hours=hours - 1 - i) for i in range(hours)]
    fields = [str(a) for a in admin_ids]
    pipe = redis_client.pipeline()
    for slot in slots:
        pipe.hmget(_KEY.format(slot), fields)
    out = []
    for slot, values in zip(slots, pipe.execute()):
        out.append((slot, sum(int(v) for v in values or [] if v)))
    return out
