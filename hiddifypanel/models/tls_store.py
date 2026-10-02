from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hiddifypanel.database import db

if TYPE_CHECKING:
    from hiddifypanel.models.domain import Domain
    from hiddifypanel.models.external_model.network import TlsStoreModel


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

    def to_model(self) -> TlsStoreModel:
        from hiddifypanel.models.external_model.network import TlsStoreModel

        domain_name = ""
        child_unique_id = ""
        if self.domain:
            domain_name = self.domain.domain or ""
            if self.domain.child:
                child_unique_id = self.domain.child.unique_id or ""
        return TlsStoreModel(
            id=self.id,
            domain_id=self.domain_id,
            domain=domain_name,
            child_unique_id=child_unique_id,
            certificate=self.certificate or "",
            private_key=self.private_key or "",
            expires_at=self.expires_at,
            valid_cert=bool(self.valid_cert),
            self_signed=bool(self.self_signed),
            issuer=self.issuer or "",
            fingerprint=self.fingerprint or "",
            auto_renew=bool(self.auto_renew),
            last_renewal_error=self.last_renewal_error or "",
            updated_at=self.updated_at,
        )

    def to_dict(self, *, include_private_key: bool = False) -> dict[str, Any]:
        return self.to_model().to_dict(exclude=None if include_private_key else {"private_key"})

    @classmethod
    def by_domain_id(cls, domain_id: int | None) -> TlsStore | None:
        if not domain_id:
            return None
        return cls.query.filter(cls.domain_id == int(domain_id)).first()

    @classmethod
    def add_or_update(cls, commit: bool = True, **data) -> TlsStore | None:
        from hiddifypanel.models.external_model.network import TlsStoreModel

        return cls.upsert(TlsStoreModel.coerce(data), commit=commit)

    @classmethod
    def upsert(cls, data: TlsStoreModel, *, commit: bool = True, force_child_unique_id: str | None = None) -> TlsStore | None:
        """Attach to the domain by ``domain_id``, else by name (preferring the row's child)."""
        from hiddifypanel.models.domain import Domain
        from hiddifypanel.panel import hiddify

        domain_row = None
        if data.domain_id:
            domain_row = Domain.query.filter(Domain.id == data.domain_id).first()
        if not domain_row:
            if not data.domain_key:
                return None
            force = force_child_unique_id if force_child_unique_id is not None else data.force_child_unique_id
            child_id = hiddify.child_id_from_row({"child_unique_id": data.child_unique_id}, force)
            domain_row = Domain.query.filter(Domain.domain == data.domain_key, Domain.child_id == child_id).first()
            if not domain_row:
                domain_row = Domain.query.filter(Domain.domain == data.domain_key).first()
        if not domain_row:
            return None

        row = cls.by_domain_id(domain_row.id)
        if not row:
            row = cls(domain_id=domain_row.id)
            db.session.add(row)

        if data.has("certificate"):
            row.certificate = data.certificate or ""
        if data.has("private_key"):
            row.private_key = data.private_key or ""
        if data.has("valid_cert"):
            row.valid_cert = bool(data.valid_cert)
        if data.has("self_signed"):
            row.self_signed = bool(data.self_signed)
        if data.has("issuer"):
            row.issuer = data.issuer or ""
        if data.has("fingerprint"):
            row.fingerprint = data.fingerprint or ""
        if data.has("auto_renew"):
            row.auto_renew = bool(data.auto_renew)
        if data.has("last_renewal_error"):
            row.last_renewal_error = data.last_renewal_error or None
        if data.expires_at is not None:
            row.expires_at = data.expires_at
        if data.updated_at is not None:
            row.updated_at = data.updated_at
        if commit:
            db.session.commit()
        return row

    @classmethod
    def bulk_register(cls, rows, commit: bool = True, force_child_unique_id: str | None = None) -> None:
        from hiddifypanel.models.external_model import as_row
        from hiddifypanel.models.external_model.network import TlsStoreModel

        # Row ids differ between panels: drop domain_id so the domain is always resolved by name.
        for data in TlsStoreModel.coerce_many({**as_row(item), "domain_id": None} for item in rows):
            cls.upsert(data, commit=False, force_child_unique_id=force_child_unique_id)
        if commit:
            db.session.commit()
