from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BeforeValidator, Field, PlainSerializer

from hiddifypanel import hutils
from hiddifypanel.models import AdminMode, Lang, UserMode
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel


def _parse_uuid(value: Any) -> str | None:
    if value is None or not hutils.auth.is_uuid_valid(value):
        return None
    try:
        return str(uuid.UUID(str(value)))
    except ValueError:
        return None


def _parse_friendly_time(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    return hutils.convert.json_to_time(value)


def _serialize_friendly_time(value: datetime | None) -> str | None:
    if value is None:
        return None
    return hutils.convert.time_to_json(value)


def _parse_friendly_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return hutils.convert.json_to_date(value)


def _serialize_friendly_date(value: date | None) -> str | None:
    if value is None:
        return None
    return hutils.convert.date_to_json(value)


FriendlyUUID = Annotated[str | None, BeforeValidator(_parse_uuid)]
FriendlyDateTime = Annotated[
    datetime | None,
    BeforeValidator(_parse_friendly_time),
    PlainSerializer(_serialize_friendly_time, when_used="json"),
]
FriendlyDate = Annotated[
    date | None,
    BeforeValidator(_parse_friendly_date),
    PlainSerializer(_serialize_friendly_date, when_used="json"),
]


class UserSchema(ApiModel):
    uuid: FriendlyUUID = Field(description="Unique identifier for the user")
    name: str = Field(description="Name of the user")
    usage_limit_GB: float | None = Field(default=None, description="The data usage limit for the user in gigabytes")
    package_days: int | None = Field(default=None, description="The number of days in the user's package")
    mode: UserMode | None = Field(default=None, description="The mode of the user's account, which dictates access level or type")
    last_online: FriendlyDateTime = Field(default=None, description="The last time the user was online, converted to a JSON-friendly format")
    start_date: FriendlyDate = Field(default=None, description="The start date of the user's package, in a JSON-friendly format")
    current_usage_GB: float | None = Field(default=None, description="The current data usage of the user in gigabytes")
    last_reset_time: FriendlyDateTime = Field(default=None, description="The last time the user's data usage was reset, in a JSON-friendly format")
    comment: str | None = Field(default=None, description="An optional comment about the user")
    added_by_uuid: FriendlyUUID = Field(default=None, description="UUID of the admin who added this user")
    telegram_id: int | None = Field(default=None, description="The Telegram ID associated with the user")
    ed25519_private_key: str | None = Field(default=None, description="If empty, it will be created automatically, The user's private key using the Ed25519 algorithm")
    ed25519_public_key: str | None = Field(default=None, description="If empty, it will be created automatically,The user's public key using the Ed25519 algorithm")
    wg_pk: str | None = Field(default=None, description="If empty, it will be created automatically, The user's WireGuard private key")
    wg_pub: str | None = Field(default=None, description="If empty, it will be created automatically, The user's WireGuard public key")
    wg_psk: str | None = Field(default=None, description="If empty, it will be created automatically, The user's WireGuard preshared key")
    lang: Lang | None = Field(default=None, description="The language of the user")
    enable: bool | None = Field(default=None, description="Whether the user is enabled or not")
    is_active: bool | None = Field(default=None, description="Whether the user is active for using hiddify")
    id: int | None = Field(default=None, description="never use it, only for better presentation")


class PostUserSchema(UserSchema):
    uuid: FriendlyUUID = Field(default=None, description="Unique identifier for the user")
    id: int | None = Field(default=None, exclude=True)


class PatchUserSchema(ApiModel):
    uuid: FriendlyUUID = Field(default=None, description="Unique identifier for the user")
    name: str | None = Field(default=None, description="Name of the user")
    usage_limit_GB: float | None = None
    package_days: int | None = None
    mode: UserMode | None = None
    last_online: FriendlyDateTime = None
    start_date: FriendlyDate = None
    current_usage_GB: float | None = None
    last_reset_time: FriendlyDateTime = None
    comment: str | None = None
    added_by_uuid: FriendlyUUID = None
    telegram_id: int | None = None
    ed25519_private_key: str | None = None
    ed25519_public_key: str | None = None
    wg_pk: str | None = None
    wg_pub: str | None = None
    wg_psk: str | None = None
    lang: Lang | None = None
    enable: bool | None = None
    is_active: bool | None = None


class AdminSchema(ApiModel):
    name: str = Field(description="The name of the admin")
    comment: str | None = Field(default=None, description="A comment related to the admin")
    uuid: FriendlyUUID = Field(default=None, description="The unique identifier for the admin")
    mode: AdminMode = Field(description="The mode for the admin")
    can_add_admin: bool = Field(description="Whether the admin can add other admins")
    parent_admin_uuid: FriendlyUUID = Field(default=None, description="The unique identifier for the parent admin")
    telegram_id: int | None = Field(default=None, description="The Telegram ID associated with the admin")
    lang: Lang
    max_users: int | None = Field(default=None, description="The maximum number of users allowed")
    max_active_users: int | None = Field(default=None, description="The maximum number of active users allowed")


class PatchAdminSchema(ApiModel):
    name: str | None = None
    comment: str | None = None
    uuid: FriendlyUUID = None
    mode: AdminMode | None = None
    can_add_admin: bool | None = None
    parent_admin_uuid: FriendlyUUID = None
    telegram_id: int | None = None
    lang: Lang | None = None
    max_users: int | None = None
    max_active_users: int | None = None


class SuccessfulSchema(ApiModel):
    status: int | None = None
    msg: str | None = None
