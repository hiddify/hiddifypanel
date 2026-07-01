from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from hiddifypanel.models.domain import Domain
from hiddifypanel.models.tls_store import TlsStore


class CertVar(BaseModel):
    model_config = ConfigDict(extra="ignore")

    certificate: str = ""
    private_key: str = ""
    verifyPeerCertByName: bool = True
    pinnedPeerCertSha256: list[str] = Field(default_factory=list)
    public_key_sha256: str = ""
    valid_cert: bool = False
    expires_at: datetime | None = None
    issuer: str = ""

    @property
    def cert_lines(self) -> list[str]:
        return [ln for ln in self.certificate.splitlines() if ln.strip()]

    @property
    def key_lines(self) -> list[str]:
        return [ln for ln in self.private_key.splitlines() if ln.strip()]

    @property
    def fingerprint(self) -> str:
        return self.public_key_sha256

    @classmethod
    def empty(cls) -> CertVar:
        return cls()

    @classmethod
    def from_tls_store(cls, row: TlsStore | None, *, verify_peer: bool = True) -> CertVar:
        if row is None:
            return cls.empty()
        fp = str(row.fingerprint or "").strip()
        return cls(
            certificate=str(row.certificate),
            private_key=str(row.private_key),
            verifyPeerCertByName=verify_peer,
            pinnedPeerCertSha256=[fp] if fp else [],
            public_key_sha256=fp,
            valid_cert=bool(row.valid_cert),
            expires_at=row.expires_at,
            issuer=str(row.issuer),
        )

    @classmethod
    def for_domain(cls, domain_db: Domain, *, verify_peer: bool = True) -> CertVar:

        return cls.from_tls_store(resolve_tls_store(domain_db), verify_peer=verify_peer)


def resolve_tls_store(domain_db: Domain, *, auto_sync: bool = True) -> TlsStore | None:
    """Load or sync the TlsStore row for a domain."""
    row = domain_db.certificate or TlsStore.by_domain_id(domain_db.id)
    if row is not None or not auto_sync:
        return row

    from hiddifypanel.proxy_v3.tls_store_sync import sync_tls_store_for_domain_id

    return sync_tls_store_for_domain_id(domain_db.id, commit=True)
