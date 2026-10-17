"""Typed values of the ACME package (kept in redis as JSON, returned to the API and the CLI)."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class JobState(StrEnum):
    running = "running"
    done = "done"
    failed = "failed"


@dataclass(slots=True)
class CertJob:
    """The last certificate request of a domain, as the domains page shows it (``CertProgress.vue``)."""

    state: JobState
    started: float | None = None
    finished: float | None = None
    error: str = ""
    rate_limited: bool = False
    ca: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v not in (None, "", False) or k == "state"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CertJob:
        return cls(
            state=JobState(data.get("state", JobState.failed)),
            started=data.get("started"),
            finished=data.get("finished"),
            error=str(data.get("error") or ""),
            rate_limited=bool(data.get("rate_limited")),
            ca=str(data.get("ca") or ""),
        )


@dataclass(slots=True)
class Failure:
    """Failed tries of a host: the scheduled renewal waits longer before each new one, and waits out a rate limit."""

    count: int
    at: float
    error: str
    rate_limited_until: float = 0.0

    @property
    def rate_limited(self) -> bool:
        return self.rate_limited_until > time.time()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Failure:
        return cls(int(data.get("count", 1)), float(data.get("at", 0)), str(data.get("error", "")), float(data.get("rate_limited_until", 0)))


@dataclass(slots=True)
class DomainResult:
    """What happened to one domain."""

    domain_id: int
    domain: str = ""
    ok: bool = False
    changed: bool = False
    error: str = ""
    rate_limited: bool = False
    ca: str = ""


@dataclass(slots=True)
class RenewSummary:
    due: int = 0
    issued: int = 0
    failed: int = 0
    rate_limited: int = 0
    changed: int = 0
    skipped: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    def add(self, res: DomainResult) -> None:
        if res.ok:
            self.issued += 1
        else:
            self.failed += 1
            self.errors[res.domain or str(res.domain_id)] = res.error
        self.rate_limited += res.rate_limited
        self.changed += res.changed

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExportStats:
    """What ``store.export_all`` did to data/cert."""

    written: int = 0
    self_signed: int = 0
    removed: int = 0
