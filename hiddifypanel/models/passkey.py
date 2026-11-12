"""An admin's passkey (WebAuthn credential): the public key the panel checks a passkey sign-in with.

The private key never leaves the admin's device (or password manager); the panel keeps only the public key.
How passkeys are made and checked is in ``hiddifypanel/passkeys.py``.
"""

from __future__ import annotations

import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hiddifypanel.database import db


class AdminPasskey(db.Model):
    __tablename__ = "admin_passkey"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("admin_user.id", ondelete="CASCADE"), index=True)
    #: The credential ID, base64url (no padding), as the browser gives it.
    credential_id: Mapped[str] = mapped_column(String(512), unique=True)
    #: The public key, base64 of its DER SubjectPublicKeyInfo, and its COSE algorithm (-7 ES256, -8 EdDSA, -257 RS256).
    public_key: Mapped[str] = mapped_column(Text)
    alg: Mapped[int] = mapped_column(Integer)
    sign_count: Mapped[int] = mapped_column(BigInteger, default=0)
    #: The domain the passkey belongs to (WebAuthn RP ID).
    rp_id: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now)
    last_used_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, default=None)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.rp_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }
