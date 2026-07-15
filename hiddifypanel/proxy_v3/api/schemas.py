from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from hiddifypanel.models import CustomProxyMode, CustomProxyTransport, L7Proto, ProxyProto, TemplateCategory
from hiddifypanel.models.custom_proxy import TlsLayer


class ProxyTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    child_id: int
    slug: str
    core: str
    category: TemplateCategory
    name: str
    description: str = ""
    content: str = ""
    is_builtin: bool = False
    builtin_override: bool = False
    builtin_content: str = ""


class ProxyTemplateIn(BaseModel):
    slug: str | None = None
    core: str
    category: TemplateCategory
    name: str
    description: str = ""
    content: str = ""


class PatchProxyTemplateIn(BaseModel):
    slug: str | None = None
    core: str | None = None
    category: TemplateCategory | None = None
    name: str | None = None
    description: str | None = None
    content: str | None = None
    builtin_override: bool | None = None


class ProxyBaseConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    child_id: int
    side: str
    core: str
    version: str = "1.0.0"
    name: str
    description: str = ""
    content: str = ""
    is_builtin: bool = False
    enable: bool = True
    builtin_override: bool = False
    builtin_content: str = ""


class ProxyBaseConfigIn(BaseModel):
    side: str
    core: str
    version: str = "1.0.0"
    name: str
    description: str = ""
    content: str = ""
    enable: bool = True


class PatchProxyBaseConfigIn(BaseModel):
    side: str | None = None
    core: str | None = None
    version: str | None = None
    name: str | None = None
    description: str | None = None
    content: str | None = None
    enable: bool | None = None
    builtin_override: bool | None = None


class TemplateVariableItem(BaseModel):
    category: str
    category_label: str | None = None
    name: str
    access: str
    access_bracket: str | None = None
    value: object | None = None
    label: str
    description: str


class TemplateVariableGroup(BaseModel):
    id: str
    label: str
    variables: list[TemplateVariableItem] = Field(default_factory=list)


class TemplateVariablesOut(BaseModel):
    groups: list[TemplateVariableGroup] = Field(default_factory=list)
    variables: list[TemplateVariableItem] = Field(default_factory=list)


class ServerConfigIn(BaseModel):
    core: str | None = None
    inbound_tcp_ports: list[int] = Field(default_factory=list)
    inbound_udp_ports: list[int] = Field(default_factory=list)
    inbound_port: int | None = None
    tcp_udp: str = "both"
    tag: str | None = None
    direct_port_access: bool = False
    template_slugs: list[str] = Field(default_factory=list)
    inbound_template: str | None = None


class ClientCoreConfigIn(BaseModel):
    core: str
    version: str | None = None
    min_version: str | None = None
    max_version: str | None = None
    slug: str | None = None
    is_builtin: bool = False
    outbounds_template: str | None = None
    override: bool = False


class ClientConfigIn(BaseModel):
    core_configs: list[ClientCoreConfigIn] = Field(default_factory=list)


class CustomProxyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    child_id: int | None = None
    name: str
    slug: str | None = None
    enable: bool = True
    mode: CustomProxyMode
    proto: ProxyProto | None = None
    transport: CustomProxyTransport | None = None
    tls_layer: TlsLayer | None = None
    l7_reverse_proto: L7Proto | None = None
    download_tls_layer: TlsLayer | None = None
    download_domain_modes: list[str] | None = None
    categories: list[str] = Field(default_factory=list)
    domain_modes: list[str] = Field(default_factory=list)
    custom_path: str = ""
    domain_ids: list[int] = Field(default_factory=list)
    server_config: ServerConfigIn | dict = Field(default_factory=dict)
    client_config: ClientConfigIn | dict = Field(default_factory=dict)
    sort_order: int = 0
    client_cores: list[str] = Field(default_factory=list)
    server_core: str | None = None
    is_builtin: bool = False
    server_override: bool = False
    client_override: bool = False
    builtin: dict | None = None
    builtin_overrides: dict[str, bool] | None = None
    builtin_server_config: str | None = None
    builtin_client_config: ClientConfigIn | dict | None = None
