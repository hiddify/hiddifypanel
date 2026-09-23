from __future__ import annotations

import datetime
from datetime import date, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from hiddifypanel import g
from hiddifypanel.database import db

from .usage_data import UsageData

if TYPE_CHECKING:
    from hiddifypanel.panel.commercial.restapi.v2.admin.dashboard_schema import DashboardStats


class DailyUsage(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[datetime.date | None] = mapped_column(Date, default=datetime.date.today(), index=True)
    usage: Mapped[int] = mapped_column(BigInteger, default=0)
    online: Mapped[int] = mapped_column(default=0)
    admin_id: Mapped[int] = mapped_column(ForeignKey("admin_user.id"), default=0)
    child_id: Mapped[int] = mapped_column(ForeignKey("child.id"), default=0)

    # def __str__(self):
    #     return str([id,date,usage,online,admin_id,child_id])

    @staticmethod
    def get_daily_usage_stats(admin_id=None, child_id=None):
        from .admin import AdminUser

        if not admin_id:
            admin_id = g.account.id
        admin = AdminUser.query.filter(AdminUser.id == admin_id).first()
        if not admin:
            return {
                "today": {"usage": 0, "online": 0},
                "h24": {"usage": 0, "online": 0},
                "m5": {"usage": 0, "online": 0},
                "yesterday": {"usage": 0, "online": 0},
                "last_30_days": {"usage": 0, "online": 0},
                "total": {"usage": 0, "online": 0, "users": 0},
            }
        sub_admins = admin.recursive_sub_admins_ids()
        # print(sub_admins)

        def filter_daily_usage_admin(query):
            # print('before',admin_id,query.all())
            if admin_id:
                query = query.filter(DailyUsage.admin_id.in_(sub_admins))
            if child_id:
                query = query.filter(DailyUsage.child_id == child_id)
            # print('after',admin_id,query.all())
            return query

        def filter_user_admin(query):
            if admin_id:
                query = query.filter(User.added_by.in_(sub_admins))

            return query

        from .user import User

        # Today's usage and online count
        today = date.today()
        today_stats = filter_daily_usage_admin(db.session.query(func.coalesce(func.sum(DailyUsage.usage), 0), func.coalesce(func.sum(DailyUsage.online), 0)).filter(DailyUsage.date == today)).first()
        users_online_today = filter_user_admin(User.query.filter(User.last_online >= today)).count()

        h24 = datetime.datetime.now() - datetime.timedelta(days=1)
        users_online_h24 = filter_user_admin(User.query.filter(User.last_online >= h24)).count()

        m5 = datetime.datetime.now() - datetime.timedelta(minutes=5)
        users_online_m5 = filter_user_admin(User.query.filter(User.last_online >= m5)).count()

        # Yesterday's usage and online count
        yesterday = date.today() - timedelta(days=1)
        yesterday_stats = filter_daily_usage_admin(db.session.query(func.coalesce(func.sum(DailyUsage.usage), 0), func.coalesce(func.sum(DailyUsage.online), 0)).filter(DailyUsage.date == yesterday)).first()
        # users_online_yesterday = User.query.filter(User.last_online >= yesterday, User.last_online < today).count()
        # Last 30 days' usage and online count
        last_30_days_start = date.today() - timedelta(days=30)
        last_30_days_stats = filter_daily_usage_admin(db.session.query(func.coalesce(func.sum(DailyUsage.usage), 0), func.coalesce(func.sum(DailyUsage.online), 0)).filter(DailyUsage.date >= last_30_days_start)).first()
        users_online_last_month = filter_user_admin(User.query.filter(User.last_online >= last_30_days_start)).count()

        # Total usage and online count
        total_stats = filter_daily_usage_admin(db.session.query(func.coalesce(func.sum(DailyUsage.usage), 0), func.coalesce(func.sum(DailyUsage.online), 0))).first()
        ten_years_ago = today - timedelta(days=365 * 10)
        users_online_last_10_years = filter_user_admin(User.query.filter(User.last_online >= ten_years_ago)).count()
        total_users = filter_user_admin(User.query).count()

        # Return the usage stats as a dictionary
        return {
            "today": {"usage": today_stats[0], "online": users_online_today},
            "h24": {"usage": 0, "online": users_online_h24},
            "m5": {"usage": 0, "online": users_online_m5},
            "yesterday": {"usage": yesterday_stats[0], "online": yesterday_stats[1]},
            "last_30_days": {"usage": last_30_days_stats[0], "online": users_online_last_month},
            "total": {"usage": total_stats[0], "online": users_online_last_10_years, "users": total_users},
        }

    @staticmethod
    def get_dashboard_stats(admin_id: int | None = None, child_id: int | None = None, series_days: int = 30, debug_nodes: bool = False) -> DashboardStats:
        """Usage history, period aggregates and user counts for the Admin V2 dashboard.

        Traffic numbers come from the parent ``daily_usage`` table (cached day by
        day). They are never fetched from child nodes. With ``debug_nodes`` the
        fake debug nodes report this server's usage.
        """
        from hiddifypanel.hutils import usage_cache
        from hiddifypanel.hutils.node_system import DEBUG_NODE_IDS, debug_node_name, is_debug_node
        from hiddifypanel.hutils.usage_stats import MONTH_DAYS, build_usage_summary
        from hiddifypanel.models.child import Child
        from hiddifypanel.panel.commercial.restapi.v2.admin.dashboard_schema import (
            DashboardNode,
            DashboardStats,
            DashboardUsers,
            UsersAverages,
            UsersOnline,
        )

        from .admin import AdminUser
        from .user import User

        if not admin_id:
            admin_id = g.account.id
        admin = AdminUser.query.filter(AdminUser.id == admin_id).first()
        sub_admins = admin.recursive_sub_admins_ids() if admin else [admin_id]

        def for_users(query):
            return query.filter(User.added_by.in_(sub_admins), User.deleted.is_(False))

        today = date.today()
        now = datetime.datetime.now()
        history_days = max(series_days, MONTH_DAYS) + MONTH_DAYS

        nodes = [DashboardNode(id=node.id, name=node.name or f"node-{node.id}", mode=str(node.mode)) for node in Child.query.order_by(Child.id).all()]
        mirrors: dict[int, int] = {}
        if debug_nodes:
            nodes += [DashboardNode(id=node_id, name=debug_node_name(node_id), mode="debug") for node_id in DEBUG_NODE_IDS]
            mirrors = {node_id: 0 for node_id in DEBUG_NODE_IDS}
        usage_child_id = 0 if is_debug_node(child_id) else child_id

        points = usage_cache.load_points(sub_admins, usage_child_id, today, history_days)
        today_usage = next((point.usage for point in points if point.day == today), 0)
        total_usage = usage_cache.lifetime_usage(sub_admins, usage_child_id, today, today_usage)
        summary = build_usage_summary(points, today, series_days=series_days, total_usage=total_usage)

        # Always split the series per node (`by_child`); a filtered request just has that one node.
        series_child_ids = [int(node.id) for node in nodes] if child_id is None else [child_id]
        summary.series = usage_cache.stacked_history(sub_admins, today, series_days, series_child_ids, mirrors=mirrors)

        online_by_day = {point.day: point.online for point in points}
        week_start = today - timedelta(days=6)
        month_start = today - timedelta(days=29)

        def online_average(days: int) -> int:
            return round(sum(online_by_day.get(today - timedelta(days=offset), 0) for offset in range(days)) / days)

        users = DashboardUsers(
            total=for_users(User.query).count(),
            enabled=for_users(User.query).filter(User.enable.is_(True)).count(),
            online=UsersOnline(
                m5=for_users(User.query).filter(User.last_online >= now - timedelta(minutes=5)).count(),
                h24=for_users(User.query).filter(User.last_online >= now - timedelta(days=1)).count(),
                today=for_users(User.query).filter(User.last_online >= today).count(),
                yesterday=online_by_day.get(today - timedelta(days=1), 0),
                week=for_users(User.query).filter(User.last_online >= week_start).count(),
                month=for_users(User.query).filter(User.last_online >= month_start).count(),
            ),
            averages=UsersAverages(daily_week=online_average(7), daily_month=online_average(30)),
        )

        return DashboardStats(
            range_days=series_days,
            series=summary.series,
            usage=summary.to_usage(),
            users=users,
            nodes=nodes,
        )


class UnsyncedUsage(db.Model):
    """Usage deltas that failed to sync to the parent panel (child nodes)."""

    __tablename__ = "unsynced_usages"

    uuid: Mapped[str] = mapped_column(String(36), primary_key=True)
    upload: Mapped[int] = mapped_column(BigInteger, default=0)
    download: Mapped[int] = mapped_column(BigInteger, default=0)

    def to_usage_data(self) -> UsageData:
        return UsageData(uuid=self.uuid, upload=int(self.upload or 0), download=int(self.download or 0))

    @classmethod
    def all_as_usage_data(cls) -> list[UsageData]:
        return [row.to_usage_data() for row in cls.query.all()]

    @classmethod
    def add_usages(cls, usages: list[UsageData], commit: bool = True) -> None:
        """Accumulate upload/download per uuid (create row if missing)."""
        for item in usages:
            if not item.uuid:
                continue
            upload = int(item.upload or 0)
            download = int(item.download or 0)
            if upload == 0 and download == 0:
                continue
            row = cls.query.filter(cls.uuid == item.uuid).first()
            if row:
                row.upload = int(row.upload or 0) + upload
                row.download = int(row.download or 0) + download
            else:
                db.session.add(cls(uuid=item.uuid, upload=upload, download=download))
        if commit:
            db.session.commit()

    @classmethod
    def clear_all(cls, commit: bool = True) -> None:
        cls.query.delete()
        if commit:
            db.session.commit()
