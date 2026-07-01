from __future__ import annotations

from typing import Any


class TemplateVersion:
    """Semantic version for Jinja comparisons: platform.app.version < \"1.2.3\"."""

    def __init__(self, version: str | list | tuple | None = None):
        if isinstance(version, (list, tuple)):
            parts = [str(x) for x in version if x is not None and str(x) != '']
            version = '.'.join(parts)
        self._version = str(version or '0')

    def _other_str(self, other: Any) -> str:
        if isinstance(other, TemplateVersion):
            return other._version
        return str(other)

    def _compare(self, other: Any) -> int:
        from hiddifypanel import hutils

        return hutils.utils.compare_versions(self._version, self._other_str(other))

    def __str__(self) -> str:
        return self._version

    def __repr__(self) -> str:
        return f'TemplateVersion({self._version!r})'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (TemplateVersion, str)):
            return NotImplemented
        return self._compare(other) == 0

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, (TemplateVersion, str)):
            return NotImplemented
        return self._compare(other) != 0

    def __lt__(self, other: Any) -> bool:
        return self._compare(other) == -1

    def __le__(self, other: Any) -> bool:
        return self._compare(other) in (-1, 0)

    def __gt__(self, other: Any) -> bool:
        return self._compare(other) == 1

    def __ge__(self, other: Any) -> bool:
        return self._compare(other) in (0, 1)


class PlatformPart:
    """Named platform facet with comparable version (platform.app.version)."""

    __slots__ = ('name', 'version')

    def __init__(self, name: str, version: str | list | tuple | TemplateVersion | None = None):
        self.name = name or ''
        self.version = version if isinstance(version, TemplateVersion) else TemplateVersion(version)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.name == other
        return NotImplemented

    def __str__(self) -> str:
        return self.name
