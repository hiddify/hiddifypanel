from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hiddifypanel.database import db

if TYPE_CHECKING:
    from hiddifypanel.models.domain import Domain


class TlsStore(db.Model):  # type: ignore
    """TLS certificate material linked to a Domain row."""

    __tablename__ = "tls_store"
    __table_args__ = (UniqueConstraint("domain_id", name="uq_tls_store_domain_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domain.id", ondelete="CASCADE"), unique=True)
    certificate: Mapped[str] = mapped_column(Text, default="")
    private_key: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    valid_cert: Mapped[bool] = mapped_column(default=False)
    self_signed: Mapped[bool] = mapped_column(default=False)
    issuer: Mapped[str] = mapped_column(String(500), default="")
    fingerprint: Mapped[str] = mapped_column(String(128), default="")
    auto_renew: Mapped[bool] = mapped_column(default=True)
    last_renewal_error: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    domain: Mapped[Domain] = relationship("Domain", back_populates="certificate")

    def to_dict(self, *, include_private_key: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "domain_id": self.domain_id,
            "certificate": self.certificate or "",
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "valid_cert": bool(self.valid_cert),
            "self_signed": bool(self.self_signed),
            "issuer": self.issuer or "",
            "fingerprint": self.fingerprint or "",
            "auto_renew": bool(self.auto_renew),
            "last_renewal_error": self.last_renewal_error or "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_private_key:
            data["private_key"] = self.private_key or ""
        return data

    @classmethod
    def by_domain_id(cls, domain_id: int | None) -> TlsStore | None:
        if not domain_id:
            return None
        return cls.query.filter(cls.domain_id == int(domain_id)).first()
