"""The node's sync page (read only): what it holds now, next to ``sync_status`` (when each kind last came)."""

from __future__ import annotations

import time

from pydantic import BaseModel

from hiddifypanel.models import AdminUser, Child, ChildMode, ConfigEnum, Domain, User, hconfig
from hiddifypanel.models.outbound import Outbound

from . import shared, sync_feed, sync_status

#: "active" checks every user in Python (``User.count_active``); above this many it is left out, to keep the page fast
ACTIVE_COUNT_LIMIT = 5000


class AccountCountsOut(BaseModel):
    total: int
    enabled: int
    deleted: int


class AdminCountsOut(AccountCountsOut):
    by_mode: dict[str, int]


class UserCountsOut(AccountCountsOut):
    #: None above ACTIVE_COUNT_LIMIT users
    active: int | None


class DomainCountsOut(BaseModel):
    total: int
    by_mode: dict[str, int]


class OutboundCountsOut(BaseModel):
    total: int
    enabled: int


class Counts(BaseModel):
    admins: AdminCountsOut
    users: UserCountsOut
    domains: DomainCountsOut
    outbounds: OutboundCountsOut


class FeedCursor(BaseModel):
    parent: str = ""
    #: the last user / admin the feed sent: [modified time, id], None before the first
    u: list[str | int | float] | None = None
    a: list[str | int | float] | None = None


class ParentInfo(BaseModel):
    url: str
    unique_id: str
    cursor: FeedCursor
    #: the parent's clock at the last usage report
    last_users_sync: str


class NodeIds(BaseModel):
    name: str
    unique_id: str


class NodeSyncReport(sync_status.SyncLog):
    is_node: bool
    #: Unix seconds: the page measures "how long ago" with this clock, not the browser's
    server_time: float
    parent: ParentInfo
    node: NodeIds
    counts: Counts
    active_count_limit: int
    #: why the sync log could not be read (the counts are still there)
    error: str = ""
    took_ms: float


def counts() -> Counts:
    admins, users = AdminUser.count_summary(), User.count_summary()
    domains = Domain.count_by_mode(child_id=0)
    outbounds_total, outbounds_enabled = Outbound.count_enabled()
    return Counts(
        admins=AdminCountsOut(**vars(admins), by_mode={str(mode): n for mode, n in AdminUser.count_by_mode().items()}),
        users=UserCountsOut(**vars(users), active=User.count_active(ACTIVE_COUNT_LIMIT)),
        domains=DomainCountsOut(total=sum(domains.values()), by_mode={str(mode): n for mode, n in domains.items()}),
        outbounds=OutboundCountsOut(total=outbounds_total, enabled=outbounds_enabled),
    )


def build() -> NodeSyncReport:
    started = time.perf_counter()
    error = ""
    try:
        log = sync_status.read()
    except Exception as e:  # noqa: BLE001  redis down: the counts still help
        log = sync_status.SyncLog(last={}, last_error={}, log=[], websocket=None)
        error = f"{type(e).__name__}: {e}"
    parent = Child.query.filter(Child.mode == ChildMode.parent).first()
    report_counts = counts()
    return NodeSyncReport(
        **dict(log),
        is_node=shared.is_child(),
        server_time=time.time(),
        parent=ParentInfo(
            url=hconfig(ConfigEnum.parent_panel) or "",
            unique_id=parent.unique_id if parent else "",
            cursor=FeedCursor.model_validate(sync_feed.stored_cursor().to_json()),
            last_users_sync=str(hconfig(ConfigEnum.last_users_sync) or ""),
        ),
        node=NodeIds(name=hconfig(ConfigEnum.node_name) or "", unique_id=hconfig(ConfigEnum.unique_id) or ""),
        counts=report_counts,
        active_count_limit=ACTIVE_COUNT_LIMIT,
        error=error,
        took_ms=round((time.perf_counter() - started) * 1000, 1),
    )
