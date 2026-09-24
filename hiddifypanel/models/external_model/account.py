from __future__ import annotations

import datetime
from typing import Any

from pydantic import FieldSerializationInfo, ValidationInfo, field_serializer, field_validator, model_validator

from hiddifypanel.models.admin import AdminMode
from hiddifypanel.models.config_enum import Lang
from hiddifypanel.models.user import UserMode

from .base import HBaseModel, parse_date, parse_datetime, try_parse_datetime


class AccountModel(HBaseModel):
    """Fields shared by users and admins. Invalid optional values are ignored (``None``), not errors."""

    uuid: str | None = None
    name: str | None = None
    comment: str | None = None
    telegram_id: int | None = None
    lang: Lang | None = None
    id: int | None = None
    """Output only (``dump_id``); never used to match rows."""

    @field_validator("uuid", mode="before")
    @classmethod
    def _uuid_str(cls, value: object) -> str | None:
        return None if value is None else str(value)

    @field_validator("name", "comment", mode="before")
    @classmethod
    def _text_only(cls, value: object) -> str | None:
        return value if isinstance(value, str) else None

    @field_validator("telegram_id", mode="before")
    @classmethod
    def _telegram_id(cls, value: object) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None

    @field_validator("lang", mode="before")
    @classmethod
    def _lang(cls, value: object) -> Lang | None:
        if isinstance(value, Lang):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return Lang(value.strip())
            except (ValueError, KeyError):
                return None
        return None


_TIME_FIELDS = ("last_online", "last_modified_time", "last_reset_time")


class UserModel(AccountModel):
    added_by_uuid: str | None = None
    package_days: int | None = None
    start_date: datetime.date | None = None
    current_usage_GB: float | None = None
    usage_limit_GB: float | None = None
    current_usage: int | None = None
    """Input only: legacy byte count, used when ``current_usage_GB`` is absent."""
    usage_limit: int | None = None
    """Input only: legacy byte count, used when ``usage_limit_GB`` is absent."""
    mode: UserMode | None = None
    enable: bool | None = None
    deleted: bool | None = None
    ed25519_private_key: str | None = None
    ed25519_public_key: str | None = None
    wg_pk: str | None = None
    wg_pub: str | None = None
    wg_psk: str | None = None
    last_online: datetime.datetime | None = None
    last_modified_time: datetime.datetime | None = None
    last_reset_time: datetime.datetime | datetime.date | None = None
    """Output only (input is ignored, as before)."""
    is_active: bool | None = None
    """Output only."""

    @model_validator(mode="before")
    @classmethod
    def _legacy_disable_mode(cls, data: Any) -> Any:
        # ≤v7 had a "disable" mode: "no reset" + disabled account.
        if isinstance(data, dict) and str(getattr(data.get("mode"), "value", data.get("mode"))) == "disable":
            return {**data, "mode": UserMode.no_reset, "enable": False}
        return data

    @field_validator("start_date", mode="before")
    @classmethod
    def _start_date(cls, value: object) -> datetime.date | None:
        return parse_date(value) if value else None

    @field_validator("last_online", "last_modified_time", mode="before")
    @classmethod
    def _times(cls, value: object, info: ValidationInfo) -> datetime.datetime | None:
        if value == "":  # legacy exports: empty means "never" / "now"
            return datetime.datetime.min if info.field_name == "last_online" else datetime.datetime.now()
        return None if value is None else parse_datetime(value)

    @field_validator("last_reset_time", mode="before")
    @classmethod
    def _reset_time(cls, value: object) -> datetime.datetime | datetime.date | None:
        return value if isinstance(value, datetime.date) else try_parse_datetime(value)

    @field_validator("package_days", "current_usage", "usage_limit", mode="before")
    @classmethod
    def _whole_number(cls, value: object) -> object:
        return int(value) if isinstance(value, float) else value

    @field_serializer("start_date", *_TIME_FIELDS)
    def _json_dates(self, value: datetime.date | None, info: FieldSerializationInfo) -> str | datetime.date | None:
        """Context ``convert_date`` (default on) renders the panel's JSON date/time strings."""
        from hiddifypanel import hutils

        if value is None or not (info.context or {}).get("convert_date", True):
            return value
        if info.field_name == "start_date":
            return value.strftime("%Y-%m-%d")
        if not isinstance(value, datetime.datetime):
            value = datetime.datetime.combine(value, datetime.time())
        return hutils.convert.time_to_json(value)


class AdminModel(AccountModel):
    mode: AdminMode | None = None
    can_add_admin: bool | None = None
    parent_admin_uuid: str | None = None
    max_users: int | None = None
    max_active_users: int | None = None

    @field_validator("parent_admin_uuid", mode="before")
    @classmethod
    def _parent_str(cls, value: object) -> str | None:
        return None if value is None else str(value)
