from __future__ import annotations

from typing import Any

from packaging.version import Version
from pydantic import BaseModel, Field


class TemplateVersion:
    """Semantic version for Jinja comparisons: platform.app.version < \"1.2.3\"."""

    version: Version

    def __init__(self, version: Version | str | None = "0.0.0"):
        if version is None or version == "":
            version = "0.0.0"
        self.version = Version(version) if isinstance(version, str) else version

    def _other_str(self, other: Any) -> str:
        if isinstance(other, TemplateVersion):
            return other.version
        return str(other)

    def get_other_version(self, other: Any) -> int:
        if isinstance(other, TemplateVersion):
            return other.version
        if isinstance(other, Version):
            return other
        return Version(str(other))

    def __str__(self) -> str:
        return self.version._str

    def __repr__(self) -> str:
        return f"TemplateVersion({self.version!r})"

    def __eq__(self, other: object) -> bool:
        other_version = self.get_other_version(other)
        return other_version == self.version

    def __ne__(self, other: object) -> bool:
        return self.version != other

    def __lt__(self, other: Any) -> bool:
        other_version = self.get_other_version(other)
        return self.version < other_version

    def __le__(self, other: Any) -> bool:
        other_version = self.get_other_version(other)
        return self.version <= other_version

    def __gt__(self, other: Any) -> bool:
        other_version = self.get_other_version(other)
        return self.version > other_version

    def __ge__(self, other: Any) -> bool:
        other_version = self.get_other_version(other)
        return self.version >= other_version


class PlatformPart(BaseModel):
    """Named platform facet with comparable version (platform.app.version)."""

    class Config:
        arbitrary_types_allowed = True

    name: str = "linux"
    version: TemplateVersion = Field(default_factory=TemplateVersion)

    def __init__(self, name: str = "linux", version: str | TemplateVersion | None = None, **data: Any) -> None:
        if version is None:
            resolved_version = TemplateVersion("0.0.0")
        elif isinstance(version, TemplateVersion):
            resolved_version = version
        else:
            resolved_version = TemplateVersion(version)
        super().__init__(name=name, version=resolved_version, **data)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (str, PlatformPart)):
            return self.name == other
        return NotImplemented

    def __str__(self) -> str:
        return self.name
