from __future__ import annotations

import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import DynamicMapped, Mapped, mapped_column, relationship

from hiddifypanel.database import db


class Report(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), default=0)
    asn_id: Mapped[str] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str | None] = mapped_column(String(200))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    accuracy_radius: Mapped[float | None] = mapped_column(Float)

    date: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.min)
    details: DynamicMapped[ReportDetail] = relationship(
        "ReportDetail",
        cascade="all,delete",
        backref="report",
        lazy="dynamic",
    )


class ReportDetail(db.Model):
    report_id: Mapped[int] = mapped_column(ForeignKey("report.id"), primary_key=True)
    proxy_id: Mapped[int] = mapped_column(ForeignKey("proxy.id"), primary_key=True)
    ping: Mapped[int | None] = mapped_column(default=-1)
