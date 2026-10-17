from __future__ import annotations

import datetime
import uuid
from collections.abc import Generator, Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Self

from flask_login import UserMixin as FlaskLoginUserMixin
from sqlalchemy import BigInteger, DateTime, Enum, String, event, func
from sqlalchemy.orm import Mapped, ORMExecuteState, Query, Session, mapped_column, with_loader_criteria

from hiddifypanel.database import db
from hiddifypanel.models.config_enum import Lang
from hiddifypanel.models.role import Role

if TYPE_CHECKING:
    from hiddifypanel.models.external_model.account import AccountModel


#: Rows looked up ahead by ``BaseAccount.prefetch``: (class, uuid) -> the row, or None when there is none.
_prefetched: ContextVar[dict[tuple[type, str], Any] | None] = ContextVar("account_prefetch", default=None)


@dataclass(frozen=True)
class AccountCounts:
    total: int
    enabled: int
    deleted: int


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

    #: Soft-deleted rows (``deleted``) are kept: the nodes learn about a deletion from the change feed, and a uuid is not given
    #: to another account. With ``hide_deleted`` they are left out of every ORM query of the class (sign in, lists, counts,
    #: relationships); a query that needs them uses ``query_with_deleted()``. Without it, each query filters them itself.
    hide_deleted: ClassVar[bool] = False

    @property
    def role(self) -> Role | None:
        return None

    @classmethod
    def query_with_deleted(cls) -> Query[Self]:
        return cls.query.execution_options(include_deleted=True)

    @classmethod
    def count_summary(cls) -> AccountCounts:
        """How many rows: not deleted, of those enabled, and deleted (kept, marked)."""
        deleted = cls.deleted.is_(True)
        rows = db.session.query(deleted, cls.enable, func.count()).execution_options(include_deleted=True).group_by(deleted, cls.enable).all()
        return AccountCounts(
            total=sum(n for is_deleted, _enable, n in rows if not is_deleted),
            enabled=sum(n for is_deleted, enable, n in rows if not is_deleted and enable),
            deleted=sum(n for is_deleted, _enable, n in rows if is_deleted),
        )

    def soft_delete(self, commit: bool = True) -> None:
        """Keep the row, marked as deleted; its username is freed for a new account."""
        self.deleted = True
        self.enable = False
        self.username = None
        if commit:
            db.session.commit()

    def remove(self, commit: bool = True) -> None:
        self.soft_delete(commit=commit)

    def undelete(self, commit: bool = True) -> None:
        self.deleted = False
        self.enable = True
        if commit:
            db.session.commit()

    def removed_by_sync(self) -> None:
        """The account is not in a full list from the other panel (``bulk_register(remove=True)``): it was deleted there."""
        self.soft_delete(commit=False)

    @classmethod
    def new_for_uuid(cls, uuid: str) -> Self:
        """A new account for ``by_uuid(create=True)``, before its fields are written."""
        raise NotImplementedError

    def get_id(self) -> str | None:
        return f"{self.__class__.name}_{self.id if self.hasattr('id') else '-'}"

    def is_username_unique(self) -> bool:
        # type(self), not self.__class__(): an instance's attributes are values, not columns (the filter was always false)
        cls = type(self)
        with db.session.no_autoflush:  # called from before_insert
            q = cls.query_with_deleted().filter(cls.username == self.username, cls.deleted.isnot(True))  # deleted ones have none
            if self.id is not None:
                q = q.filter(cls.id != self.id)
            return q.first() is None

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
        account = db.session.get(cls, id)
        # get() answers from the session without a query (and so without the filter) when the row was loaded before.
        if account is not None and cls.hide_deleted and account.deleted:
            return None
        return account

    @classmethod
    def by_uuid(cls, uuid: str | None, create: bool = False, include_deleted: bool = False) -> Self | None:
        """The account with ``uuid``. A deleted one only with ``include_deleted``; with ``create`` it is brought back (and a
        missing one is made)."""
        if not create:
            account = cls._find(uuid)
            return account if account is not None and (include_deleted or not account.deleted) else None
        account, created = cls._get_or_create(uuid)
        if account.deleted:
            account.undelete(commit=True)
        elif created:
            db.session.commit()
        return account

    @classmethod
    def _find(cls, account_uuid: str | None) -> Self | None:
        if account_uuid is None or account_uuid == "":
            return None
        known = _prefetched.get()
        if known is not None and (cls, str(account_uuid)) in known:
            return known[(cls, str(account_uuid))]
        return cls.query_with_deleted().filter(cls.uuid == str(account_uuid)).first()

    @classmethod
    @contextmanager
    def prefetch(cls, uuids: Iterable[str | None]) -> Generator[dict[str, Self]]:
        """Look the accounts of ``uuids`` up (deleted ones too) in a few queries; inside the block ``by_uuid`` and ``upsert`` take
        them from there instead of asking the database once per account. Accounts made inside the block are added to it."""
        wanted = sorted({str(u) for u in uuids if u})
        found: dict[str, Self] = {}
        for i in range(0, len(wanted), 500):
            found.update({a.uuid: a for a in cls.query_with_deleted().filter(cls.uuid.in_(wanted[i : i + 500])).all()})
        known = dict(_prefetched.get() or {})
        known.update({(cls, u): found.get(u) for u in wanted})
        token = _prefetched.set(known)
        try:
            yield found
        finally:
            _prefetched.reset(token)

    @classmethod
    def _get_or_create(cls, account_uuid: str | None) -> tuple[Self, bool]:
        """The account with ``account_uuid``, deleted or not, or a new one added to the session (flushed, not committed);
        and whether it is new."""
        from hiddifypanel import hutils

        account = cls._find(account_uuid)
        if account is not None:
            return account, False
        valid = account_uuid and hutils.auth.is_uuid_valid(str(account_uuid))
        account = cls.new_for_uuid(str(account_uuid) if valid else str(uuid.uuid4()))
        db.session.add(account)
        db.session.flush()
        known = _prefetched.get()
        if known is not None:
            known[(cls, account.uuid)] = account
        return account, True

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

        db_account, _created = cls._get_or_create(old_uuid or data.uuid)
        # Written means there, unless it says it is deleted (a deleted account from the other panel; its ``enable`` is its own).
        if data.deleted:
            db_account.deleted = True
            db_account.username = None  # freed, as soft_delete does
        elif db_account.deleted:
            db_account.undelete(commit=False)

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
            for d in cls.query.filter(cls.deleted.isnot(True)).all():
                if d.uuid not in keep:
                    d.removed_by_sync()
        if commit:
            db.session.commit()


def _not_deleted(c):
    # A module-level function, not a lambda: loaded rows keep this option, and the redis cache pickles them.
    return c.deleted.isnot(True)


@event.listens_for(Session, "do_orm_execute")
def _hide_deleted_accounts(state: ORMExecuteState) -> None:
    """Leave deleted rows of the classes with ``hide_deleted`` out of a query, unless it asks for them (``query_with_deleted``).
    Loading the columns of a row already in hand (a refresh) is not filtered: a row deleted a moment ago can still be read."""
    if not state.is_select or state.is_column_load or state.execution_options.get("include_deleted"):
        return
    for cls in _hidden_classes():
        # IS NOT TRUE: rows from before the column was used have NULL there, and they are not deleted.
        state.statement = state.statement.options(with_loader_criteria(cls, _not_deleted, include_aliases=True))


def _hidden_classes() -> list[type[BaseAccount]]:
    found: list[type[BaseAccount]] = []
    todo: list[type[BaseAccount]] = list(BaseAccount.__subclasses__())
    while todo:
        cls = todo.pop()
        todo.extend(cls.__subclasses__())
        if cls.hide_deleted and not cls.__dict__.get("__abstract__", False):
            found.append(cls)
    return found

