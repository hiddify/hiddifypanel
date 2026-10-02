from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    """Shared pydantic base for v2 REST schemas (apiflask 3.x)."""

    model_config = ConfigDict(
        validate_assignment=True,
        from_attributes=True,
        use_enum_values=False,
        extra="ignore",
    )

    def dump(self, obj: Any | None = None) -> dict[str, Any]:
        """Marshmallow-compatible dump used by NodeApiClient and similar callers."""
        if obj is None or obj is self:
            return self.model_dump(mode="json")
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode="json")
        return self.__class__.model_validate(obj).model_dump(mode="json")

    @classmethod
    def load(cls, data: Any) -> ApiModel:
        """Marshmallow-compatible load (no empty instance required)."""
        return cls.model_validate(data)
