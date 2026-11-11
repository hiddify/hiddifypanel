"""The free test package people get from the Telegram bot, and the conversations around it.

Each admin has a link to the bot (``/start free_<code>``; the code is a keyed hash of the admin's uuid, so it is the
same after every restart and does not give the uuid away). Whoever opens it sees the admin's package (say 7 days,
500 MB) and asks for it; they are never shown who the admin is (its name stays in the panel):

- approval ``auto``: the account is created at once, for a Telegram account that never had a free test on this panel
  and has no account yet;
- otherwise the request goes to the admin's inbox, and the account is created when the admin approves it.

The package is the admin's own when it has the ``modify_free_package`` capability and defined one, else the nearest
parent's. Everything written to the bot by someone who is not an admin is kept in ``message`` and shown in the inbox
of the admin they talk to; the admin answers from the inbox or from Telegram.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import hmac
import re
import secrets
import uuid as uuid_lib
from dataclasses import dataclass
from typing import Any

from flask import current_app

from hiddifypanel import admin_capabilities as caps
from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, User
from hiddifypanel.models.message import Conversation, FreeStatus, Message, MessageKind, Sender
from hiddifypanel.models.tag import Tag, set_tags

MAX_DAYS = 365
MAX_USAGE_GB = 1000.0
MIN_USAGE_GB = 0.01
MAX_TEXT = 2000
#: A declined request can be sent again after this long.
RETRY_AFTER = datetime.timedelta(days=1)
APPROVALS = ("auto", "manual")
DEFAULT: dict[str, Any] = {"enabled": False, "days": 7, "usage_gb": 0.5, "approval": "manual"}
#: How many packages one admin may keep. Only the default one is offered in the bot; the others wait.
MAX_PACKAGES = 20
_ID = re.compile(r"^[A-Za-z0-9_-]{1,16}$")
#: The id a package stored before there were several gets.
LEGACY_ID = "main"


class FreeTestError(Exception):
    """Why a free test cannot be given now; ``code`` is one of: disabled, no_room, read_only, not_pending."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# --------------------------------------------------------------------------- the package


@dataclass(frozen=True, slots=True)
class Package:
    enabled: bool
    days: int
    usage_gb: float
    approval: str
    #: The admin who defined it (None: nobody did, the defaults).
    owner: AdminUser | None
    #: Its id among the owner's packages ("" for the defaults).
    id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "enabled": self.enabled, "days": self.days, "usage_gb": self.usage_gb, "approval": self.approval}


def clean(value: Any) -> dict[str, Any]:
    """A package as it is stored: every field, inside its limits."""
    src = value if isinstance(value, dict) else {}

    def number(key: str, low: float, high: float) -> float:
        try:
            return min(max(float(src.get(key, DEFAULT[key])), low), high)
        except (TypeError, ValueError):
            return float(DEFAULT[key])

    approval = str(src.get("approval", DEFAULT["approval"]))
    return {
        "enabled": bool(src.get("enabled", DEFAULT["enabled"])),
        "days": int(number("days", 1, MAX_DAYS)),
        "usage_gb": round(number("usage_gb", MIN_USAGE_GB, MAX_USAGE_GB), 3),
        "approval": approval if approval in APPROVALS else DEFAULT["approval"],
    }


def can_define(admin: AdminUser) -> bool:
    return caps.has(admin, caps.MODIFY_FREE_PACKAGE)


def _clean_one(value: Any, taken: set[str]) -> dict[str, Any]:
    """One package with its id: a new or clashing id gets a fresh one."""
    src = value if isinstance(value, dict) else {}
    pid = str(src.get("id") or "")
    while not _ID.match(pid) or pid in taken:
        pid = secrets.token_hex(4)
    taken.add(pid)
    return {"id": pid, **clean(src)}


def clean_set(value: Any) -> dict[str, Any]:
    """The admin's packages as they are stored: ``{"packages": [...], "default": id}``. The default is one of them (the
    first when the given one is gone); no packages means the free test is off. A package stored before there were
    several (a single package dict) becomes the only one, and the default."""
    src = value if isinstance(value, dict) else {}
    if "packages" not in src:
        src = {"packages": [{**src, "id": LEGACY_ID}], "default": LEGACY_ID}
    taken: set[str] = set()
    items = src.get("packages") if isinstance(src.get("packages"), list) else []
    packages = [_clean_one(item, taken) for item in items[:MAX_PACKAGES]]
    ids = [item["id"] for item in packages]
    default = str(src.get("default") or "")
    return {"packages": packages, "default": default if default in ids else (ids[0] if ids else None)}


def own_set(admin: AdminUser) -> dict[str, Any] | None:
    """The admin's own packages, or None when it uses its parent's (or may not define any)."""
    return clean_set(admin.free_package) if isinstance(admin.free_package, dict) and can_define(admin) else None


def _package(item: dict[str, Any], owner: AdminUser) -> Package:
    return Package(**{k: v for k, v in item.items() if k != "id"}, owner=owner, id=item["id"])


def package_of(admin: AdminUser, package_id: str | None = None) -> Package:
    """The package offered for the admin: its own default one when it may define packages and did (``package_id``: that
    one of them instead, while it exists), else the nearest parent's, else the defaults (off)."""
    seen: set[int] = set()
    current: AdminUser | None = admin
    while current is not None and current.id not in seen:  # the owner is its own parent
        seen.add(current.id)
        if (own := own_set(current)) is not None:
            by_id = {item["id"]: item for item in own["packages"]}
            item = by_id.get(package_id or "") or by_id.get(own["default"] or "")
            return _package(item, current) if item else Package(**clean(None), owner=current)
        current = current.parent_admin
    return Package(**clean(None), owner=None)


def set_package(admin: AdminUser, value: Any | None) -> None:
    """``None`` goes back to the parent's package; ``{"packages": [...], "default": id}`` sets them all; a single
    package (the form before there were several) replaces the default one. Not committed."""
    if value is None:
        admin.free_package = None
        return
    if isinstance(value, dict) and "packages" not in value:
        current = own_set(admin) or {"packages": [], "default": None}
        default = current["default"] or LEGACY_ID
        rest = [item for item in current["packages"] if item["id"] != default]
        value = {"packages": [{**value, "id": default}, *rest], "default": default}
    admin.free_package = clean_set(value)


# --------------------------------------------------------------------------- the link


def code_of(admin: AdminUser) -> str:
    """The admin's start code: a keyed hash of its uuid (the panel's secret key), stable between runs."""
    key = str(current_app.config["SECRET_KEY"]).encode()
    digest = hmac.new(key, f"free-test:{admin.uuid}".encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest[:12]).decode().rstrip("=")


def admin_by_code(code: str) -> AdminUser | None:
    for admin in AdminUser.query.filter(AdminUser.deleted.is_(False)).all():
        if hmac.compare_digest(code_of(admin), code):
            return admin
    return None


def start_payload(admin: AdminUser) -> str:
    return f"free_{code_of(admin)}"


# --------------------------------------------------------------------------- conversations


def conversation(admin: AdminUser, telegram_id: int, *, name: str = "", username: str | None = None) -> Conversation:
    """This chat's conversation with ``admin`` (created on first contact); the name follows the Telegram profile."""
    conv = Conversation.query.filter(Conversation.admin_id == admin.id, Conversation.telegram_id == telegram_id).first()
    if conv is None:
        conv = Conversation(admin_id=admin.id, telegram_id=telegram_id, name=name[:128] or str(telegram_id), username=(username or None))
        db.session.add(conv)
    else:
        if name:
            conv.name = name[:128]
        if username:
            conv.username = username[:64]
    conv.last_at = datetime.datetime.now()
    db.session.flush()
    return conv


def current_conversation(telegram_id: int, user: User | None) -> Conversation | None:
    """Who this chat is talking to: the admin whose link it opened last, else the admin of its account."""
    conv = Conversation.query.filter(Conversation.telegram_id == telegram_id).order_by(Conversation.last_at.desc()).first()
    if conv is None and user is not None:
        admin = AdminUser.by_id(user.added_by or 1)
        if admin is not None:
            conv = conversation(admin, telegram_id, name=user.name or "")
            conv.user_uuid = user.uuid
    return conv


def add_message(conv: Conversation, sender: Sender, text: str, kind: MessageKind = MessageKind.text) -> Message:
    """Not committed."""
    message = Message(conversation_id=conv.id, sender=sender.value, kind=kind.value, text=text[:MAX_TEXT])
    db.session.add(message)
    conv.last_text = text[:200] if kind is MessageKind.text else kind.value
    conv.last_sender = sender.value
    conv.last_at = datetime.datetime.now()
    if sender is Sender.user:
        conv.unread = (conv.unread or 0) + 1
    return message


def account_of(conv: Conversation) -> User | None:
    return User.by_uuid(conv.user_uuid) if conv.user_uuid else None


# --------------------------------------------------------------------------- asking and giving


def had_before(telegram_id: int) -> bool:
    """This Telegram account already got a free test from some admin of this panel."""
    return db.session.query(Conversation.id).filter(Conversation.telegram_id == telegram_id, Conversation.free_grants > 0).first() is not None


def has_account(telegram_id: int) -> bool:
    return db.session.query(User.id).filter(User.telegram_id == telegram_id, User.deleted.is_(False)).first() is not None


def is_first_time(conv: Conversation) -> bool:
    return not had_before(conv.telegram_id) and not has_account(conv.telegram_id)


def can_ask(conv: Conversation) -> bool:
    """Nothing waiting, and a declined request is old enough to be sent again."""
    if conv.free_status == FreeStatus.pending:
        return False
    if conv.free_status == FreeStatus.declined and conv.requested_at:
        return datetime.datetime.now() - conv.requested_at >= RETRY_AFTER
    return True


def _has_room(admin: AdminUser) -> bool:
    from hiddifypanel import hutils

    return not hutils.node.is_child() and admin.can_have_more_users()


def ask(conv: Conversation) -> User | None:
    """The chat asks for the free test. The new account when it is given at once, None when the request now waits for
    the admin. Commits."""
    admin = AdminUser.by_id(conv.admin_id)
    package = package_of(admin) if admin else None
    if admin is None or package is None or not package.enabled:
        raise FreeTestError("disabled")
    if not can_ask(conv):
        raise FreeTestError("not_pending")
    conv.requested_at = datetime.datetime.now()
    conv.free_package_id = package.id or None
    add_message(conv, Sender.user, "", MessageKind.request)
    if package.approval == "auto" and is_first_time(conv) and _has_room(admin):
        return grant(conv)
    conv.free_status = FreeStatus.pending.value
    db.session.commit()
    return None


def grant(conv: Conversation) -> User:
    """Create the account with the admin's package, tagged "free" and linked to the chat. Commits and applies."""
    from hiddifypanel import hutils
    from hiddifypanel.panel.commercial.telegrambot import accounts

    admin = AdminUser.by_id(conv.admin_id)
    if admin is None:
        raise FreeTestError("disabled")
    if hutils.node.is_child():
        raise FreeTestError("read_only")
    if not admin.can_have_more_users():
        raise FreeTestError("no_room")
    # The package that was asked for, while the admin still has it; else the one offered now.
    package = package_of(admin, conv.free_package_id)
    comment = "Free test · Telegram " + (f"@{conv.username}" if conv.username else str(conv.telegram_id))
    user = User(uuid=str(uuid_lib.uuid4()), name=(conv.name or str(conv.telegram_id))[:100], package_days=package.days, added_by=admin.id, enable=True, comment=comment)
    user.usage_limit_GB = package.usage_gb
    # One chat is one account: the new one takes the chat.
    User.query.filter(User.telegram_id == conv.telegram_id).update({User.telegram_id: None})
    user.telegram_id = conv.telegram_id
    db.session.add(user)
    if tag := _free_tag():
        set_tags("user", user.uuid, [tag.id])
    conv.user_uuid = user.uuid
    conv.free_status = FreeStatus.approved.value
    conv.free_package_id = package.id or None
    conv.free_grants = (conv.free_grants or 0) + 1
    add_message(conv, Sender.system, f"{package.days}|{package.usage_gb:g}", MessageKind.granted)
    db.session.commit()
    accounts.apply([user])
    return user


def decline(conv: Conversation) -> None:
    if conv.free_status != FreeStatus.pending:
        raise FreeTestError("not_pending")
    conv.free_status = FreeStatus.declined.value
    add_message(conv, Sender.system, "", MessageKind.declined)
    db.session.commit()


def _free_tag() -> Tag | None:
    """The default "free" tag (a super admin may have renamed it: then the last default tag, which it is)."""
    Tag.seed_defaults()
    defaults = Tag.query.filter(Tag.is_default.is_(True)).order_by(Tag.position, Tag.id).all()
    return next((t for t in defaults if t.name.lower() == "free"), defaults[-1] if defaults else None)


def counts(admin: AdminUser) -> dict[str, int]:
    """For the menu badge: unread messages and requests waiting, of this admin's conversations."""
    rows = db.session.query(Conversation.unread, Conversation.free_status).filter(Conversation.admin_id == admin.id).all()
    return {
        "unread": sum(1 for unread, _status in rows if unread),
        "pending": sum(1 for _unread, status in rows if status == FreeStatus.pending),
        #: Conversations that need the admin: unread, or with a request waiting (each counted once).
        "waiting": sum(1 for unread, status in rows if unread or status == FreeStatus.pending),
    }


