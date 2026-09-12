from __future__ import annotations

import uuid
from datetime import datetime
from enum import auto
from typing import TYPE_CHECKING

from flask import has_app_context
from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from strenum import StrEnum

from hiddifypanel import g
from hiddifypanel.database import db

if TYPE_CHECKING:
    from hiddifypanel.models.config import BoolConfig, StrConfig
    from hiddifypanel.models.domain import Domain
    from hiddifypanel.models.proxy import Proxy
    from hiddifypanel.models.usage import DailyUsage


class ChildMode(StrEnum):
    virtual = auto()
    remote = auto()  # it's child
    parent = auto()


# the child model is node


class Child(db.Model):  # type: ignore
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    mode: Mapped[ChildMode] = mapped_column(Enum(ChildMode), default=ChildMode.virtual)
    node_base_url: Mapped[str] = mapped_column(String(200), default="")
    # ip = db.Column(db.String(200), nullable=False, unique=True)
    unique_id: Mapped[str] = mapped_column(String(200), default=lambda: str(uuid.uuid4()), unique=True)
    last_node_to_parent_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.min)
    last_parent_to_node_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.min)
    domains: Mapped[list[Domain]] = relationship("Domain", cascade="all,delete", backref="child")
    proxies: Mapped[list[Proxy]] = relationship("Proxy", cascade="all,delete", backref="child")
    boolconfigs: Mapped[list[BoolConfig]] = relationship("BoolConfig", cascade="all,delete", backref="child")
    strconfigs: Mapped[list[StrConfig]] = relationship("StrConfig", cascade="all,delete", backref="child")
    dailyusages: Mapped[list[DailyUsage]] = relationship("DailyUsage", cascade="all,delete", backref="child")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "mode": self.mode,
            "unique_id": self.unique_id,
            "last_node_to_parent_time": self.last_node_to_parent_time.isoformat() if self.last_node_to_parent_time else None,
            "last_parent_to_node_time": self.last_parent_to_node_time.isoformat() if self.last_parent_to_node_time else None,
        }

    def mark_node_to_parent(self, when: datetime | None = None, *, commit: bool = False) -> None:
        self.last_node_to_parent_time = when or datetime.now()
        if commit:
            db.session.commit()

    def mark_parent_to_node(self, when: datetime | None = None, *, commit: bool = False) -> None:
        self.last_parent_to_node_time = when or datetime.now()
        if commit:
            db.session.commit()

    @staticmethod
    def add_or_update(commit=True, **data) -> Child:
        dbchild = Child.query.filter(Child.id == data["id"]).first()
        if not dbchild:
            dbchild = Child()
            db.session.add(dbchild)
        dbchild.name = data["name"]
        dbchild.mode = data["mode"]
        dbchild.unique_id = data["unique_id"]
        if "last_node_to_parent_time" in data:
            dbchild.last_node_to_parent_time = _parse_optional_datetime(data["last_node_to_parent_time"])
        if "last_parent_to_node_time" in data:
            dbchild.last_parent_to_node_time = _parse_optional_datetime(data["last_parent_to_node_time"])
        if commit:
            db.session.commit()
        return dbchild

    @staticmethod
    def bulk_register(childs, commit=True):
        for child in childs:
            Child.add_or_update(commit=False, **child)
        if commit:
            db.session.commit()

    @classmethod
    def by_id(cls, id: int) -> Child:
        return db.session.query(Child).filter(Child.id == id).first()

    @classmethod
    def by_unique_id(cls, unique_id: str) -> Child:
        return db.session.query(Child).filter(Child.unique_id == unique_id).first()

    @classmethod
    def current(cls) -> Child:
        if has_app_context() and hasattr(g, "child"):
            return g.child
        child = Child.by_id(0)
        # if child is None:
        #     tmp_uuid = str(uuid.uuid4())
        #     db.session.add(Child(id=0, unique_id=tmp_uuid, name="Root"))
        #     db.session.commit()
        #     db_execute(f"update child set id=0 where unique_id='{tmp_uuid}'", commit=True)
        #     child = Child.by_id(0)
        return child

    @staticmethod
    def node() -> Child | None:
        """Authenticated peer node from ``g.node`` (parent/child API key auth)."""
        if has_app_context() and hasattr(g, "node"):
            return getattr(g, "node", None)
        return None


def _parse_optional_datetime(raw: object) -> datetime | None:
    if isinstance(raw, str) and raw:
        return datetime.fromisoformat(raw)
    if isinstance(raw, datetime):
        return raw
    return None
