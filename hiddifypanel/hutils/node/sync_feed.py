"""The users and admins of the parent in the order they changed: what a node has not had yet (sent over its WebSocket,
see ws_server.py and ws_client.py).

A node keeps a cursor per table: the ``(last_modified_time, id)`` of the last row it got. The parent sends the rows after it,
in that order, a batch at a time; a deleted account is a row like the others (``deleted``), so deletions travel too.

``last_modified_time`` is set when a change is written, not when it is committed: a change that takes a few seconds to commit
can show up with a time the node has already gone past. So the parent also looks ``OVERLAP`` back for rows it has not sent
(only ids and times are read for that; it remembers what it sent within that window). After a reconnect the rows of the last
``OVERLAP`` are sent again: a node writes a row it already has without harm.
"""

from __future__ import annotations

import datetime
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field

from loguru import logger
from sqlalchemy import and_, or_

from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, Child, ChildMode, ConfigEnum, User, hconfig, set_hconfig
from hiddifypanel.models.base_account import BaseAccount

from .ws_proto import ChangesMessage, CursorJson, InventoryMessage, Json, Row

OVERLAP = datetime.timedelta(minutes=2)
BATCH = 1000

type Position = tuple[datetime.datetime, int]


def _to_json(pos: Position | None) -> list[Json] | None:
    return None if pos is None else [pos[0].isoformat(), pos[1]]


def _from_json(raw: object) -> Position | None:
    if not isinstance(raw, list) or len(raw) != 2:
        return None
    try:
        return datetime.datetime.fromisoformat(str(raw[0])), int(raw[1])
    except (TypeError, ValueError):
        return None


@dataclass
class Cursor:
    """Where a node is in the feed of one parent (``parent`` is that parent's unique id)."""

    parent: str = ""
    users: Position | None = None
    admins: Position | None = None

    def to_json(self) -> CursorJson:
        return CursorJson(parent=self.parent, u=_to_json(self.users), a=_to_json(self.admins))

    @classmethod
    def from_json(cls, raw: object) -> Cursor:
        if not isinstance(raw, dict):
            return cls()
        return cls(parent=str(raw.get("parent") or ""), users=_from_json(raw.get("u")), admins=_from_json(raw.get("a")))


# --------------------------------------------------------------------------- parent: what to send


def _user_row(u: BaseAccount) -> Row:
    assert isinstance(u, User)
    return u.to_schema().model_dump(mode="json")


def _admin_row(a: BaseAccount) -> Row:
    assert isinstance(a, AdminUser)
    return json.loads(json.dumps(a.to_dict(), default=str))  # carries ``deleted`` (AdminSchema does not); plain JSON values


@dataclass
class _TableFeed:
    model: type[BaseAccount]
    dump: Callable[[BaseAccount], Row]
    pos: Position | None
    #: id -> last_modified_time of the rows sent within OVERLAP of ``pos``
    sent: dict[int, datetime.datetime] = field(default_factory=dict)
    #: uuids the node asked for again (it did not have them, see ``reconcile``)
    resend: set[str] = field(default_factory=set)

    def next_rows(self, limit: int) -> tuple[list[Row], bool]:
        """Rows asked for again (``resend``), rows that changed late (behind ``pos``, not sent yet), then rows after ``pos``;
        and whether more are waiting."""
        late = self._resend_rows(limit) + self._late_rows(limit)
        limit = max(1, limit - len(late))
        m = self.model
        query = m.query_with_deleted()
        if self.pos is not None:
            t, i = self.pos
            query = query.filter(m.last_modified_time >= t, or_(m.last_modified_time > t, and_(m.last_modified_time == t, m.id > i)))
        rows = query.order_by(m.last_modified_time, m.id).limit(limit + 1).all()
        more = len(rows) > limit
        rows = rows[:limit]
        if rows:
            self.pos = (rows[-1].last_modified_time, rows[-1].id)
        out = [self.dump(r) for r in [*late, *rows]]
        for r in [*late, *rows]:
            self.sent[r.id] = r.last_modified_time
        self._forget_old()
        return out, more

    def _late_rows(self, limit: int) -> list[BaseAccount]:
        if self.pos is None:
            return []
        m = self.model
        t, i = self.pos
        seen = db.session.query(m.id, m.last_modified_time).execution_options(include_deleted=True)
        seen = seen.filter(m.last_modified_time >= t - OVERLAP, or_(m.last_modified_time < t, and_(m.last_modified_time == t, m.id <= i)))
        ids = [rid for rid, lmt in seen.all() if self.sent.get(rid) != lmt][:limit]  # the rest come with the next batch
        if not ids:
            return []
        logger.debug(f"node feed: {len(ids)} {m.__tablename__} rows changed behind the cursor")
        return m.query_with_deleted().filter(m.id.in_(ids)).order_by(m.last_modified_time, m.id).all()

    def _resend_rows(self, limit: int) -> list[BaseAccount]:
        if not self.resend:
            return []
        wanted = sorted(self.resend)[:limit]
        self.resend.difference_update(wanted)
        m = self.model
        return m.query_with_deleted().filter(m.uuid.in_(wanted)).all()

    def live_uuids(self) -> list[str]:
        m = self.model
        return sorted(str(u) for (u,) in db.session.query(m.uuid).filter(m.deleted.isnot(True)).execution_options(include_deleted=True).all())

    def _forget_old(self) -> None:
        if self.pos is None:
            return
        oldest = self.pos[0] - OVERLAP
        for rid in [rid for rid, lmt in self.sent.items() if lmt < oldest]:
            del self.sent[rid]


class Feed:
    """What one connected node still needs; one per connection (it remembers what it sent)."""

    def __init__(self, cursor: Cursor, parent_unique_id: str):
        same_parent = cursor.parent == parent_unique_id
        self.parent = parent_unique_id
        self.admins = _TableFeed(AdminUser, _admin_row, cursor.admins if same_parent else None)
        self.users = _TableFeed(User, _user_row, cursor.users if same_parent else None)
        self.outbounds_hash = ""

    def cursor(self) -> Cursor:
        return Cursor(parent=self.parent, users=self.users.pos, admins=self.admins.pos)

    def inventory(self) -> InventoryMessage:
        """What accounts are there (not deleted): the admins (few), and a digest of the users (the node asks for their list
        when its own differs). See ``reconcile``."""
        return InventoryMessage(type="inventory", admins=self.admins.live_uuids(), users_digest=uuids_digest(self.users.live_uuids()))

    def user_list(self) -> list[str]:
        return self.users.live_uuids()

    def ask_again(self, users: list[str], admins: list[str]) -> None:
        self.users.resend.update(users)
        self.admins.resend.update(admins)

    def next_batch(self, limit: int = BATCH) -> ChangesMessage | None:
        """The next ``changes`` message, or None when the node has everything. Admins come first: a user names its admin."""
        admins, more_admins = self.admins.next_rows(limit)
        users: list[Row] = []
        more_users = False
        if not more_admins:
            users, more_users = self.users.next_rows(max(1, limit - len(admins)))
        outbounds = self._outbounds_if_changed()
        if not admins and not users and outbounds is None:
            return None
        return ChangesMessage(type="changes", admins=admins, users=users, outbounds=outbounds, cursor=self.cursor().to_json(), more=more_admins or more_users)

    def _outbounds_if_changed(self) -> list[Row] | None:
        from hiddifypanel.proxy_v3 import outbounds as ob

        rows: list[Row] = [o.model_dump(mode="json") for o in ob.export_rows()]
        digest = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
        if digest == self.outbounds_hash:
            return None
        self.outbounds_hash = digest
        return rows


def uuids_digest(uuids: list[str]) -> str:
    """Of sorted uuids: the same on both sides when they have the same accounts."""
    h = hashlib.sha256()
    for uuid in uuids:
        h.update(uuid.encode() + b"\n")
    return h.hexdigest()


# --------------------------------------------------------------------------- node: what came


def stored_cursor() -> Cursor:
    """This node's cursor, if it belongs to the parent it has now (a new parent starts from the beginning)."""
    try:
        cursor = Cursor.from_json(json.loads(hconfig(ConfigEnum.parent_sync_cursor) or "{}"))
    except ValueError:
        return Cursor()
    parent = Child.query.filter(Child.mode == ChildMode.parent).first()
    return cursor if parent is not None and cursor.parent == parent.unique_id else Cursor()


def reset_cursor() -> None:
    set_hconfig(ConfigEnum.parent_sync_cursor, "")


@dataclass
class Applied:
    users: int
    admins: int
    #: some user became active or inactive: the proxy cores need the users again
    users_changed: bool
    outbounds_changed: bool


def local_user_uuids() -> list[str]:
    return sorted(str(u) for (u,) in db.session.query(User.uuid).filter(User.deleted.isnot(True)).all())


@dataclass(frozen=True)
class Reconciled:
    removed: int
    #: uuids the parent has and this node does not: asked for again
    missing: list[str]


def _reconcile[A: BaseAccount](model: type[A], local: list[str], parent: list[str]) -> Reconciled:
    keep = set(parent)
    gone = [u for u in local if u not in keep]
    removed = 0
    try:
        for i in range(0, len(gone), 500):
            for row in model.query.filter(model.uuid.in_(gone[i : i + 500])).all():
                row.removed_by_sync()  # never the owner of this node (AdminUser.removed_by_sync)
                removed += int(bool(row.deleted))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    have = set(local)
    return Reconciled(removed=removed, missing=[u for u in parent if u not in have])


def reconcile_admins(parent_admins: list[str]) -> Reconciled:
    """Make this node's admins the parent's: what the parent no longer has is deleted here (a uuid changed there, a row the feed
    could not send), what it has and this node lacks is asked for again."""
    local = sorted(str(u) for (u,) in db.session.query(AdminUser.uuid).filter(AdminUser.deleted.isnot(True)).all())
    return _reconcile(AdminUser, local, parent_admins)


def reconcile_users(parent_users: list[str]) -> Reconciled:
    """As ``reconcile_admins``, for users (asked for when ``uuids_digest`` of the two sides differ)."""
    return _reconcile(User, local_user_uuids(), parent_users)


def local_users_digest() -> str:
    return uuids_digest(local_user_uuids())


def _uuid(row: Row, key: str = "uuid") -> str | None:
    value = row.get(key)
    return str(value) if value else None


def apply_batch(batch: ChangesMessage) -> Applied:
    """Write a ``changes`` message of the parent (checked with ``ws_proto.parse_changes``) and its cursor, in one commit."""
    from hiddifypanel.models.external_model.outbound import OutboundModel
    from hiddifypanel.proxy_v3 import outbounds as ob

    users, admins, outbounds = batch["users"], batch["admins"], batch["outbounds"]
    user_uuids = [u for u in (_uuid(row) for row in users) if u]
    admin_uuids = [_uuid(a) for a in admins] + [_uuid(u, "added_by_uuid") for u in users]
    try:
        with AdminUser.prefetch(admin_uuids), User.prefetch(user_uuids) as existing:
            active_before = {uuid: u.is_active for uuid, u in existing.items()}
            outbounds_changed = ob.import_rows([OutboundModel.model_validate(o) for o in outbounds]) if outbounds is not None else False
            if admins:
                # Every admin first, then who is under whom: a sub-admin may come before its parent in the batch.
                AdminUser.bulk_register([{k: v for k, v in a.items() if k != "parent_admin_uuid"} for a in admins], commit=False)
                AdminUser.bulk_register(admins, commit=False)
            if users:
                User.bulk_register(users, commit=False)
            db.session.flush()
            after = {uuid: User.by_uuid(uuid, include_deleted=True) for uuid in user_uuids}
            users_changed = any((row is not None and row.is_active) != active_before.get(uuid, False) for uuid, row in after.items())
        set_hconfig(ConfigEnum.parent_sync_cursor, json.dumps(batch["cursor"]), commit=False)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return Applied(users=len(users), admins=len(admins), users_changed=users_changed, outbounds_changed=outbounds_changed)
