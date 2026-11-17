"""Settings a person makes in the Telegram bot, by chat (usage alerts on or off...): a small key/value table, so
new settings (and later the shop's) need no new column."""

from __future__ import annotations

from sqlalchemy import BigInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hiddifypanel.database import db


class BotPref(db.Model):  # type: ignore
    __tablename__ = "bot_pref"
    __table_args__ = (UniqueConstraint("chat_id", "key", name="uq_bot_pref"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    key: Mapped[str] = mapped_column(String(32))
    value: Mapped[str] = mapped_column(String(255), default="")

    @classmethod
    def get(cls, chat_id: int, key: str, default: str = "") -> str:
        row = cls.query.filter(cls.chat_id == chat_id, cls.key == key).first()
        return row.value if row else default

    @classmethod
    def put(cls, chat_id: int, key: str, value: str) -> None:
        """Not committed."""
        row = cls.query.filter(cls.chat_id == chat_id, cls.key == key).first()
        if row:
            row.value = value
        else:
            db.session.add(cls(chat_id=chat_id, key=key, value=value))
