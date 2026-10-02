"""External (JSON / API / backup) models for the ORM models, all built on ``HBaseModel``.

One class per entity serves both directions: ``Model.add_or_update(**data)`` and
``Model.bulk_register(rows)`` coerce input into it and call the typed ``Model.upsert(model)``;
``Model.to_model()`` builds it from a row and ``Model.to_dict()`` is ``to_model().to_dict()``.
Model code imports these submodules lazily to avoid import cycles.
"""

from .base import ExternalModelError, HBaseModel, as_row

__all__ = ["ExternalModelError", "HBaseModel", "as_row"]
