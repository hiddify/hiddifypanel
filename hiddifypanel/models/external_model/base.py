"""``HBaseModel``: the one pydantic base for every external (JSON/API/backup) view of an ORM model.

The same class is used in both directions:

* **in** — ``Model.add_or_update(**data)`` / ``bulk_register(rows)`` coerce the raw row into it.
  Unknown keys are ignored, legacy aliases are normalized by validators, and the keys the
  caller actually sent are kept in ``model_fields_set`` (``has()``) so partial updates only
  touch what was sent.
* **out** — ``Model.to_model()`` builds it from the ORM row and ``Model.to_dict()`` is
  ``to_model().to_dict()``. Fields that only make sense on output (``is_active``,
  ``blocked_by`` …) are ignored by ``upsert``.
"""

from __future__ import annotations

import datetime
import enum
from collections.abc import Callable, Iterable, Mapping
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, PlainSerializer, ValidationError


class ExternalModelError(ValueError):
    """Input failed validation. ``str()`` is the first human-readable reason, so API handlers
    doing ``abort(409, str(e))`` keep returning the same messages as before."""

    def __init__(self, message: str, errors: list[Any] | None = None):
        super().__init__(message)
        self.errors: list[Any] = errors or []


def _first_error_message(exc: ValidationError) -> str:
    errors = exc.errors(include_url=False)
    if not errors:
        return str(exc)
    first = errors[0]
    ctx_error = (first.get("ctx") or {}).get("error")
    if first["type"] == "value_error" and ctx_error is not None:
        return str(ctx_error)
    loc = ".".join(str(part) for part in first["loc"])
    return f"{loc}: {first['msg']}" if loc else first["msg"]


def as_row(item: object) -> dict[str, Any]:
    """Plain dict view of a row given as a mapping, an API schema or an ``HBaseModel``."""
    if isinstance(item, HBaseModel):
        return item.provided()
    if isinstance(item, BaseModel):
        return item.model_dump()
    if isinstance(item, Mapping):
        return {str(k): v for k, v in item.items()}
    raise ExternalModelError(f"Unsupported row type: {type(item).__name__}")


class HBaseModel(BaseModel):
    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True, populate_by_name=True)

    # ------------------------------------------------------------ in

    @classmethod
    def coerce(cls, data: object = None, /, **overrides: Any) -> Self:
        """Build from a dict, an API schema, or another ``HBaseModel``."""
        if isinstance(data, cls) and not overrides:
            return data
        raw = {} if data is None else as_row(data)
        raw.update(overrides)
        try:
            return cls.model_validate(raw)
        except ValidationError as e:
            raise ExternalModelError(_first_error_message(e), list(e.errors(include_url=False))) from e

    @classmethod
    def coerce_many(cls, rows: Iterable[object] | None) -> list[Self]:
        return [cls.coerce(row) for row in rows or ()]

    def has(self, field: str) -> bool:
        """True when the input contained ``field`` (even as ``None``)."""
        return field in self.model_fields_set

    def provided(self, *, exclude: Iterable[str] = ()) -> dict[str, Any]:
        """Only the fields the input contained, with parsed values."""
        skip = set(exclude)
        return {name: getattr(self, name) for name in self.model_fields_set if name not in skip}

    # ------------------------------------------------------------ out

    def to_dict(self, *, exclude: set[str] | None = None, **context: Any) -> dict[str, Any]:
        """Legacy ``to_dict`` shape: only fields that were filled in, minus ``exclude``."""
        return self.model_dump(exclude_unset=True, exclude=exclude, context=context or None)


# ---------------------------------------------------------------- field types


def _iso(value: datetime.datetime) -> str:
    return value.isoformat()


def _enum_value(value: enum.Enum) -> Any:
    return value.value


IsoDateTime = Annotated[datetime.datetime, PlainSerializer(_iso)]
"""Parsed as a datetime, dumped as an ISO-8601 string."""

EnumValue = PlainSerializer(_enum_value)
"""Annotate an enum field with this to dump its plain ``.value``."""


# ---------------------------------------------------------------- lenient parsers


def _fix_year(text: str) -> str:
    """Pad short years (``1-01-01 00:00:00`` from ``datetime.min``) to four digits."""
    head, sep, tail = text.partition("-")
    return head.zfill(4) + sep + tail if sep and len(head) < 4 and head.isdigit() else text


def parse_datetime(value: object) -> datetime.datetime:
    """Accept datetimes, dates and the string formats older panels exported."""
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time())
    if isinstance(value, str):
        text = _fix_year(value.strip())
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(text, fmt)
            except ValueError:
                pass
        try:
            parsed = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            pass
        else:
            return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    raise ValueError(f"Invalid datetime: {value!r}")


def parse_date(value: object) -> datetime.date:
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return parse_datetime(value).date()


def try_parse_datetime(value: object) -> datetime.datetime | None:
    """``None`` for empty or unparseable values (legacy: silently ignored)."""
    if not value:
        return None
    try:
        return parse_datetime(value)
    except ValueError:
        return None


def blank_to_none(parse: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Wrap an enum parser so ``None``/``""`` mean "not given" instead of an error."""

    def _parse(value: Any) -> Any:
        return None if value is None or value == "" else parse(value)

    return _parse
