from __future__ import annotations

from typing import Any, Literal

from apiflask import Schema, fields
from pydantic import BaseModel, Field, field_validator

from hiddifypanel.proxy_v3.config_builder.dump import CLIENT_CONFIG_FILES

CLIENT_CORES = tuple(core for core, _filename in CLIENT_CONFIG_FILES)
ClientCore = Literal["hiddify-core", "xray", "sublink", "clash", "singbox"]


class RegisterWithParentInputSchema(Schema):
    parent_panel = fields.String(required=True, metadata={"description": "The parent panel url"})
    name = fields.String(required=True, metadata={"description": "The child's name in the parent panel"})
    apikey = fields.String(metadata={"description": "The parent's apikey"})


class ClientConfigsIn(BaseModel):
    core: ClientCore = Field(description=f"The client core to render, one of {list(CLIENT_CORES)}")
    user_uuid: str = Field(description="The uuid of the user to render the configs for")
    domains: list[str] = Field(description="The domains to build the configs from; unknown domains are ignored", min_length=1)
    user_agent: str = Field(default="", description="The client user agent, used to pick the template version")
    pretty: bool = Field(default=True, description="Indent the json based cores")


class ClientConfigsOut(BaseModel):
    status: int = 200
    msg: str = "ok"
    core: ClientCore
    config: str = ""
    user_uuid: str | None = None
    user_name: str | None = None
    domains: list[str] = Field(default_factory=list)
    ignored_domains: list[str] = Field(default_factory=list)
