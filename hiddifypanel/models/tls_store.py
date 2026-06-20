from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from hiddifypanel.database import db


class TlsStore(db.Model):  # type: ignore
    """TLS certificate material linked to a Domain row."""

    __tablename__ = 'tls_store'
    __table_args__ = (
        UniqueConstraint('domain_id', name='uq_tls_store_domain_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain_id = Column(Integer, ForeignKey('domain.id', ondelete='CASCADE'), unique=True, nullable=False)
    certificate = Column(Text, nullable=False, default='')
    private_key = Column(Text, nullable=False, default='')
    expires_at = Column(DateTime, nullable=True)
    valid_cert = Column(Boolean, default=False, nullable=False)
    issuer = Column(String(500), default='')
    fingerprint = Column(String(128), default='')
    auto_renew = Column(Boolean, default=True, nullable=False)
    last_renewal_error = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    domain = relationship('Domain', back_populates='certificate')

    def to_dict(self, *, include_private_key: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            'id': self.id,
            'domain_id': self.domain_id,
            'certificate': self.certificate or '',
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'valid_cert': bool(self.valid_cert),
            'issuer': self.issuer or '',
            'fingerprint': self.fingerprint or '',
            'auto_renew': bool(self.auto_renew),
            'last_renewal_error': self.last_renewal_error or '',
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_private_key:
            data['private_key'] = self.private_key or ''
        return data

    @classmethod
    def by_domain_id(cls, domain_id: int | None) -> TlsStore | None:
        if not domain_id:
            return None
        return cls.query.filter(cls.domain_id == int(domain_id)).first()
