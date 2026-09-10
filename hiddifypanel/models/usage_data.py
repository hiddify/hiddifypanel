"""Shared usage DTO for drivers and parent/child usage sync."""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field


class UsageData(BaseModel):
    uuid: str = Field(description="The user uuid")
    upload: int = Field(default=0, description="The user upload in bytes")
    download: int = Field(default=0, description="The user download in bytes")
    devices: list[str] = Field(default_factory=list, description="The user connected devices")

    @computed_field
    @property
    def usage(self) -> int:
        return int(self.upload or 0) + int(self.download or 0)

    def add(self, other: UsageData) -> UsageData:
        """Return a new UsageData with upload/download/devices merged."""
        devices = list(dict.fromkeys([*self.devices, *other.devices]))
        return UsageData(
            uuid=self.uuid or other.uuid,
            upload=self.upload + other.upload,
            download=self.download + other.download,
            devices=devices,
        )
