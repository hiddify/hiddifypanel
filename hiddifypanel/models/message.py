"""Conversations between an admin and the people who write to the Telegram bot, and every message in them.

A conversation is one Telegram chat talking to one admin: it starts when someone opens the admin's free test link
(or a user of the admin writes to the bot). It also keeps where that chat's free test stands.
"""

from __future__ import annotations

import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from strenum import StrEnum

from hiddifypanel.database import db


class FreeStatus(StrEnum):
    none = "none"
    pending = "pending"  # waits for the admin
    approved = "approved"
    declined = "declined"


class Sender(StrEnum):
    user = "user"
    admin = "admin"
    system = "system"  # what happened to the free test, shown inside the thread


class MessageKind(StrEnum):
    text = "text"
    request = "request"  # asked for a free test
    granted = "granted"  # got one (text: "<days>|<usage_gb>")
    declined = "declined"


class Conversation(db.Model):  # type: ignore
    __tablename__ = "conversation"
    __table_args__ = (UniqueConstraint("admin_id", "telegram_id", name="uq_conversation_admin_chat"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("admin_user.id"), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    username: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True)
    #: The account this chat got (or already had) from the admin.
    user_uuid: Mapped[str | None] = mapped_column(String(36), default=None, nullable=True)
    free_status: Mapped[str] = mapped_column(String(10), default=FreeStatus.none.value)
    #: Free tests this chat got from this admin.
    free_grants: Mapped[int] = mapped_column(default=0)
    requested_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, default=None, nullable=True)
    #: Messages the admin has not opened yet.
    unread: Mapped[int] = mapped_column(default=0)
    last_text: Mapped[str] = mapped_column(String(200), default="")
    last_sender: Mapped[str] = mapped_column(String(6), default=Sender.system.value)
    last_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now)

    messages: Mapped[list[Message]] = relationship("Message", backref="conversation", cascade="all, delete-orphan", order_by="Message.id")


class Message(db.Model):  # type: ignore
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversation.id", ondelete="CASCADE"), index=True)
    sender: Mapped[str] = mapped_column(String(6), default=Sender.user.value)
    kind: Mapped[str] = mapped_column(String(10), default=MessageKind.text.value)
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now)
