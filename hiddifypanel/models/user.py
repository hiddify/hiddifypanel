import datetime
from enum import auto
from uuid import uuid4

import json5
from sqlalchemy import event
from strenum import StrEnum

from hiddifypanel.database import db
from hiddifypanel.models.admin import AdminUser
from hiddifypanel.models.base_account import BaseAccount
from hiddifypanel.models.role import Role

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
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), default=0, nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey("child.id"), default=0, nullable=False)
    last_online = db.Column(db.DateTime, nullable=False, default=datetime.datetime.min)
    current_usage = db.Column(db.BigInteger, default=0, nullable=False)
    connected_devices = db.Column(db.String(512), default="", nullable=False)

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

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    last_online = db.Column(db.DateTime, nullable=False, default=datetime.datetime.min)
    last_modified_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)
    # removed
    # expiry_time = db.Column(db.Date, default=datetime.date.today() + relativedelta.relativedelta(months=6))
    usage_limit = db.Column(db.BigInteger, default=1000 * ONE_GIG, nullable=False)
    package_days = db.Column(db.Integer, default=90, nullable=False)
    mode = db.Column(db.Enum(UserMode), default=UserMode.no_reset, nullable=False)
    monthly = db.Column(db.Boolean, default=False)  # removed
    start_date = db.Column(db.Date, nullable=True)
    current_usage = db.Column(db.BigInteger, default=0, nullable=False)
    last_reset_time = db.Column(db.Date, default=datetime.date.today())
    added_by = db.Column(db.Integer, db.ForeignKey("admin_user.id"), default=1)
    max_ips = db.Column(db.Integer, default=100, nullable=False)
    details = db.relationship(
        "UserDetail",
        cascade="all,delete",
        backref="user",
        lazy="dynamic",
    )

    ed25519_private_key = db.Column(db.String(500), default="")
    ed25519_public_key = db.Column(db.String(100), default="")
    wg_pk = db.Column(db.String(50), default="")
    wg_pub = db.Column(db.String(50), default="")
    wg_psk = db.Column(db.String(50), default="")
    extra_params = db.Column(db.String(2000), nullable=True, default="{}")

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
    def bulk_register(cls, accounts: list = [], commit: bool = True, remove: bool = False):
        for u in accounts:
            data = {**u.model_dump(), "deleted": False}
            cls.add_or_update(commit=False, **data)
        if remove:
            keep = {str(u.get("uuid")) for u in accounts if u.get("uuid")}
            for d in cls.query.filter(cls.deleted.is_(False)).all():
                if d.uuid not in keep:
                    d.remove(commit=False)
        if commit:
            db.session.commit()

    @classmethod
    def add_or_update(cls, commit: bool = True, **data):
        from hiddifypanel import hutils

        dbuser: User = super().add_or_update(commit=commit, **data)
        if data.get("added_by_uuid"):
            admin = AdminUser.by_uuid(data.get("added_by_uuid"), create=True) or AdminUser.current_admin_or_owner()  # type: ignore
            dbuser.added_by = admin.id
        elif not dbuser.added_by:
            dbuser.added_by = 1

        # if data.get('expiry_time', ''): #v4
        #     last_reset_time = hutils.convert.json_to_time(data.get('last_reset_time', '')) or datetime.date.today()

        #     expiry_time = hutils.convert.json_to_date(data['expiry_time'])
        #     dbuser.start_date = last_reset_time
        #     dbuser.package_days = (expiry_time - last_reset_time).days  # type: ignore
        # el
        if data.get("package_days") is not None:
            dbuser.package_days = data["package_days"]

            if data.get("start_date"):
                dbuser.start_date = hutils.convert.json_to_date(data["start_date"])
            elif "start_date" in data and data["start_date"] is None:
                dbuser.start_date = None

        if (c_GB := data.get("current_usage_GB")) is not None:
            dbuser.current_usage_GB = c_GB
        elif (c := data.get("current_usage")) is not None:
            dbuser.current_usage = c
        elif dbuser.current_usage is None:
            dbuser.current_usage = 0

        if (l_GB := data.get("usage_limit_GB")) is not None:
            dbuser.usage_limit_GB = l_GB
        elif (l := data.get("usage_limit")) is not None:
            dbuser.usage_limit = l
        elif dbuser.usage_limit_GB is None:
            dbuser.usage_limit_GB = 1000

        if data.get("enable") is not None:
            dbuser.enable = data["enable"]

        if data.get("deleted") is not None:
            dbuser.deleted = bool(data["deleted"])

        if data.get("ed25519_private_key", "") and data.get("ed25519_public_key", ""):
            dbuser.ed25519_private_key = data.get("ed25519_private_key", "")
            dbuser.ed25519_public_key = data.get("ed25519_public_key", "")
        if data.get("wg_pk") is not None:
            dbuser.wg_pk = data["wg_pk"]
        if data.get("wg_pub") is not None:
            dbuser.wg_pub = data["wg_pub"]
        if data.get("wg_psk") is not None:
            dbuser.wg_psk = data["wg_psk"]

        if data.get("mode") is not None or dbuser.mode is None:
            mode = data.get("mode", UserMode.no_reset)
            if mode == "disable":
                mode = UserMode.no_reset
                dbuser.enable = False
            dbuser.mode = mode

        if data.get("last_online") is not None:
            dbuser.last_online = hutils.convert.json_to_time(data.get("last_online")) or datetime.datetime.min
        if data.get("last_modified_time") is not None:
            dbuser.last_modified_time = hutils.convert.json_to_time(data.get("last_modified_time")) or datetime.datetime.now()
        if commit:
            db.session.commit()
        return dbuser

    @staticmethod
    def form_schema(schema):
        return schema.dump(User())

    def to_schema(self):
        from hiddifypanel.panel.commercial.restapi.v2.admin.schema import UserSchema

        return UserSchema.model_validate(self.to_dict(dump_id=True))

    def to_dict(self, convert_date=True, dump_id=False) -> dict:
        base = super().to_dict()
        from hiddifypanel import hutils

        if dump_id:
            base["id"] = self.id
        if not base.get("lang"):
            from hiddifypanel.models import ConfigEnum, hconfig

            base["lang"] = hconfig(ConfigEnum.lang)
        return {
            **base,
            "last_online": hutils.convert.time_to_json(self.last_online) if convert_date else self.last_online,
            "last_modified_time": hutils.convert.time_to_json(self.last_modified_time) if convert_date else self.last_modified_time,
            "usage_limit_GB": self.usage_limit_GB,
            "package_days": self.package_days,
            "mode": self.mode,
            "start_date": hutils.convert.date_to_json(self.start_date) if convert_date else self.start_date,
            "current_usage_GB": self.current_usage_GB,
            "last_reset_time": hutils.convert.time_to_json(self.last_reset_time) if convert_date else self.last_reset_time,
            # 'expiry_time': hutils.convert.date_to_json(self.expiry_time) if convert_date else self.expiry_time,
            "added_by_uuid": self.admin.uuid if self.admin else None,
            "ed25519_private_key": self.ed25519_private_key,
            "ed25519_public_key": self.ed25519_public_key,
            "wg_pk": self.wg_pk,
            "wg_pub": self.wg_pub,
            "wg_psk": self.wg_psk,
            "is_active": self.is_active,
            "enable": self.enable,
            "deleted": bool(self.deleted),
        }

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
