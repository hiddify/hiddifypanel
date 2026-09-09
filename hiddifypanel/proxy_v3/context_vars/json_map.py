from __future__ import annotations

from typing import Any


class JsonMap(dict):
    """JSON object usable as ``obj['k']``, ``obj.k``, and ``obj.get('k')`` in Jinja/Python."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raw = dict(*args, **kwargs)
        super().__init__({key: self._wrap(value) for key, value in raw.items()})

    @classmethod
    def from_any(cls, value: Any) -> JsonMap:
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(value)
        return cls()

    @classmethod
    def _wrap(cls, value: Any) -> Any:
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(value)
        if isinstance(value, list):
            return [cls._wrap(item) for item in value]
        return value

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return self.get(name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        self[name] = self._wrap(value)

    def __delattr__(self, name: str) -> None:
        if name.startswith("_"):
            object.__delattr__(self, name)
            return
        try:
            del self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc
