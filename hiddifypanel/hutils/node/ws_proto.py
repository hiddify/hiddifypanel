"""Messages on the WebSocket between a node and its parent: JSON objects with a ``type``, sent as zlib-compressed binary frames
(the users' JSON is mostly field names: it shrinks several times; nothing between the panels has to agree on an extension).

node → parent: ``hello`` {cursor, version}, ``ack`` {cursor}, ``ping`` (every ``HEARTBEAT`` seconds),
               ``inventory_please``, ``users_list_please``, ``resend`` {users, admins}
parent → node: ``welcome`` {parent_unique_id, parent_hosts}, ``changes`` {admins, users, outbounds, cursor, more},
               ``inventory`` {admins, users_digest}, ``users_list`` {users}
"""

from __future__ import annotations

import json
import zlib
from typing import Any, Literal, TypedDict

VERSION = 1
#: The node says something at least this often (seconds); the parent drops a node it has not heard from for ``SILENT``.
HEARTBEAT = 25
SILENT = 90
#: How often the parent sends the inventory (seconds).
RECONCILE_EVERY = 300
#: After the admin proxy path (routes in hiddifypanel/asgi.py): the WebSocket, the streamed response, and ``<NODE_BASE><session>/``
#: for what the node says on a stream.
PATH = "api/v2/node/ws/"
STREAM_PATH = "api/v2/node/stream/"
NODE_BASE = "api/v2/node/"
MAX_MESSAGE = 64 * 1024 * 1024

#: Close codes (4000-4999 are the application's)
CLOSE_UNAUTHORIZED = 4403
CLOSE_NOT_FOUND = 4404
CLOSE_PROTOCOL = 4400


class ProtocolError(Exception):
    pass


type Json = None | bool | int | float | str | list[Json] | dict[str, Json]
#: A user or an admin as it travels (the JSON of UserSchema / AdminModel).
type Row = dict[str, Json]


class CursorJson(TypedDict):
    """Where a node is in its parent's change feed: per table the (last_modified_time, id) of the last row it got."""

    parent: str
    u: list[Json] | None
    a: list[Json] | None


class InventoryMessage(TypedDict):
    """parent → node, after catching up and every few minutes: which accounts are there. The node deletes what is gone, asks for
    what it lacks (``resend``), and asks for the users' list (``users_list``) when the digest of its own differs."""

    type: Literal["inventory"]
    admins: list[str]
    users_digest: str


class ChangesMessage(TypedDict):
    type: Literal["changes"]
    admins: list[Row]
    users: list[Row]
    #: All outbounds of the parent, when they changed since the last message (None: unchanged).
    outbounds: list[Row] | None
    cursor: CursorJson
    #: More rows wait: the next message follows the ack.
    more: bool


def encode(message: dict[str, Any]) -> bytes:
    return zlib.compress(json.dumps(message, separators=(",", ":"), default=str).encode(), 6)


def decode(frame: bytes | str) -> dict[str, Any]:
    try:
        raw = frame.encode() if isinstance(frame, str) else zlib.decompress(frame)
        message = json.loads(raw)
    except (zlib.error, ValueError) as e:
        raise ProtocolError(f"not a message: {e}") from e
    if not isinstance(message, dict) or not isinstance(message.get("type"), str):
        raise ProtocolError("a message is an object with a type")
    return message


def _rows(raw: object, name: str) -> list[Row]:
    if not isinstance(raw, list) or not all(isinstance(r, dict) for r in raw):
        raise ProtocolError(f"changes.{name} is not a list of objects")
    return raw


def parse_changes(message: dict[str, Any]) -> ChangesMessage:
    """A ``changes`` message from the other side, checked before anything of it is written."""
    cursor = message.get("cursor")
    if not isinstance(cursor, dict) or not isinstance(cursor.get("parent"), str):
        raise ProtocolError("changes.cursor is missing")
    outbounds = message.get("outbounds")
    return ChangesMessage(
        type="changes",
        admins=_rows(message.get("admins", []), "admins"),
        users=_rows(message.get("users", []), "users"),
        outbounds=None if outbounds is None else _rows(outbounds, "outbounds"),
        cursor=CursorJson(parent=cursor["parent"], u=cursor.get("u"), a=cursor.get("a")),
        more=bool(message.get("more")),
    )


def str_list(raw: object, name: str) -> list[str]:
    if not isinstance(raw, list) or not all(isinstance(u, str) for u in raw):
        raise ProtocolError(f"{name} is not a list of strings")
    return raw


def parse_inventory(message: dict[str, Any]) -> InventoryMessage:
    digest = message.get("users_digest")
    if not isinstance(digest, str):
        raise ProtocolError("inventory.users_digest is missing")
    return InventoryMessage(type="inventory", admins=str_list(message.get("admins", []), "inventory.admins"), users_digest=digest)

