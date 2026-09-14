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
        domain_name = ""
        child_unique_id = ""
        if self.domain:
            domain_name = self.domain.domain or ""
            if self.domain.child:
                child_unique_id = self.domain.child.unique_id or ""
        data: dict[str, Any] = {
            "id": self.id,
            "domain_id": self.domain_id,
            "domain": domain_name,
            "child_unique_id": child_unique_id,
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

    @classmethod
    def add_or_update(cls, commit: bool = True, **data) -> TlsStore | None:
        from hiddifypanel.models.domain import Domain
        from hiddifypanel.panel import hiddify

        domain_id = data.get("domain_id")
        domain_row = None
        if domain_id:
            domain_row = Domain.query.filter(Domain.id == int(domain_id)).first()
        if not domain_row:
            domain_name = str(data.get("domain") or "").strip().lower()
            if not domain_name:
                return None
            child_id = hiddify.child_id_from_row(data, data.get("force_child_unique_id"))
            domain_row = Domain.query.filter(Domain.domain == domain_name, Domain.child_id == child_id).first()
            if not domain_row:
                domain_row = Domain.query.filter(Domain.domain == domain_name).first()
        if not domain_row:
            return None

        row = cls.by_domain_id(domain_row.id)
        if not row:
            row = cls(domain_id=domain_row.id)
            db.session.add(row)

        if "certificate" in data:
            row.certificate = data.get("certificate") or ""
        if "private_key" in data:
            row.private_key = data.get("private_key") or ""
        if "valid_cert" in data:
            row.valid_cert = bool(data["valid_cert"])
        if "self_signed" in data:
            row.self_signed = bool(data["self_signed"])
        if "issuer" in data:
            row.issuer = data.get("issuer") or ""
        if "fingerprint" in data:
            row.fingerprint = data.get("fingerprint") or ""
        if "auto_renew" in data:
            row.auto_renew = bool(data["auto_renew"])
        if "last_renewal_error" in data:
            row.last_renewal_error = data.get("last_renewal_error") or None
        for field in ("expires_at", "updated_at"):
            if field not in data or not data[field]:
                continue
            raw = data[field]
            if isinstance(raw, datetime):
                setattr(row, field, raw)
            elif isinstance(raw, str):
                try:
                    setattr(row, field, datetime.fromisoformat(raw.replace("Z", "+00:00")))
                except ValueError:
                    pass
        if commit:
            db.session.commit()
        return row

    @classmethod
    def bulk_register(cls, rows, commit: bool = True, force_child_unique_id: str | None = None) -> None:
        for item in rows:
            row = item.model_dump() if hasattr(item, "model_dump") else dict(item)
            payload = {k: v for k, v in row.items() if k not in {"id", "domain_id"}}
            if force_child_unique_id is not None:
                payload["force_child_unique_id"] = force_child_unique_id
            cls.add_or_update(commit=False, **payload)
        if commit:
            db.session.commit()
