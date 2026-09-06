from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import joinedload

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
    self_signed: bool = False
    expires_at: datetime | None = None
    issuer: str = ""
    # SNI / server_name for templates that share one cert across many IPs.
    server_name: str = ""

    @property
    def cert_lines(self) -> list[str]:
        return [ln for ln in self.certificate.splitlines() if ln.strip()]

    @property
    def key_lines(self) -> list[str]:
        return [ln for ln in self.private_key.splitlines() if ln.strip()]

    @property
    def fingerprint(self) -> str:
        return self.pinnedPeerCertSha256[0] if self.pinnedPeerCertSha256 else ""

    @property
    def is_usable(self) -> bool:
        return bool(self.cert_lines and self.key_lines)

    @property
    def is_trusted(self) -> bool:
        return bool(self.valid_cert) and not bool(self.self_signed)

    @classmethod
    def empty(cls) -> CertVar:
        return cls()

    @classmethod
    def from_tls_store(cls, row: TlsStore | None, *, verify_peer: bool = True, server_name: str = "") -> CertVar:
        if row is None:
            return cls.empty()
        from hiddifypanel.proxy_v3.tls_store_sync import cert_sha256_hex_from_pem, public_key_sha256_from_pem

        cert_pem = row.certificate or ""
        fp = cert_sha256_hex_from_pem(cert_pem) or (row.fingerprint or "").strip()
        return cls(
            certificate=cert_pem,
            private_key=row.private_key or "",
            verifyPeerCertByName=verify_peer,
            pinnedPeerCertSha256=[fp] if fp else [],
            public_key_sha256=public_key_sha256_from_pem(cert_pem) or "",
            valid_cert=row.valid_cert,
            self_signed=row.self_signed,
            expires_at=row.expires_at,
            issuer=row.issuer or "",
            server_name=server_name,
        )

    @classmethod
    def for_domain(cls, domain_db: Domain, *, verify_peer: bool = True) -> CertVar:
        return cls.from_tls_store(resolve_tls_store(domain_db), verify_peer=verify_peer)


def resolve_tls_store(domain_db: Domain, *, auto_sync: bool = True) -> TlsStore | None:
    """Load or sync the TlsStore row for a domain."""
    linked = domain_db.certificate
    if isinstance(linked, TlsStore):
        return linked
    domain_id = domain_db.id
    if not isinstance(domain_id, int):
        return None
    row = TlsStore.by_domain_id(domain_id)
    if row is not None or not auto_sync:
        return row

    from hiddifypanel.proxy_v3.tls_store_sync import sync_tls_store_for_domain_id

    return sync_tls_store_for_domain_id(domain_id, commit=True)


def _domain_hostname(domain: Domain) -> str:
    name = domain.domain
    return name.strip() if isinstance(name, str) else ""


def _cert_from_store(row: TlsStore) -> CertVar:
    domain = row.domain
    server_name = _domain_hostname(domain) if domain is not None else ""
    trusted = row.valid_cert and not row.self_signed
    return CertVar.from_tls_store(row, verify_peer=trusted, server_name=server_name)


def select_shared_certificate() -> CertVar:
    """Pick one cert for IP-based proxies: valid if possible, otherwise any usable cert.

    Same ORM query for client and server: trusted, then valid, then lowest domain id.
    """
    row: TlsStore | None = (
        TlsStore.query.options(joinedload(TlsStore.domain))
        .filter(TlsStore.certificate != "", TlsStore.private_key != "")
        .order_by(TlsStore.valid_cert.desc(), TlsStore.self_signed.asc(), TlsStore.domain_id.asc())
        .first()
    )
    if row is None:
        return CertVar.empty()
    return _cert_from_store(row)
