from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from hiddifypanel.models import ChildMode, ConfigEnum, DomainType, ProxyCDN, ProxyL3, ProxyProto, ProxyTransport
from hiddifypanel.panel.commercial.restapi.v2.admin.schema import AdminSchema, UserSchema
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel


class DomainSchema(ApiModel):
    child_unique_id: str | None = Field(default=None, description="The child's unique id")
    domain: str = Field(description="The domain name")
    alias: str | None = Field(default=None, description="The domain alias")
    sub_link_only: bool = Field(description="Is the domain sub link only")
    mode: DomainType = Field(description="The domain type")
    cdn_ip: str | None = Field(default=None, description="The cdn ip")
    grpc: bool = Field(description="Is the domain grpc")
    ech: bool = Field(default=False, description="Enable ECH for CDN domain")
    servernames: str | None = Field(default=None, description="The servernames")
    show_domains: list[str] | None = Field(default=None, description="The list of domains to show")


class ProxySchema(ApiModel):
    child_unique_id: str | None = Field(default=None, description="The child's unique id")
    name: str = Field(description="The proxy name")
    enable: bool = Field(description="Is the proxy enabled")
    proto: ProxyProto = Field(description="The proxy protocol")
    l3: ProxyL3 = Field(description="The proxy l3")
    transport: ProxyTransport = Field(description="The proxy transport")
    cdn: ProxyCDN = Field(description="The proxy cdn")


class HConfigSchema(ApiModel):
    child_unique_id: str | None = Field(default=None, description="The child's unique id")
    key: str = Field(description="The config key")
    value: str | bool = Field(description="The config value")

    @field_validator("key")
    @classmethod
    def _hconfig_key(cls, value: str) -> str:
        if value not in [c.name for c in ConfigEnum]:
            raise ValueError(f"{value} is not a valid hconfig key.")
        return value

    @field_validator("value", mode="before")
    @classmethod
    def _coerce_value(cls, value: Any) -> str | bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value
        return str(value)


class UsageData(ApiModel):
    uuid: UUID | str | None = Field(default=None, description="The user uuid")
    usage: int = Field(default=0, description="The user usage in bytes")
    devices: list[str] | str | None = Field(default_factory=list, description="The user connected devices")

    @field_validator("devices", mode="before")
    @classmethod
    def _coerce_devices(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, dict):
            return [str(key) for key in value.keys()]
        if isinstance(value, str):
            return [part for part in value.split(",") if part]
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value]
        return [str(value)]


class UsageInputOutputSchema(ApiModel):
    usages: list[UsageData] = Field(default_factory=list, description="The list of usages")


class SyncInputSchema(ApiModel):
    domains: list[DomainSchema] | None = Field(default=None, description="The list of domains")
    proxies: list[ProxySchema] | None = Field(default=None, description="The list of proxies")
    hconfigs: list[HConfigSchema] | None = Field(default=None, description="The list of configs")

    @model_validator(mode="after")
    def _at_least_one(self) -> SyncInputSchema:
        if not (self.domains or self.proxies or self.hconfigs):
            raise ValueError("At least one field must exist (domains, proxies, or hconfigs)")
        return self


class SyncOutputSchema(ApiModel):
    users: list[UserSchema] = Field(default_factory=list, description="The list of users")
    admin_users: list[AdminSchema] = Field(default_factory=list, description="The list of admin users")


class ChildStatusInputSchema(ApiModel):
    child_unique_id: str = Field(description="The child's unique id")


class ChildStatusOutputSchema(ApiModel):
    existance: bool = Field(default=False, description="Whether child exists")


class RegisterDataSchema(ApiModel):
    users: list[UserSchema] = Field(description="The list of users")
    domains: list[DomainSchema] = Field(description="The list of domains")
    proxies: list[ProxySchema] = Field(description="The list of proxies")
    admin_users: list[AdminSchema] = Field(description="The list of admin users")
    hconfigs: list[HConfigSchema] = Field(description="The list of configs")


class RegisterInputSchema(ApiModel):
    panel_data: RegisterDataSchema = Field(description="The child's data")
    unique_id: str = Field(description="The child's unique id")
    name: str = Field(description="The child's name")
    mode: ChildMode = Field(description="The child's mode")


class RegisterOutputSchema(ApiModel):
    parent_unique_id: str | None = Field(default=None, description="The parent's unique id")
    users: list[UserSchema] = Field(default_factory=list, description="The list of users")
    admin_users: list[AdminSchema] = Field(default_factory=list, description="The list of admin users")
