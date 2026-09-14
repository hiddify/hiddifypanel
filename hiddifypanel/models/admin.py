from __future__ import annotations

import datetime
from enum import auto
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Enum, ForeignKey, event
from sqlalchemy.orm import Mapped, mapped_column, relationship
from strenum import StrEnum

from hiddifypanel import g
from hiddifypanel.database import db, db_execute
from hiddifypanel.models.base_account import BaseAccount
from hiddifypanel.models.role import Role
from hiddifypanel.models.usage import DailyUsage

if TYPE_CHECKING:
    from hiddifypanel.models.user import User


class AdminMode(StrEnum):
    """
    The "UserMode" class is an enumeration that defines five possible modes: "no_reset", "monthly", "weekly",
    "daily", and "disable". These modes represent different settings that can be applied to a user account,
    such as the frequency at which data is reset or whether the account is currently disabled. The class is
    implemented using the "StrEnum" base class and the "auto()" function to generate unique values for each mode.
    """

    super_admin = auto()
    admin = auto()
    agent = auto()


class AdminUser(BaseAccount):
    """
    This is a model class for a user in a database that includes columns for their ID, UUID, name, online status,
    account expiration date, usage limit, package days, mode, start date, current usage, last reset time, and comment.
    """

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mode: Mapped[AdminMode] = mapped_column(Enum(AdminMode), default=AdminMode.agent)
    can_add_admin: Mapped[bool] = mapped_column(default=False)
    max_users: Mapped[int] = mapped_column(default=100)
    max_active_users: Mapped[int] = mapped_column(default=100)
    users: Mapped[list[User]] = relationship("User", backref="admin")
    usages: Mapped[list[DailyUsage]] = relationship("DailyUsage", backref="admin")
    parent_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_user.id"), default=1)
    parent_admin: Mapped[AdminUser | None] = relationship("AdminUser", remote_side=[id], backref="sub_admins")

    @property
    def role(self) -> Role | None:
        match self.mode:
            case AdminMode.super_admin:
                return Role.super_admin
            case AdminMode.admin:
                return Role.admin
            case AdminMode.agent:
                return Role.agent
        return None

    @staticmethod
    def form_schema(schema):
        return schema.dump(AdminUser())

    def to_schema(self):
        from hiddifypanel.panel.commercial.restapi.v2.admin.schema import AdminSchema

        return AdminSchema.model_validate(self.to_dict())

    def get_id(self) -> str | None:
        return f"admin_{self.id}"

    def to_dict(self, convert_date=True, dump_id=False) -> dict:
        base = super().to_dict()
        if dump_id:
            base["id"] = self.id
        if not base.get("lang"):
            from hiddifypanel.models import ConfigEnum, hconfig

            base["lang"] = hconfig(ConfigEnum.admin_lang)
        return {
            **base,
            "mode": self.mode,
            "can_add_admin": self.can_add_admin,
            "parent_admin_uuid": self.parent_admin.uuid if self.parent_admin else None,
            "max_users": self.max_users,
            "max_active_users": self.max_active_users,
        }

    @classmethod
    def by_uuid(cls, uuid: str | None, create: bool = False) -> BaseAccount | None:
        if uuid is None or uuid == "":
            if not create:
                return None
            uuid = str(uuid4())
        elif not isinstance(uuid, str):
            uuid = str(uuid)
        account = AdminUser.query.filter(AdminUser.uuid == uuid).first()
        if not account and create:
            from hiddifypanel import hutils

            if not hutils.auth.is_uuid_valid(uuid):
                uuid = str(uuid4())
            dbuser = AdminUser(uuid=uuid, name="unknown", parent_admin_id=AdminUser.current_admin_or_owner().id)
            db.session.add(dbuser)
            db.session.commit()
            account = AdminUser.by_uuid(uuid, False)

        return account

    @classmethod
    def add_or_update(cls, commit: bool = True, old_uuid=None, **data):
        # Forward old_uuid so uuid renames update the existing row instead of inserting a duplicate.
        dbuser = super().add_or_update(commit=False, old_uuid=old_uuid, **data)

        if dbuser.id != 1 and "parent_admin_uuid" in data:
            parent = data.get("parent_admin_uuid")
            if not parent or str(parent) == str(dbuser.uuid):
                parent_admin = cls.current_admin_or_owner()
            else:
                parent_admin = cls.by_uuid(str(parent), create=False) or cls.current_admin_or_owner()
            dbuser.parent_admin_id = parent_admin.id
        elif dbuser.id != 1 and not dbuser.parent_admin_id:
            dbuser.parent_admin_id = cls.current_admin_or_owner().id

        if data.get("mode") is not None:
            dbuser.mode = data.get("mode", AdminMode.agent)
        if data.get("can_add_admin") is not None:
            dbuser.can_add_admin = data["can_add_admin"]
        if data.get("max_users") is not None:
            dbuser.max_users = data["max_users"]
        if data.get("max_active_users") is not None:
            dbuser.max_active_users = data["max_active_users"]
        if commit:
            db.session.commit()
        return dbuser

    def recursive_users_query(self):
        from .user import User

        admin_ids = self.recursive_sub_admins_ids()
        return User.query.filter(User.added_by.in_(admin_ids), User.deleted.is_(False))

    def can_have_more_users(self):
        if self.mode == AdminMode.super_admin:
            return True
        users_count = self.recursive_users_query().count()
        if users_count >= self.max_users:
            return False
        if users_count < self.max_active_users:
            return True

        actives = [u for u in self.recursive_users_query().all() if u.is_active]
        return len(actives) < self.max_active_users

    def recursive_sub_admins_ids(self, depth=20, seen=None):
        if seen is None:
            seen = set()
        sub_admin_ids = []
        if self.id not in seen:
            sub_admin_ids.append(self.id)
            seen.add(self.id)
        if depth > 0:
            for sub_admin in self.sub_admins:
                sub_admin_ids += sub_admin.recursive_sub_admins_ids(depth - 1, seen=seen)
        return sub_admin_ids

    def remove(self):
        if self.id == 1 or self.id == g.account.id:
            # raise ValidationError(_("Owner can not be deleted!"))
            from apiflask import abort
            from flask_babel import gettext as __

            abort(422, __("Owner can not be deleted!"))
        users = self.recursive_users_query().all()
        for u in users:
            u.added_by = g.account.id

        DailyUsage.query.filter(DailyUsage.admin_id.in_(self.recursive_sub_admins_ids())).update({"admin_id": g.account.id})
        AdminUser.query.filter(AdminUser.id.in_(self.recursive_sub_admins_ids())).delete()

        db.session.commit()

    def __str__(self):
        return str(self.name)

    @staticmethod
    def get_super_admin() -> "AdminUser":
        admin = AdminUser.by_id(1)
        if not admin:
            db.session.add(AdminUser(id=1, uuid=str(uuid4()), name="Owner", mode=AdminMode.super_admin, comment=""))
            db.session.commit()

            db_execute("update admin_user set id=1 where name='Owner'", commit=True)
            admin = AdminUser.by_id(1)

        return admin

    @staticmethod
    def get_super_admin_uuid() -> str:
        return AdminUser.get_super_admin().uuid

    @staticmethod
    def current_admin_or_owner():
        if g and hasattr(g, "account") and g.account and isinstance(g.account, AdminUser):
            return g.account
        return AdminUser.query.filter(AdminUser.id == 1).first()


@event.listens_for(AdminUser, "before_insert")
def before_insert(mapper, connection, target):
    from hiddifypanel import hutils

    hutils.model.gen_username(target)
    # hutils.model.gen_password(target)
    target.last_modified_time = datetime.datetime.now()


@event.listens_for(AdminUser, "before_update")
def on_admin_update(mapper, connection, target):
    """Bump last_modified_time so parent/node usage sync can detect admin changes."""
    target.last_modified_time = datetime.datetime.now()
