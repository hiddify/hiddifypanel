"""External models for proxy_v3 templates, base configs and custom proxies.

Enum fields reuse the ORM module's ``_parse_*`` helpers so aliases (``ss``, ``splithttp``,
``tls-h2``, ``h3`` …) keep working and error messages stay identical for the API; they dump
as plain ``.value`` strings like the old ``to_dict``.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import field_validator, model_validator

from hiddifypanel.models.custom_proxy import (
    ClientCore,
    CustomProxyMode,
    CustomProxyTransport,
    InboundTcpUdp,
    L7Proto,
    ServerCore,
    TemplateCategory,
    TemplateCore,
    TlsLayer,
    _parse_client_core,
    _parse_l7_reverse_proto,
    _parse_mode,
    _parse_proto,
    _parse_server_core,
    _parse_tcp_udp,
    _parse_template_core,
    _parse_tls_layer,
    _parse_transport,
)
from hiddifypanel.models.proxy import ProxyProto
from hiddifypanel.models.proxy_base_config import BaseConfigSide
from hiddifypanel.proxy_v3.context_vars.ports import normalize_port_list

from .base import EnumValue, HBaseModel, blank_to_none

# ---------------------------------------------------------------- ProxyTemplate


class ProxyTemplateModel(HBaseModel):
    id: int | None = None
    child_id: int | None = None
    """Output only."""
    child_unique_id: str | None = None
    slug: str = ""
    core: Annotated[TemplateCore, EnumValue] | None = None
    category: Annotated[TemplateCategory, EnumValue] | None = None
    name: str | None = None
    description: str | None = None
    content: str | None = None
    builtin_content: str | None = None
    """Output only."""
    builtin_override: bool = False
    is_builtin: bool = False

    @field_validator("slug", mode="before")
    @classmethod
    def _slug(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("core", mode="before")
    @classmethod
    def _core(cls, value: object) -> TemplateCore | None:
        return None if value is None else _parse_template_core(value)

    @field_validator("category", mode="before")
    @classmethod
    def _category(cls, value: object) -> TemplateCategory | None:
        if value is None or isinstance(value, TemplateCategory):
            return value
        return TemplateCategory(value)


# ---------------------------------------------------------------- ProxyBaseConfig


class ProxyBaseConfigModel(HBaseModel):
    id: int | None = None
    child_id: int | None = None
    """Output only."""
    side: Annotated[BaseConfigSide, EnumValue] | None = None
    core: str | None = None
    version: str | None = None
    name: str | None = None
    description: str | None = None
    content: str | None = None
    builtin_content: str | None = None
    """Output only."""
    builtin_override: bool = False
    is_builtin: bool = False
    enable: bool | None = None

    @field_validator("side", mode="before")
    @classmethod
    def _side(cls, value: object) -> BaseConfigSide | None:
        if value is None or isinstance(value, BaseConfigSide):
            return value
        return BaseConfigSide(value)

    @property
    def clean_version(self) -> str:
        return (self.version or "").strip()


# ---------------------------------------------------------------- CustomProxy


def _ports(value: object) -> list[int] | None:
    return None if value is None else normalize_port_list(value)


class CustomProxyServerConfigModel(HBaseModel):
    core: Annotated[ServerCore, EnumValue] | None = None
    inbound_template: str | None = None
    inbound_tcp_ports: list[int] | None = None
    inbound_udp_ports: list[int] | None = None
    inbound_port: list[int] | None = None
    """Input only: legacy single port, used when ``inbound_tcp_ports`` is empty."""
    tcp_udp: Annotated[InboundTcpUdp, EnumValue] | None = None
    upload_tcp_udp: Annotated[InboundTcpUdp, EnumValue] | None = None
    """Input only: legacy alias of ``tcp_udp`` for xhttp."""
    download_tcp_udp: Annotated[InboundTcpUdp, EnumValue] | None = None

    @field_validator("core", mode="before")
    @classmethod
    def _core(cls, value: object) -> ServerCore | None:
        return None if value is None else _parse_server_core(value)

    @field_validator("inbound_tcp_ports", "inbound_udp_ports", "inbound_port", mode="before")
    @classmethod
    def _port_list(cls, value: object) -> list[int] | None:
        return _ports(value)

    @field_validator("tcp_udp", "upload_tcp_udp", "download_tcp_udp", mode="before")
    @classmethod
    def _tcp_udp(cls, value: object) -> InboundTcpUdp | None:
        # None stays None here; applying a sent-but-empty value still means "both".
        return None if value is None else _parse_tcp_udp(value)


class CustomProxyClientCoreModel(HBaseModel):
    core: Annotated[ClientCore, EnumValue]
    version: str = ""
    slug: str | None = None
    is_builtin: bool = False
    outbounds_template: str | None = None
    link_template: str | None = None
    """Input only: legacy name of ``outbounds_template``."""
    override: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def _core_required(cls, data: Any) -> Any:
        # Route a missing core through the parser so the legacy message is kept.
        return {"core": None, **data} if isinstance(data, dict) else data

    @field_validator("core", mode="before")
    @classmethod
    def _core(cls, value: object) -> ClientCore:
        return _parse_client_core(value)

    @field_validator("version", mode="before")
    @classmethod
    def _version(cls, value: object) -> str:
        return str(value or "")

    @property
    def default_slug(self) -> str:
        return str(self.slug or f"client-{self.core.value}")

    @property
    def template(self) -> str:
        return str(self.outbounds_template or self.link_template or "")


class CustomProxyClientConfigModel(HBaseModel):
    core_configs: list[CustomProxyClientCoreModel] = []

    @field_validator("core_configs", mode="before")
    @classmethod
    def _none_is_empty(cls, value: object) -> object:
        return value or []


class BlockedByModel(HBaseModel):
    key: str
    label: str


class CustomProxyModel(HBaseModel):
    id: int | None = None
    child_id: int | None = None
    """Output only."""
    child_unique_id: str | None = None
    name: str | None = None
    slug: str | None = None
    enable: bool | None = None
    effective_enable: bool | None = None
    """Output only."""
    blocked_by: list[BlockedByModel] | None = None
    """Output only."""
    mode: Annotated[CustomProxyMode, EnumValue] | None = None
    proto: Annotated[ProxyProto, EnumValue] | None = None
    transport: Annotated[CustomProxyTransport, EnumValue] | None = None
    tls_layer: Annotated[TlsLayer, EnumValue] | None = None
    l7_reverse_proto: Annotated[L7Proto, EnumValue] | None = None
    download_tls_layer: Annotated[TlsLayer, EnumValue] | None = None
    download_domain_modes: list[str] | None = None
    categories: list[str] | None = None
    domain_modes: list[str] | None = None
    custom_path: str | None = None
    server_config: CustomProxyServerConfigModel | None = None
    client_config: CustomProxyClientConfigModel | None = None
    builtin: dict[str, Any] | None = None
    """Output only: catalog snapshot (free-form JSON)."""
    builtin_overrides: dict[str, bool] | None = None
    builtin_server_config: str | None = None
    """Output only."""
    builtin_client_config: CustomProxyClientConfigModel | None = None
    """Output only."""
    server_override: bool = False
    client_override: bool | None = None
    """Output only."""
    sort_order: int | None = None
    is_builtin: bool = False
    is_common_proxy: bool = False
    client_cores: list[str] | None = None
    """Output only."""
    server_core: Annotated[ServerCore, EnumValue] | None = None
    """Output only (input goes through ``server_config.core``)."""

    @model_validator(mode="before")
    @classmethod
    def _aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = dict(data)
        # Legacy ``l7_proto`` is only used when ``l7_reverse_proto`` is blank.
        legacy_l7 = data.pop("l7_proto", None)
        if data.get("l7_reverse_proto") in (None, "") and legacy_l7 not in (None, ""):
            data["l7_reverse_proto"] = legacy_l7
        for key in ("server_config", "client_config"):
            if key in data and data[key] is None:
                data[key] = {}
        return data

    @field_validator("mode", mode="before")
    @classmethod
    def _mode(cls, value: object) -> CustomProxyMode:
        return _parse_mode(value)

    @field_validator("proto", mode="before")
    @classmethod
    def _proto(cls, value: object) -> ProxyProto | None:
        return blank_to_none(_parse_proto)(value)

    @field_validator("transport", mode="before")
    @classmethod
    def _transport(cls, value: object) -> CustomProxyTransport | None:
        return blank_to_none(_parse_transport)(value)

    @field_validator("tls_layer", "download_tls_layer", mode="before")
    @classmethod
    def _tls(cls, value: object) -> TlsLayer | None:
        return _parse_tls_layer(value)

    @field_validator("l7_reverse_proto", mode="before")
    @classmethod
    def _l7(cls, value: object) -> L7Proto | None:
        return _parse_l7_reverse_proto(value)

    @field_validator("server_core", mode="before")
    @classmethod
    def _server_core(cls, value: object) -> ServerCore | None:
        return None if value is None else _parse_server_core(value)

    @field_validator("categories", "domain_modes", "download_domain_modes", mode="before")
    @classmethod
    def _str_list(cls, value: object) -> list[str]:
        return [str(v) for v in value] if isinstance(value, (list, tuple)) else []

    @field_validator("builtin_overrides", mode="before")
    @classmethod
    def _overrides(cls, value: object) -> dict[str, bool]:
        return {str(k): bool(v) for k, v in value.items()} if isinstance(value, dict) else {}

    def override_requested(self, field: str) -> bool:
        return bool((self.builtin_overrides or {}).get(field))
