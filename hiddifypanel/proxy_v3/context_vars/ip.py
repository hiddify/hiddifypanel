from __future__ import annotations

import ipaddress
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class IPVar(BaseModel):
    """Typed IPv4/IPv6 collections with version filtering."""

    model_config = ConfigDict(extra="ignore")

    ipsv4: set[str] = Field(default_factory=set)
    ipsv6: set[str] = Field(default_factory=set)

    @property
    def ips(self) -> list[str]:
        return list(self.ipsv4) + list(self.ipsv6)

    @classmethod
    def empty(cls) -> IPVar:
        return cls()

    @classmethod
    def from_strings(cls, *values: str | ipaddress.IPv4Address | ipaddress.IPv6Address) -> IPVar:
        v4: set[str] = set()
        v6: set[str] = set()

        def add(ipstr: str | ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
            ip = _normalize_ip(ipstr)
            if not ip:
                return
            bucket = v4 if isinstance(ip, ipaddress.IPv4Address) else v6

            if ip not in bucket:
                bucket.add(str(ip))

        for value in values:
            add(value)
        return cls(ipsv4=v4, ipsv6=v6)

    def merge(self, other: IPVar | list[str]):
        if isinstance(other, list):
            other = IPVar.from_strings(*other)
        self.ipsv4.update(other.ipsv4)
        self.ipsv6.update(other.ipsv6)
        return self


def _normalize_ip(value: str | ipaddress.IPv4Address | ipaddress.IPv6Address | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    if isinstance(value, ipaddress.IPv4Address) or isinstance(value, ipaddress.IPv6Address):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return ipaddress.ip_address(text)
    except ValueError:
        return None
