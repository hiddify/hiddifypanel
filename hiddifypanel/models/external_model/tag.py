"""External models for tags and their links (backups): tags are keyed by name, links by account uuid + tag name."""

from __future__ import annotations

from typing import Annotated

from pydantic import field_validator

from hiddifypanel.models.tag import COLORS, KINDS

from .base import HBaseModel


class TagModel(HBaseModel):
    name: str
    color: str = "blue"
    is_default: bool = False
    position: int = 0

    @field_validator("name", mode="before")
    @classmethod
    def _name(cls, value: object) -> str:
        name = " ".join(str(value or "").split())[:60]
        if not name:
            raise ValueError("name is required")
        return name

    @field_validator("color", mode="before")
    @classmethod
    def _color(cls, value: object) -> str:
        return value if value in COLORS else "blue"


class TagLinkModel(HBaseModel):
    kind: str
    account_uuid: str
    tag: Annotated[str, "tag name"]

    @field_validator("kind")
    @classmethod
    def _kind(cls, value: str) -> str:
        if value not in KINDS:
            raise ValueError(f"unknown kind {value!r}")
        return value

    @field_validator("tag", "account_uuid", mode="before")
    @classmethod
    def _text(cls, value: object) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("must not be empty")
        return text
