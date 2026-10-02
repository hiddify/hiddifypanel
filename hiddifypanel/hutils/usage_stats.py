"""Pure aggregation helpers for daily usage/online history.

Kept free of database and Flask imports so the dashboard math (period totals,
averages, trends) can be unit tested with plain data.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from hiddifypanel.panel.commercial.restapi.v2.admin.dashboard_schema import (
    ChildUsagePoint,
    DashboardDailyPoint,
    UsageAverages,
    UsagePeak,
    UsagePrevious,
    UsageSummary,
    UsageTotals,
    UsageTrends,
)

WEEK_DAYS = 7
MONTH_DAYS = 30


@dataclass(frozen=True)
class DailyPoint:
    """One aggregated day of traffic and distinct online users."""

    day: datetime.date
    usage: int = 0
    online: int = 0


@dataclass(frozen=True)
class NodeDailyPoint:
    """One day of traffic for a single node (child)."""

    day: datetime.date
    child_id: int
    usage: int = 0
    online: int = 0


def _trend_percent(current: float, previous: float) -> float | None:
    """Growth of `current` over `previous` in percent, or None when unknown."""
    if not previous:
        return None
    return round((current - previous) * 100 / previous, 1)


def _window_sum(by_day: dict[datetime.date, DailyPoint], end: datetime.date, days: int) -> int:
    start = end - datetime.timedelta(days=days - 1)
    return sum(point.usage for day, point in by_day.items() if start <= day <= end)


def fill_series(
    points: list[DailyPoint],
    today: datetime.date,
    days: int,
) -> list[DailyPoint]:
    """Contiguous day-by-day series ending today, zero-filled where data is missing."""
    by_day = {point.day: point for point in points}
    start = today - datetime.timedelta(days=days - 1)
    return [
        by_day.get(start + datetime.timedelta(days=offset), DailyPoint(day=start + datetime.timedelta(days=offset)))
        for offset in range(days)
    ]


def build_usage_summary(
    points: list[DailyPoint],
    today: datetime.date,
    series_days: int = MONTH_DAYS,
    total_usage: int | None = None,
) -> UsageSummary:
    """Period totals, averages and trends for the usage charts.

    `points` may cover more days than `series_days`; the extra history is used
    for the previous-period comparisons. `total_usage` is the all-time total
    (which the series cannot know) and defaults to the sum of `points`.
    """
    by_day = {point.day: point for point in points}
    yesterday = today - datetime.timedelta(days=1)

    today_usage = by_day.get(today, DailyPoint(day=today)).usage
    yesterday_usage = by_day.get(yesterday, DailyPoint(day=yesterday)).usage

    week = _window_sum(by_day, today, WEEK_DAYS)
    prev_week = _window_sum(by_day, today - datetime.timedelta(days=WEEK_DAYS), WEEK_DAYS)
    month = _window_sum(by_day, today, MONTH_DAYS)
    prev_month = _window_sum(by_day, today - datetime.timedelta(days=MONTH_DAYS), MONTH_DAYS)

    series = fill_series(points, today, series_days)
    peak = max(series, key=lambda point: point.usage, default=None)

    return UsageSummary(
        series=[DashboardDailyPoint(date=point.day.isoformat(), usage=point.usage, online=point.online) for point in series],
        totals=UsageTotals(
            today=today_usage,
            yesterday=yesterday_usage,
            week=week,
            month=month,
            total=int(total_usage if total_usage is not None else sum(point.usage for point in points)),
        ),
        averages=UsageAverages(
            daily_week=round(week / WEEK_DAYS),
            daily_month=round(month / MONTH_DAYS),
        ),
        previous=UsagePrevious(week=prev_week, month=prev_month),
        trends=UsageTrends(
            day=_trend_percent(today_usage, yesterday_usage),
            week=_trend_percent(week, prev_week),
            month=_trend_percent(month, prev_month),
        ),
        peak=UsagePeak(date=peak.day.isoformat(), usage=peak.usage) if peak and peak.usage else None,
    )


def stacked_series(
    node_points: list[NodeDailyPoint],
    today: datetime.date,
    days: int,
    child_ids: list[int],
) -> list[DashboardDailyPoint]:
    """Zero-filled stacked series: one date per day, usage keyed by child_id."""
    by_day_child: dict[tuple[datetime.date, int], NodeDailyPoint] = {(point.day, point.child_id): point for point in node_points}
    start = today - datetime.timedelta(days=days - 1)
    series: list[DashboardDailyPoint] = []
    for offset in range(days):
        day = start + datetime.timedelta(days=offset)
        by_child: dict[int, ChildUsagePoint] = {}
        total_usage = 0
        total_online = 0
        for child_id in child_ids:
            point = by_day_child.get((day, child_id), NodeDailyPoint(day=day, child_id=child_id))
            by_child[child_id] = ChildUsagePoint(usage=point.usage, online=point.online)
            total_usage += point.usage
            total_online += point.online
        series.append(
            DashboardDailyPoint(
                date=day.isoformat(),
                usage=total_usage,
                online=total_online,
                by_child=by_child,
            )
        )
    return series
