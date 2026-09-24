"""External models for nodes (Child), hconfigs and legacy (v2) proxies."""

from __future__ import annotations

import datetime
import json
from typing import Any

from fast_enum import FastEnum
from pydantic import field_serializer, field_validator

from hiddifypanel.models.child import ChildMode
from hiddifypanel.models.config_enum import ConfigEnum
from hiddifypanel.models.proxy import ProxyCDN, ProxyL3, ProxyProto, ProxyTransport

from .base import HBaseModel, IsoDateTime, parse_datetime


class ChildModel(HBaseModel):
    id: int | None = None
    name: str
    mode: ChildMode
    unique_id: str
    node_base_url: str | None = None
    last_node_to_parent_time: IsoDateTime | None = None
    last_parent_to_node_time: IsoDateTime | None = None

    @field_validator("last_node_to_parent_time", "last_parent_to_node_time", mode="before")
    @classmethod
    def _sync_time(cls, value: object) -> datetime.datetime:
        # Columns are NOT NULL; an empty/None sync time means "never synced".
        return datetime.datetime.min if value is None or value == "" else parse_datetime(value)


HConfigValue = bool | int | float | str | None


class HConfigModel(HBaseModel):
    key: ConfigEnum | None = None
    """``None`` when the key is unknown to this panel version (the row is skipped)."""
    value: HConfigValue = None
    child_unique_id: str | None = None

    @field_validator("key", mode="before")
    @classmethod
    def _key(cls, value: object) -> ConfigEnum | None:
        if isinstance(value, ConfigEnum):
            return value
        try:
            member = FastEnum.get(ConfigEnum, value)  # what ConfigEnum(value) does
        except (ValueError, TypeError, KeyError):
            return None
        return member if isinstance(member, ConfigEnum) else None

    @field_serializer("key")
    def _key_name(self, key: ConfigEnum | None) -> str | None:
        return None if key is None else str(key)

    def typed_value(self) -> HConfigValue:
        if self.key is not None and self.key.type is bool:
            return str(self.value).lower() == "true"
        return self.value


class ProxyModel(HBaseModel):
    name: str
    enable: bool
    proto: ProxyProto
    l3: ProxyL3
    transport: ProxyTransport
    cdn: ProxyCDN
    params: dict[str, Any] | None = None
    child_unique_id: str | None = None

    @field_validator("proto", mode="before")
    @classmethod
    def _proto_alias(cls, value: object) -> object:
        if str(getattr(value, "value", value) or "").strip().lower() == "ss":
            return ProxyProto.shadowsocks
        return value

    @field_validator("transport", mode="before")
    @classmethod
    def _transport_alias(cls, value: object) -> object:
        return ProxyTransport.xhttp if value == "splithttp" else value

    @field_validator("params", mode="before")
    @classmethod
    def _params_json(cls, value: object) -> object:
        return json.loads(value) if isinstance(value, str) and value.strip() else value
