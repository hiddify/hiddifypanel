from __future__ import annotations

import datetime
import uuid
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from flask_login import UserMixin as FlaskLoginUserMixin
from sqlalchemy import BigInteger, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from hiddifypanel.database import db
from hiddifypanel.models.config_enum import Lang
from hiddifypanel.models.role import Role

if TYPE_CHECKING:
    from hiddifypanel.models.external_model.account import AccountModel


class BaseAccount(db.Model, FlaskLoginUserMixin):
    __abstract__ = True
    uuid: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(512), default="")
    username: Mapped[str | None] = mapped_column(String(100), default="", index=True)
    password: Mapped[str | None] = mapped_column(String(100), default="")
    comment: Mapped[str | None] = mapped_column(String(512), default="")
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, default=None, index=True)
    lang: Mapped[Lang | None] = mapped_column(Enum(Lang), default=None)
    deleted: Mapped[bool] = mapped_column(default=False, index=True)
    enable: Mapped[bool] = mapped_column(default=True)
    last_online: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.min)
    last_modified_time: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now)

    @property
    def role(self) -> Role | None:
        return None

    def get_id(self) -> str | None:
        return f"{self.__class__.name}_{self.id if self.hasattr('id') else '-'}"

    def is_username_unique(self) -> bool:
        cls = self.__class__()
        model = cls.query.filter(cls.username == self.username, cls.id != self.id).first()
        if model:
            return False
        return True

    def to_model(self) -> AccountModel:
        from hiddifypanel.models.external_model.account import AccountModel

        return AccountModel(name=self.name, comment=self.comment, uuid=self.uuid, telegram_id=self.telegram_id, lang=self.lang)

    def to_dict(self, convert_date=True) -> dict:
        return self.to_model().to_dict()

    def update_password(self, new_password):
        self.password = new_password
        db.session.commit()

    @classmethod
    def by_id(cls, id: int):
        # return cls.query.filter(cls.id == id).first()
        return db.session.query(cls).get(id)

    @classmethod
    def by_uuid(cls, uuid: str | None, create: bool = False):
        if not isinstance(uuid, str):
            uuid = str(uuid)
        account = cls.query.filter(cls.uuid == uuid).first()
        if not account and create:
            raise NotImplementedError
        return account

    @classmethod
    def by_username_password(cls, username: str, password: str):
        return cls.query.filter(cls.username == username, cls.password == password).first()

    @classmethod
    def external_model(cls) -> type[AccountModel]:
        from hiddifypanel.models.external_model.account import AccountModel

        return AccountModel

    @classmethod
    def add_or_update(cls, commit: bool = True, old_uuid: str | None = None, **data):
        return cls.upsert(cls.external_model().coerce(data), commit=commit, old_uuid=old_uuid)

    @classmethod
    def upsert(cls, data: AccountModel, *, commit: bool = True, old_uuid: str | None = None):
        from hiddifypanel import hutils

        db_account: BaseAccount = cls.by_uuid(old_uuid or data.uuid, create=True)

        if data.uuid and hutils.auth.is_uuid_valid(data.uuid):
            db_account.uuid = data.uuid
        if data.name:
            db_account.name = data.name
        if data.comment:
            db_account.comment = data.comment
        if data.telegram_id:
            db_account.telegram_id = data.telegram_id
        if data.lang is not None:
            db_account.lang = data.lang
        if commit:
            db.session.commit()
        return db_account

    @classmethod
    def bulk_register(cls, accounts: Iterable[Any] = (), commit: bool = True, remove: bool = False):
        rows = cls.external_model().coerce_many(accounts)
        for row in rows:
            cls.upsert(row, commit=False)
        if remove:
            keep = {str(row.uuid) for row in rows if row.uuid}
            for d in cls.query.all():
                if d.uuid not in keep:
                    db.session.delete(d)
        if commit:
            db.session.commit()
