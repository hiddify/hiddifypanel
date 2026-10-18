from __future__ import annotations

import datetime
from enum import auto
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Enum, ForeignKey, String, event, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from strenum import StrEnum

from hiddifypanel import g
from hiddifypanel.database import db, db_execute
from hiddifypanel.models.base_account import BaseAccount
from hiddifypanel.models.role import Role
from hiddifypanel.models.usage import DailyUsage

if TYPE_CHECKING:
    from hiddifypanel.models.external_model.account import AccountModel, AdminModel
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


def _outbound_slug(outbound_id: int | None) -> str | None:
    from hiddifypanel.models.outbound import Outbound

    return Outbound.slug_by_id(outbound_id)


class AdminUser(BaseAccount):
    """
    This is a model class for a user in a database that includes columns for their ID, UUID, name, online status,
    account expiration date, usage limit, package days, mode, start date, current usage, last reset time, and comment.
    """

    hide_deleted = True

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mode: Mapped[AdminMode] = mapped_column(Enum(AdminMode), default=AdminMode.agent)

    @classmethod
    def count_by_mode(cls) -> dict[AdminMode, int]:
        """Admins (not deleted) of each mode."""
        return {mode: n for mode, n in db.session.query(cls.mode, func.count()).group_by(cls.mode).all()}
    can_add_admin: Mapped[bool] = mapped_column(default=False)
    max_users: Mapped[int] = mapped_column(default=100)
    max_active_users: Mapped[int] = mapped_column(default=100)
    # None = no limit. Online means seen in the last 24 hours.
    max_online_users: Mapped[int | None] = mapped_column(default=None, nullable=True)
    # Traffic (GB) all users of this admin and its sub-admins may use together; None = no limit.
    max_total_usage_GB: Mapped[float | None] = mapped_column(default=None, nullable=True)
    #: Sign-in username instead of the UUID (lowercase, unique; never for super admins; needs a strong
    #: password). See hiddifypanel.admin_credentials.
    alias: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, index=True)
    #: [kind, target, value] rows added to the subscription of every user of this admin and its
    #: sub-admins (merged with the users' own; see proxy_v3.user_configs).
    additional_configs: Mapped[list | None] = mapped_column(JSON, default=list, nullable=True)
    #: Outbound id this admin's users (and its sub-admins' users) leave through, unless the user (or a nearer
    #: admin) chose another; None = automatic. See proxy_v3.outbounds.admin_default_outbounds.
    default_outbound_id: Mapped[int | None] = mapped_column(default=None, nullable=True)
    users: Mapped[list[User]] = relationship("User", backref="admin")
    usages: Mapped[list[DailyUsage]] = relationship("DailyUsage", backref="admin")
    parent_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_user.id"), default=1)
    # post_update: the owner is its own parent; a row that depends on itself can only be written with its parent set after it.
    parent_admin: Mapped[AdminUser | None] = relationship("AdminUser", remote_side=[id], backref="sub_admins", post_update=True)

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

        return AdminSchema.model_validate({**self.to_dict(), "default_outbound_slug": _outbound_slug(self.default_outbound_id)})

    def get_id(self) -> str | None:
        return f"admin_{self.id}"

    def to_model(self) -> AdminModel:
        from hiddifypanel.models import ConfigEnum, hconfig
        from hiddifypanel.models.external_model.account import AdminModel

        return AdminModel(
            name=self.name,
            comment=self.comment,
            uuid=self.uuid,
            telegram_id=self.telegram_id,
            lang=self.lang or hconfig(ConfigEnum.admin_lang),
            id=self.id,
            mode=self.mode,
            can_add_admin=self.can_add_admin,
            parent_admin_uuid=self.parent_admin.uuid if self.parent_admin else None,
            max_users=self.max_users,
            max_active_users=self.max_active_users,
            max_online_users=self.max_online_users,
            max_total_usage_GB=self.max_total_usage_GB,
            **({"default_outbound_slug": slug} if (slug := _outbound_slug(self.default_outbound_id)) else {}),
            # Only a deleted admin carries it (it travels to the nodes); backups never see one, since queries hide them.
            **({"deleted": True} if self.deleted else {}),
        )

    def to_dict(self, convert_date=True, dump_id=False) -> dict:
        return self.to_model().to_dict(exclude=None if dump_id else {"id"})

    @classmethod
    def new_for_uuid(cls, uuid: str) -> AdminUser:
        return AdminUser(uuid=uuid, name="unknown", parent_admin_id=AdminUser.current_admin_or_owner().id)

    @classmethod
    def external_model(cls) -> type[AdminModel]:
        from hiddifypanel.models.external_model.account import AdminModel

        return AdminModel

    @classmethod
    def add_or_update(cls, commit: bool = True, old_uuid=None, **data) -> AdminUser:
        # Forward old_uuid so uuid renames update the existing row instead of inserting a duplicate.
        return cls.upsert(cls.external_model().coerce(data), commit=commit, old_uuid=old_uuid)

    @classmethod
    def upsert(cls, data: AccountModel, *, commit: bool = True, old_uuid: str | None = None) -> AdminUser:
        row = cls.external_model().coerce(data)
        dbuser = super().upsert(row, commit=False, old_uuid=old_uuid)

        if dbuser.id != 1 and row.has("parent_admin_uuid"):
            parent = row.parent_admin_uuid
            if not parent or parent == str(dbuser.uuid):
                parent_admin = cls.current_admin_or_owner()
            else:
                parent_admin = cls.by_uuid(parent, create=False) or cls.current_admin_or_owner()
            # Never make an admin its own parent (detaches from the tree / parent quotas).
            if parent_admin.id == dbuser.id:
                if not dbuser.parent_admin_id:
                    dbuser.parent_admin_id = cls.get_super_admin().id
            else:
                dbuser.parent_admin_id = parent_admin.id
        elif dbuser.id != 1 and not dbuser.parent_admin_id:
            owner = cls.current_admin_or_owner()
            dbuser.parent_admin_id = owner.id if owner.id != dbuser.id else cls.get_super_admin().id

        if row.mode is not None:
            dbuser.mode = row.mode
        if row.can_add_admin is not None:
            dbuser.can_add_admin = row.can_add_admin
        if row.max_users is not None:
            dbuser.max_users = row.max_users
        if row.max_active_users is not None:
            dbuser.max_active_users = row.max_active_users
        # 0 or a negative value clears these optional limits (None alone means "not sent").
        if row.max_online_users is not None:
            dbuser.max_online_users = row.max_online_users if row.max_online_users > 0 else None
        if row.max_total_usage_GB is not None:
            dbuser.max_total_usage_GB = row.max_total_usage_GB if row.max_total_usage_GB > 0 else None
        if row.has("default_outbound_slug"):
            from hiddifypanel.models.outbound import Outbound

            dbuser.default_outbound_id = Outbound.id_by_slug(row.default_outbound_slug)
        if dbuser.id == 1 and dbuser.deleted:  # the owner is never deleted
            dbuser.undelete(commit=False)
        elif dbuser.deleted:  # deleted on the other panel: what is still under it here goes to the owner
            dbuser.hand_over_to(cls.get_super_admin())
        if commit:
            db.session.commit()
        return dbuser

    def recursive_users_query(self):
        from .user import User

        admin_ids = self.recursive_sub_admins_ids()
        return User.query.filter(User.added_by.in_(admin_ids), User.deleted.is_(False))

    def limited_ancestors(self) -> list[AdminUser]:
        """This admin and its parents up to the first super admin: each one's limits apply to the users below it."""
        chain: list[AdminUser] = []
        admin: AdminUser | None = self
        seen: set[int] = set()
        while admin is not None and admin.id not in seen and admin.mode != AdminMode.super_admin:
            chain.append(admin)
            seen.add(admin.id)
            admin = admin.parent_admin
        return chain

    def total_usage_GB(self) -> float:
        """Traffic used by this admin's users and all its sub-admins' users."""
        from sqlalchemy import func

        from .user import User

        used = db.session.query(func.coalesce(func.sum(User.current_usage), 0)).filter(User.added_by.in_(self.recursive_sub_admins_ids()), User.deleted.is_(False)).scalar()
        return (used or 0) / 1024**3

    def _has_room_for_one_more_user(self) -> bool:
        if self.max_total_usage_GB and self.total_usage_GB() >= self.max_total_usage_GB:
            return False
        users_count = self.recursive_users_query().count()
        max_users = self.max_users if self.max_users is not None else 10**9
        max_active = self.max_active_users if self.max_active_users is not None else 10**9
        if users_count >= max_users:
            return False
        if users_count < max_active:
            return True

        actives = [u for u in self.recursive_users_query().all() if u.is_active]
        return len(actives) < max_active

    def can_have_more_users(self):
        # A sub-admin's users also count against its parents' limits.
        return all(admin._has_room_for_one_more_user() for admin in self.limited_ancestors())

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

    def remove(self, commit: bool = True) -> None:
        """Delete this admin and its sub-admins (kept as deleted); their users and usage go to the admin who deletes them."""
        if self.id == 1 or self.id == g.account.id:
            # raise ValidationError(_("Owner can not be deleted!"))
            from apiflask import abort
            from flask_babel import gettext as __

            abort(422, __("Owner can not be deleted!"))
        users = self.recursive_users_query().all()
        for u in users:
            u.added_by = g.account.id

        ids = self.recursive_sub_admins_ids()
        DailyUsage.query.filter(DailyUsage.admin_id.in_(ids)).update({"admin_id": g.account.id})
        for admin in AdminUser.query.filter(AdminUser.id.in_(ids)).all():
            admin.soft_delete(commit=False)
        if commit:
            db.session.commit()

    def removed_by_sync(self) -> None:
        if self.id != 1:
            super().removed_by_sync()
            self.hand_over_to(AdminUser.get_super_admin())

    def hand_over_to(self, heir: AdminUser) -> None:
        """This admin's own users and sub-admins go to ``heir`` (a deleted admin would hide them from every list)."""
        from .user import User

        now = datetime.datetime.now()  # bulk updates skip the ORM hooks: the nodes see these rows changed
        User.query.filter(User.added_by == self.id).update({"added_by": heir.id, "last_modified_time": now}, synchronize_session=False)
        AdminUser.query_with_deleted().filter(AdminUser.parent_admin_id == self.id, AdminUser.id != self.id).update(
            {"parent_admin_id": heir.id, "last_modified_time": now}, synchronize_session=False
        )

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
        return AdminUser.by_id(1)  # from the session once loaded (it is asked for every new user)


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
