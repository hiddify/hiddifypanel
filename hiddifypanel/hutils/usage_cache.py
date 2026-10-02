"""Day-by-day usage cache for the Admin V2 dashboard.

Closed days are cached until midnight; today's row is cached briefly so live
polls only re-query the changing day instead of summing the whole history.
"""

from __future__ import annotations

import datetime

from hiddifypanel.cache import cache
from hiddifypanel.database import db
from hiddifypanel.hutils.usage_stats import DailyPoint, NodeDailyPoint, stacked_series
from hiddifypanel.models.usage import DailyUsage
from hiddifypanel.panel.commercial.restapi.v2.admin.dashboard_schema import DashboardDailyPoint
from sqlalchemy import func

# Closed days barely change; keep them until the next calendar day.
CLOSED_DAY_TTL = 24 * 3600
# Today is still accumulating; a short TTL is enough for live polls.
TODAY_TTL = 30


def _admin_key(admin_ids: list[int]) -> str:
    return ",".join(str(i) for i in sorted(admin_ids))


def _query_day(admin_ids: list[int], child_id: int | None, day: datetime.date) -> tuple[int, int]:
    query = db.session.query(
        func.coalesce(func.sum(DailyUsage.usage), 0),
        func.coalesce(func.sum(DailyUsage.online), 0),
    ).filter(DailyUsage.admin_id.in_(admin_ids), DailyUsage.date == day)
    if child_id is not None:
        query = query.filter(DailyUsage.child_id == child_id)
    row = query.first()
    return (int(row[0] or 0), int(row[1] or 0)) if row else (0, 0)


def _query_day_by_child(admin_ids: list[int], day: datetime.date) -> list[tuple[int, int, int]]:
    rows = (
        db.session.query(
            DailyUsage.child_id,
            func.coalesce(func.sum(DailyUsage.usage), 0),
            func.coalesce(func.sum(DailyUsage.online), 0),
        )
        .filter(DailyUsage.admin_id.in_(admin_ids), DailyUsage.date == day)
        .group_by(DailyUsage.child_id)
        .all()
    )
    return [(int(row[0] or 0), int(row[1] or 0), int(row[2] or 0)) for row in rows]


@cache.cache(ttl=CLOSED_DAY_TTL)
def _closed_day(admin_key: str, child_id: int | None, day_iso: str) -> tuple[int, int]:
    admin_ids = [int(part) for part in admin_key.split(",") if part]
    return _query_day(admin_ids, child_id, datetime.date.fromisoformat(day_iso))


@cache.cache(ttl=TODAY_TTL)
def _today_day(admin_key: str, child_id: int | None, day_iso: str) -> tuple[int, int]:
    admin_ids = [int(part) for part in admin_key.split(",") if part]
    return _query_day(admin_ids, child_id, datetime.date.fromisoformat(day_iso))


@cache.cache(ttl=CLOSED_DAY_TTL)
def _closed_day_by_child(admin_key: str, day_iso: str) -> list[tuple[int, int, int]]:
    admin_ids = [int(part) for part in admin_key.split(",") if part]
    return _query_day_by_child(admin_ids, datetime.date.fromisoformat(day_iso))


@cache.cache(ttl=TODAY_TTL)
def _today_day_by_child(admin_key: str, day_iso: str) -> list[tuple[int, int, int]]:
    admin_ids = [int(part) for part in admin_key.split(",") if part]
    return _query_day_by_child(admin_ids, datetime.date.fromisoformat(day_iso))


@cache.cache(ttl=CLOSED_DAY_TTL)
def _closed_lifetime(admin_key: str, child_id: int | None, before_iso: str) -> int:
    admin_ids = [int(part) for part in admin_key.split(",") if part]
    before = datetime.date.fromisoformat(before_iso)
    query = db.session.query(func.coalesce(func.sum(DailyUsage.usage), 0)).filter(DailyUsage.admin_id.in_(admin_ids), DailyUsage.date < before)
    if child_id is not None:
        query = query.filter(DailyUsage.child_id == child_id)
    return int(query.scalar() or 0)


def load_points(admin_ids: list[int], child_id: int | None, today: datetime.date, days: int) -> list[DailyPoint]:
    """History of `days` ending today. Closed days come from cache; today is fresh."""
    admin_key = _admin_key(admin_ids)
    points: list[DailyPoint] = []
    for offset in range(days):
        day = today - datetime.timedelta(days=days - 1 - offset)
        loader = _today_day if day == today else _closed_day
        usage, online = loader(admin_key, child_id, day.isoformat())
        points.append(DailyPoint(day=day, usage=usage, online=online))
    return points


def load_node_points(admin_ids: list[int], today: datetime.date, days: int) -> list[NodeDailyPoint]:
    admin_key = _admin_key(admin_ids)
    points: list[NodeDailyPoint] = []
    for offset in range(days):
        day = today - datetime.timedelta(days=days - 1 - offset)
        loader = _today_day_by_child if day == today else _closed_day_by_child
        for child_id, usage, online in loader(admin_key, day.isoformat()):
            points.append(NodeDailyPoint(day=day, child_id=child_id, usage=usage, online=online))
    return points


def lifetime_usage(admin_ids: list[int], child_id: int | None, today: datetime.date, today_usage: int) -> int:
    """All-time total = cached closed days (before today) + today's bytes."""
    closed = _closed_lifetime(_admin_key(admin_ids), child_id, today.isoformat())
    return closed + today_usage


def stacked_history(
    admin_ids: list[int],
    today: datetime.date,
    days: int,
    child_ids: list[int],
    mirrors: dict[int, int] | None = None,
) -> list[DashboardDailyPoint]:
    """`mirrors` maps a fake child id to a real one whose points it copies (debug nodes)."""
    points = load_node_points(admin_ids, today, days)
    for fake_id, source_id in (mirrors or {}).items():
        points += [NodeDailyPoint(day=point.day, child_id=fake_id, usage=point.usage, online=point.online) for point in points if point.child_id == source_id]
    return stacked_series(points, today, days, child_ids)
