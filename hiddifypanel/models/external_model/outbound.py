"""External model for outbounds (parent→node sync and backups): keyed by ``slug``, never by the local id."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field, field_validator

from hiddifypanel.models.outbound import Outbound, OutboundMode

from .base import EnumValue, HBaseModel

_COPIED = (
    "name", "mode", "enabled", "position", "is_default", "domestic", "sites", "geosites", "rule_sets",
    "host", "port", "username", "password", "is_builtin", "builtin_lists", "lists_override",
)


class OutboundModel(HBaseModel):
    slug: str
    name: str
    mode: Annotated[OutboundMode, EnumValue]
    enabled: bool = True
    position: int | None = None
    is_default: bool = False
    domestic: bool = False
    sites: list[str] = Field(default_factory=list)
    geosites: list[str] = Field(default_factory=list)
    rule_sets: list[str] = Field(default_factory=list)
    host: str | None = ""
    port: int | None = None
    username: str | None = ""
    password: str | None = ""
    is_builtin: bool = False
    builtin_lists: dict[str, Any] = Field(default_factory=dict)
    lists_override: bool = False

    @field_validator("slug", mode="before")
    @classmethod
    def _slug(cls, value: object) -> str:
        slug = str(value or "").strip()
        if not slug:
            raise ValueError("slug is required")
        return slug

    @field_validator("sites", "geosites", "rule_sets", mode="before")
    @classmethod
    def _lists(cls, value: object) -> list[str]:
        return [str(v) for v in value or []]

    @field_validator("builtin_lists", mode="before")
    @classmethod
    def _builtin_lists(cls, value: object) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @classmethod
    def from_row(cls, row: Outbound) -> OutboundModel:
        return cls.model_validate({"slug": row.slug, **{f: getattr(row, f) for f in _COPIED}})

    def apply_to(self, row: Outbound) -> bool:
        """Copy the sent fields onto ``row``; returns whether a value changed."""
        changed = False
        for field in ("slug", *_COPIED):
            if not self.has(field):
                continue
            value = getattr(self, field)
            if getattr(row, field, None) != value:
                setattr(row, field, value)
                changed = True
        return changed
