import uuid

from flask_login import UserMixin as FlaskLoginUserMixin
from sqlalchemy import BigInteger, Column, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from hiddifypanel.database import db
from hiddifypanel.models.config_enum import Lang
from hiddifypanel.models.role import Role


class BaseAccount(db.Model, FlaskLoginUserMixin):
    __abstract__ = True
    uuid: Mapped[str] = Column(String(36), default=lambda: str(uuid.uuid4()), nullable=False, unique=True, index=True)
    name: Mapped[str] = Column(String(512), nullable=False, default="")
    username: Mapped[str] = Column(String(100), nullable=True, default="", index=True)
    password: Mapped[str] = Column(String(100), nullable=True, default="")
    comment: Mapped[str] = Column(String(512), nullable=True, default="")
    telegram_id: Mapped[int | None] = Column(BigInteger, nullable=True, default=None, index=True)
    lang: Mapped[Lang] = mapped_column(Enum(Lang), default=None)
    deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    enable = db.Column(db.Boolean, default=True, nullable=False)

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

    def to_dict(self, convert_date=True) -> dict:
        return {"name": self.name, "comment": self.comment, "uuid": self.uuid, "telegram_id": self.telegram_id, "lang": self.lang}

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
    def add_or_update(cls, commit: bool = True, old_uuid: str | None = None, **data):

        db_account: BaseAccount = cls.by_uuid(old_uuid or data.get("uuid"), create=True)
        from hiddifypanel import hutils

        if (uuid := data.get("uuid")) and hutils.auth.is_uuid_valid(uuid):
            db_account.uuid = data["uuid"]

        if (name := data.get("name")) and isinstance(name, str):
            db_account.name = name

        if (comment := data.get("comment")) and isinstance(comment, str):
            db_account.comment = comment
        if (telegram_id := data.get("telegram_id")) and isinstance(telegram_id, int):
            db_account.telegram_id = hutils.convert.to_int(telegram_id)
        if (lang := data.get("lang")) and isinstance(lang, Lang):
            db_account.lang = lang
        if commit:
            db.session.commit()
        return db_account

    @classmethod
    def bulk_register(cls, accounts: list = [], commit: bool = True, remove: bool = False):
        for u in accounts:
            cls.add_or_update(commit=False, **u)
        if remove:
            dd = {str(u["uuid"]): 1 for u in accounts}
            for d in cls.query.all():
                if d.uuid not in dd:
                    db.session.delete(d)
        if commit:
            db.session.commit()
