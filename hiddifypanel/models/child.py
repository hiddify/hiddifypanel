from __future__ import annotations

import uuid
from enum import auto
from typing import TYPE_CHECKING

from flask import has_app_context
from sqlalchemy import Enum, String
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
    domains: Mapped[list[Domain]] = relationship("Domain", cascade="all,delete", backref="child")
    proxies: Mapped[list[Proxy]] = relationship("Proxy", cascade="all,delete", backref="child")
    boolconfigs: Mapped[list[BoolConfig]] = relationship("BoolConfig", cascade="all,delete", backref="child")
    strconfigs: Mapped[list[StrConfig]] = relationship("StrConfig", cascade="all,delete", backref="child")
    dailyusages: Mapped[list[DailyUsage]] = relationship("DailyUsage", cascade="all,delete", backref="child")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "mode": self.mode, "unique_id": self.unique_id}

    @staticmethod
    def add_or_update(commit=True, **data) -> Child:
        dbchild = Child.query.filter(Child.id == data["id"]).first()
        if not dbchild:
            dbchild = Child()
            db.session.add(dbchild)
        dbchild.name = data["name"]
        dbchild.mode = data["mode"]
        dbchild.unique_id = data["unique_id"]
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
