"""External models for domains, server IPs and TLS certificates."""

from __future__ import annotations

import datetime
import json
from typing import Any

from pydantic import Field, field_validator, model_validator

from hiddifypanel.models.domain import DomainType, FakeMode

from .base import HBaseModel, IsoDateTime, try_parse_datetime

# ---------------------------------------------------------------- Domain

_LEGACY_REALITY_MODES = {"reality", "special_reality", "special_reality_tcp", "special_reality_grpc", "special_reality_xhttp"}


def normalize_legacy_domain_mode(mode: object, fake_mode: object) -> tuple[DomainType, FakeMode | None]:
    """Map ≤12.x domain modes (reality/fake/special_*/…) to DomainType + FakeMode."""
    mode_value = str(getattr(mode, "value", mode) or "").strip().lower()
    fake_value = fake_mode
    if isinstance(fake_value, str):
        fake_value = fake_value.strip().lower() or None

    if mode_value in {"old_xtls_direct"}:
        remapped = DomainType.direct
    elif mode_value == "auto_cdn_ip":
        remapped = DomainType.cdn
    elif mode_value == "special":
        remapped = DomainType.direct
        fake_value = FakeMode.reality
    elif mode_value == "fake":
        remapped = DomainType.direct
        fake_value = FakeMode.fake
    elif mode_value in _LEGACY_REALITY_MODES or mode_value.startswith("special_reality"):
        remapped = DomainType.direct
        fake_value = FakeMode.reality
    elif mode_value == "dnstt":
        remapped = DomainType.direct
        fake_value = FakeMode.dns
    elif mode_value:
        try:
            remapped = mode if isinstance(mode, DomainType) else DomainType(mode_value)
        except ValueError:
            remapped = DomainType.direct
    else:
        remapped = DomainType.direct

    if isinstance(fake_value, FakeMode):
        resolved_fake = fake_value
    elif isinstance(fake_value, str) and fake_value:
        try:
            resolved_fake = FakeMode(fake_value)
        except ValueError:
            resolved_fake = None
    else:
        resolved_fake = None
    return remapped, resolved_fake


DOMAIN_LINK_FIELDS = frozenset({"show_domains", "download_domain", "server_domain", "custom_proxy_slugs"})
DOMAIN_PORT_FIELDS = frozenset({"internal_port_hysteria2", "internal_port_tuic", "internal_port_naive", "internal_port_special", "need_valid_ssl"})

ExtraParams = dict[str, Any] | list[Any] | str | None


class DomainModel(HBaseModel):
    """On input, unset scalar fields fall back to their defaults on every upsert (legacy behavior)."""

    domain: str
    mode: DomainType = DomainType.direct
    fake_mode: FakeMode | None = None
    alias: str = ""
    child_unique_id: str | None = None
    cdn_ip: str = ""
    servernames: str | None = ""
    grpc: bool | None = False
    ech: bool = False
    resolve_ip: bool | None = False
    extra_params: ExtraParams = ""
    # Cross-domain links; only applied when present in the input.
    show_domains: list[str] | None = None
    download_domain: str | None = None
    server_domain: str | None = None
    custom_proxy_slugs: list[str] | None = None
    # Output only.
    child_id: int | None = None
    internal_port_hysteria2: int | None = None
    internal_port_tuic: int | None = None
    internal_port_naive: int | None = None
    internal_port_special: int | None = None
    need_valid_ssl: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def _legacy_modes(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        mode, fake_mode = normalize_legacy_domain_mode(data.get("mode"), data.get("fake_mode"))
        data = {**data, "mode": mode}
        if fake_mode is None:
            data.pop("fake_mode", None)
        else:
            data["fake_mode"] = fake_mode
        return data

    @field_validator("cdn_ip", "alias", mode="before")
    @classmethod
    def _not_null_text(cls, value: object) -> object:
        return "" if value is None else value

    @field_validator("custom_proxy_slugs", "show_domains", mode="before")
    @classmethod
    def _names(cls, value: object) -> list[str] | None:
        if value is None:
            return None
        return [str(item) for item in value] if isinstance(value, (list, tuple)) else []

    def extra_params_text(self) -> str:
        if isinstance(self.extra_params, (dict, list)):
            return json.dumps(self.extra_params)
        if self.extra_params is None:
            return "{}"
        return self.extra_params

    def without_links(self) -> DomainModel:
        """Same row without cross-domain link fields (first pass of a bulk restore)."""
        return type(self).model_validate(self.provided(exclude=DOMAIN_LINK_FIELDS))


# ---------------------------------------------------------------- ServerIp


class ServerIpModel(HBaseModel):
    id: int | None = None
    """Output only."""
    child_id: int | None = None
    """Output only."""
    child_unique_id: str | None = None
    address: str = Field(default="", validate_default=True)
    version: int | None = None
    enabled: bool | None = None
    is_auto: bool | None = None
    label: str | None = None
    health_status: str | None = None
    last_health_check: IsoDateTime | None = None
    last_health_error: str | None = None

    @field_validator("address", mode="before")
    @classmethod
    def _address(cls, value: object) -> str:
        address = str(value or "").strip()
        if not address:
            raise ValueError("address is required")
        return address

    @field_validator("last_health_check", mode="before")
    @classmethod
    def _health_time(cls, value: object) -> datetime.datetime | None:
        # An unparseable health timestamp is ignored rather than rejecting the row.
        return try_parse_datetime(value)


# ---------------------------------------------------------------- TlsStore


class TlsStoreModel(HBaseModel):
    id: int | None = None
    """Output only."""
    domain_id: int | None = None
    domain: str | None = None
    child_unique_id: str | None = None
    force_child_unique_id: str | None = None
    """Input only (legacy way to pin the child on single-row calls)."""
    certificate: str | None = None
    private_key: str | None = None
    expires_at: IsoDateTime | None = None
    valid_cert: bool | None = None
    self_signed: bool | None = None
    issuer: str | None = None
    fingerprint: str | None = None
    auto_renew: bool | None = None
    last_renewal_error: str | None = None
    updated_at: IsoDateTime | None = None

    @field_validator("expires_at", "updated_at", mode="before")
    @classmethod
    def _times(cls, value: object) -> datetime.datetime | None:
        return try_parse_datetime(value)  # empty/unparseable: ignored

    @field_validator("domain_id", mode="before")
    @classmethod
    def _domain_id(cls, value: object) -> object:
        return value or None

    @property
    def domain_key(self) -> str:
        """Domain name as stored (lookup key)."""
        return (self.domain or "").strip().lower()
