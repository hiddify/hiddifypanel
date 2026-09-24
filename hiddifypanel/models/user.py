from __future__ import annotations

import datetime
from collections.abc import Iterable
from enum import auto
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import json5
from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, String, event
from sqlalchemy.orm import DynamicMapped, Mapped, mapped_column, relationship
from strenum import StrEnum

from hiddifypanel.database import db
from hiddifypanel.models.admin import AdminUser
from hiddifypanel.models.base_account import BaseAccount
from hiddifypanel.models.role import Role

if TYPE_CHECKING:
    from hiddifypanel.models.external_model.account import AccountModel, UserModel

ONE_GIG = 1024 * 1024 * 1024


class UserMode(StrEnum):
    """
    The "UserMode" class is an enumeration that defines five possible modes: "no_reset", "monthly", "weekly",
    "daily", and "disable". These modes represent different settings that can be applied to a user account,
    such as the frequency at which data is reset or whether the account is currently disabled. The class is
    implemented using the "StrEnum" base class and the "auto()" function to generate unique values for each mode.
    """

    no_reset = auto()
    monthly = auto()
    weekly = auto()
    daily = auto()
    # disable = auto()


package_mode_dic = {UserMode.daily: 1, UserMode.weekly: 7, UserMode.monthly: 30}


class UserDetail(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), default=0)
    child_id: Mapped[int] = mapped_column(ForeignKey("child.id"), default=0)
    last_online: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.min)
    current_usage: Mapped[int] = mapped_column(BigInteger, default=0)
    connected_devices: Mapped[str] = mapped_column(String(512), default="")

    @property
    def current_usage_GB(self):
        return (self.current_usage or 0) / ONE_GIG

    @current_usage_GB.setter
    def current_usage_GB(self, value):
        self.current_usage = (value or 0) * ONE_GIG

    @property
    def devices(self):
        return []
        # return [] if not self.connected_devices else self.connected_devices.split(",")


class User(BaseAccount):
    """
    This is a model class for a user in a database that includes columns for their ID, UUID, name, online status,
    account expiration date, usage limit, package days, mode, start date, current usage, last reset time, and comment.
    """

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # removed
    # expiry_time = db.Column(db.Date, default=datetime.date.today() + relativedelta.relativedelta(months=6))
    usage_limit: Mapped[int] = mapped_column(BigInteger, default=1000 * ONE_GIG)
    package_days: Mapped[int] = mapped_column(default=90)
    mode: Mapped[UserMode] = mapped_column(Enum(UserMode), default=UserMode.no_reset)
    monthly: Mapped[bool | None] = mapped_column(default=False)  # removed
    start_date: Mapped[datetime.date | None] = mapped_column(Date)
    current_usage: Mapped[int] = mapped_column(BigInteger, default=0)
    last_reset_time: Mapped[datetime.date | None] = mapped_column(Date, default=datetime.date.today())
    added_by: Mapped[int | None] = mapped_column(ForeignKey("admin_user.id"), default=1)
    max_ips: Mapped[int] = mapped_column(default=100)
    details: DynamicMapped[UserDetail] = relationship(
        "UserDetail",
        cascade="all,delete",
        backref="user",
        lazy="dynamic",
    )

    ed25519_private_key: Mapped[str | None] = mapped_column(String(500), default="")
    ed25519_public_key: Mapped[str | None] = mapped_column(String(100), default="")
    wg_pk: Mapped[str | None] = mapped_column(String(50), default="")
    wg_pub: Mapped[str | None] = mapped_column(String(50), default="")
    wg_psk: Mapped[str | None] = mapped_column(String(50), default="")
    extra_params: Mapped[str | None] = mapped_column(String(2000), default="{}")

    def extra_params_json(self):
        try:
            return json5.loads(self.extra_params)
        except Exception:
            return {}

    @property
    def role(self) -> Role | None:
        return Role.user

    def get_id(self) -> str | None:
        return f"user_{self.id}"

    @property
    def current_usage_GB(self):
        return (self.current_usage or 0) / ONE_GIG

    @current_usage_GB.setter
    def current_usage_GB(self, value):
        self.current_usage = min(1000000 * ONE_GIG, (value or 0) * ONE_GIG)

    @property
    def usage_limit_GB(self):
        return (self.usage_limit or 0) / ONE_GIG

    @usage_limit_GB.setter
    def usage_limit_GB(self, value):
        self.usage_limit = min(1000000 * ONE_GIG, (value or 0) * ONE_GIG)

    @property
    def is_active(self) -> bool:
        """
        The "is_active" function checks if the input user object "user" is active by verifying if their mode is not
        "disable", if their usage limit hasn't been exceeded, and if there are remaining days on their account. The
        function returns a boolean value indicating whether the user is active or not.
        """

        if not self:
            return False
        if self.deleted:
            return False
        if not self.enable:
            return False
        elif self.usage_limit < self.current_usage:
            return False
        elif self.remaining_days < 0:
            return False
        # elif len(self.devices) > max(3, self.max_ips):
        #     is_active = False
        return True

    @property
    def devices(self) -> list[str]:
        res = []
        return res
        for detail in UserDetail.query.filter(UserDetail.user_id == self.id):
            for device in detail.devices:
                res[device] = 1
        return list(res.keys())

    def user_should_reset(self) -> bool:
        # print("start_date",user.start_date, "pack",package_mode_dic.get(user.mode,10000), "total",(datetime.date.today()-user.start_date).days)
        # if user.mode==UserMode.daily:
        #     return 0
        if not self.last_reset_time:
            return True
        elif not self.start_date or (datetime.date.today() - self.last_reset_time).days == 0:
            return False
        return ((datetime.date.today() - self.start_date).days % package_mode_dic.get(self.mode, 10000)) == 0

    def reset_usage(self, commit: bool = False):
        """Resets the user usages"""
        self.last_reset_time = datetime.date.today()
        self.current_usage_GB = 0

        # there's no usage of UserDetail yet, but we reset it too
        # if ud := UserDetail.query.filter(UserDetail.user_id == self.id).first():
        #    ud.current_usage_GB = 0

        if commit:
            db.session.commit()

    def days_to_reset(self):
        """
        The "days_to_reset" function calculates the number of days until the user's data usage is reset, based on the
        user's start date and mode of usage. The function returns the remaining days as an integer value. If the start
        date is not available, the function returns the total days for the user's mode.
        """
        # print("start_date",user.start_date, "pack",package_mode_dic.get(user.mode,10000), "total",(datetime.date.today()-user.start_date).days)
        # if user.mode==UserMode.daily:
        #     return 0
        if self.start_date:
            days = package_mode_dic.get(self.mode, 10000) - (datetime.date.today() - self.start_date).days % package_mode_dic.get(self.mode, 10000)
        else:
            days = package_mode_dic.get(self.mode, 10000)
        return max(-100000, min(days, 100000))

    @property
    def remaining_days(self) -> int:
        """
        The "remaining_days" function calculates the number of days remaining for a user's account package based on the
        current date and the user's start date. The function returns the remaining days as an integer value. If the start
        date is not available, the function returns the total package days.
        """
        res = -1
        if self.package_days is None:
            res = -1
        elif self.start_date:
            # print(datetime.date.today(), u.start_date,u.package_days, u.package_days - (datetime.date.today() - u.start_date).days)
            res = self.package_days - (datetime.date.today() - self.start_date).days
        else:
            # print("else",u.package_days )
            res = self.package_days
        return min(res, 10000)

    def remove(self, commit: bool = True) -> None:
        """Soft-delete the user (keep the row; hide from admin/API lists)."""
        from hiddifypanel.drivers import user_driver

        user_driver.remove_client(self)
        self.deleted = True
        self.enable = False
        if commit:
            db.session.commit()

    def purge(self, commit: bool = True) -> None:
        """Permanently remove the user row (frees the UUID for reuse)."""
        from hiddifypanel.drivers import user_driver

        user_driver.remove_client(self)
        db.session.delete(self)
        if commit:
            db.session.commit()
        else:
            db.session.flush()

    def undelete(self, commit: bool = True) -> None:
        self.deleted = False
        if commit:
            db.session.commit()

    @classmethod
    def purge_by_uuid(cls, uuid: str, commit: bool = True) -> bool:
        """Hard-delete any user (including soft-deleted) with this UUID. Returns True if a row was removed."""
        dbuser = cls.query.filter(cls.uuid == uuid).first()
        if not dbuser:
            return False
        dbuser.purge(commit=commit)
        return True

    @classmethod
    def by_uuid(cls, uuid: str, create: bool = False, include_deleted: bool = False) -> "User":
        if not isinstance(uuid, str):
            uuid = str(uuid)
        query = User.query.filter(User.uuid == uuid)
        account = query.first()
        if account and account.deleted and not include_deleted and not create:
            return None  # type: ignore[return-value]
        if account and account.deleted and create:
            account.deleted = False
            account.enable = True
            db.session.commit()
            return account
        if not account and create:
            from hiddifypanel import hutils

            if not hutils.auth.is_uuid_valid(uuid):
                uuid = str(uuid4())

            dbuser = User(uuid=uuid, name="unknown", added_by=AdminUser.current_admin_or_owner().id)
            db.session.add(dbuser)
            db.session.commit()
            account = User.by_uuid(uuid, False)
        return account

    @classmethod
    def remove_by_uuid(cls, uuid: str, commit: bool = True):
        dbuser = User.by_uuid(uuid, include_deleted=True)
        if dbuser:
            dbuser.remove(commit=commit)

    @classmethod
    def external_model(cls) -> type[UserModel]:
        from hiddifypanel.models.external_model.account import UserModel

        return UserModel

    @classmethod
    def bulk_register(cls, accounts: Iterable[Any] = (), commit: bool = True, remove: bool = False):
        from hiddifypanel.models.external_model import as_row

        # Preserve soft-delete flag from backup; only default when missing (before validation).
        rows = cls.external_model().coerce_many({"deleted": False, **as_row(account)} for account in accounts)
        for row in rows:
            cls.upsert(row, commit=False)
        if remove:
            keep = {str(row.uuid) for row in rows if row.uuid}
            for d in cls.query.filter(cls.deleted.is_(False)).all():
                if d.uuid not in keep:
                    d.remove(commit=False)
        if commit:
            db.session.commit()

    @classmethod
    def add_or_update(cls, commit: bool = True, old_uuid: str | None = None, **data) -> User:
        return cls.upsert(cls.external_model().coerce(data), commit=commit, old_uuid=old_uuid)

    @classmethod
    def upsert(cls, data: AccountModel, *, commit: bool = True, old_uuid: str | None = None) -> User:
        row = cls.external_model().coerce(data)
        dbuser: User = super().upsert(row, commit=False, old_uuid=old_uuid)
        if row.added_by_uuid:
            # Never auto-create admins from user input.
            admin = AdminUser.by_uuid(row.added_by_uuid, create=False) or AdminUser.current_admin_or_owner()
            dbuser.added_by = admin.id
        elif not dbuser.added_by:
            dbuser.added_by = 1

        if row.package_days is not None:
            dbuser.package_days = row.package_days

        if row.has("start_date"):
            dbuser.start_date = row.start_date

        if row.current_usage_GB is not None:
            dbuser.current_usage_GB = row.current_usage_GB
        elif row.current_usage is not None:
            dbuser.current_usage = row.current_usage
        elif dbuser.current_usage is None:
            dbuser.current_usage = 0

        if row.usage_limit_GB is not None:
            dbuser.usage_limit_GB = row.usage_limit_GB
        elif row.usage_limit is not None:
            dbuser.usage_limit = row.usage_limit

        if row.enable is not None:
            dbuser.enable = row.enable

        if row.deleted is not None:
            dbuser.deleted = row.deleted

        if row.ed25519_private_key and row.ed25519_public_key:
            dbuser.ed25519_private_key = row.ed25519_private_key
            dbuser.ed25519_public_key = row.ed25519_public_key
        if row.wg_pk is not None:
            dbuser.wg_pk = row.wg_pk
        if row.wg_pub is not None:
            dbuser.wg_pub = row.wg_pub
        if row.wg_psk is not None:
            dbuser.wg_psk = row.wg_psk

        if row.mode is not None or dbuser.mode is None:
            dbuser.mode = row.mode or UserMode.no_reset

        if row.last_online is not None:
            dbuser.last_online = row.last_online
        if row.last_modified_time is not None:
            dbuser.last_modified_time = row.last_modified_time
        if commit:
            db.session.commit()
        return dbuser

    @staticmethod
    def form_schema(schema):
        return schema.dump(User())

    def to_schema(self):
        from hiddifypanel.panel.commercial.restapi.v2.admin.schema import UserSchema

        return UserSchema.model_validate(self.to_dict(dump_id=True))

    def to_model(self) -> UserModel:
        from hiddifypanel.models import ConfigEnum, hconfig
        from hiddifypanel.models.external_model.account import UserModel

        return UserModel(
            name=self.name,
            comment=self.comment,
            uuid=self.uuid,
            telegram_id=self.telegram_id,
            lang=self.lang or hconfig(ConfigEnum.lang),
            id=self.id,
            last_online=self.last_online,
            last_modified_time=self.last_modified_time,
            usage_limit_GB=self.usage_limit_GB,
            package_days=self.package_days,
            mode=self.mode,
            start_date=self.start_date,
            current_usage_GB=self.current_usage_GB,
            last_reset_time=self.last_reset_time,
            added_by_uuid=self.admin.uuid if self.admin else None,
            ed25519_private_key=self.ed25519_private_key,
            ed25519_public_key=self.ed25519_public_key,
            wg_pk=self.wg_pk,
            wg_pub=self.wg_pub,
            wg_psk=self.wg_psk,
            is_active=self.is_active,
            enable=self.enable,
            deleted=bool(self.deleted),
        )

    def to_dict(self, convert_date=True, dump_id=False) -> dict:
        return self.to_model().to_dict(exclude=None if dump_id else {"id"}, convert_date=convert_date)

    # @staticmethod
    # def from_dict(data):
    #     """
    #     Returns a new User object created from a dictionary.
    #     """

    #     return User(
    #         name=data.get('name', ''),
    #         expiry_time=data.get('expiry_time', datetime.date.today() + relativedelta.relativedelta(months=6)),
    #         usage_limit_GB=data.get('usage_limit_GB', 1000),
    #         package_days=data.get('package_days', 90),
    #         mode=UserMode[data.get('mode', 'no_reset')],
    #         monthly=data.get('monthly', False),
    #         start_date=data.get('start_date', None),
    #         current_usage_GB=data.get('current_usage_GB', 0),
    #         last_reset_time=data.get('last_reset_time', datetime.date.today()),
    #         comment=data.get('comment', None),
    #         telegram_id=data.get('telegram_id', None),
    #         added_by=data.get('added_by', 1)
    #     )


@event.listens_for(User, "before_insert")
def on_user_insert(mapper, connection, target):
    from hiddifypanel import hutils

    hutils.model.gen_username(target)
    # hutils.model.gen_password(target)
    hutils.model.gen_ed25519_keys(target)
    hutils.model.gen_wg_keys(target)
    target.last_modified_time = datetime.datetime.now()


@event.listens_for(User, "before_update")
def on_user_update(mapper, connection, target):
    """Bump last_modified_time on any ORM attribute change (admin edits, usage via ORM, etc.)."""
    target.last_modified_time = datetime.datetime.now()
