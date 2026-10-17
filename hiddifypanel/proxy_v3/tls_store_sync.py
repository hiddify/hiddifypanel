from __future__ import annotations

import functools
import hashlib
import ipaddress
import re
import subprocess
from base64 import b64encode
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from loguru import logger

from hiddifypanel.database import db
from hiddifypanel.models import Child
from hiddifypanel.models.domain import Domain
from hiddifypanel.models.tls_store import TlsStore

# The certificates HAProxy serves: written by the panel from tls_store (hiddifypanel/acme/store.py), the database is the
# source of truth. data/ssl is the folder of acme.sh (before v14): only read once, to import its certificates.
CERT_ROOT = Path("/opt/hiddify-manager/data/cert")
LEGACY_SSL_ROOT = Path("/opt/hiddify-manager/data/ssl")


def domain_file_key(domain: str) -> str:
    return (domain or "").strip().lower()[:64]


def cert_paths_for_domain(domain: str, root: Path | None = None) -> tuple[Path, Path]:
    """``<root>/<name[:64]>.crt`` and ``.crt.key``; ``root`` is data/cert by default."""
    key = domain_file_key(domain)
    base = root or CERT_ROOT
    return base / f"{key}.crt", base / f"{key}.crt.key"


@functools.lru_cache(maxsize=256)
def _leaf_cert(cert_pem: str) -> x509.Certificate | None:
    """First (leaf) certificate of a PEM bundle, parsed in-process (an openssl process per call made every dump slow)."""
    if not cert_pem.strip():
        return None
    try:
        return x509.load_pem_x509_certificate(cert_pem.encode())
    except ValueError:
        return None


def _leaf_cert_der(cert_pem: str) -> bytes | None:
    """First (leaf) certificate in a PEM bundle as DER. Matches ``openssl x509``."""
    cert = _leaf_cert(cert_pem)
    return cert.public_bytes(serialization.Encoding.DER) if cert else None


def cert_sha256_hex_from_pem(cert_pem: str) -> str | None:
    """Xray ``pinnedPeerCertSha256``: SHA-256 of the leaf cert DER, lowercase hex.

    Same value as ``openssl x509 -noout -fingerprint -sha256`` (colons stripped)
    and ``xray tls hash --cert``.
    """
    der = _leaf_cert_der(cert_pem)
    if not der:
        return None
    return hashlib.sha256(der).hexdigest()


def public_key_sha256_from_pem(cert_pem: str) -> str | None:
    """sing-box / hiddify-core ``certificate_public_key_sha256``: SPKI SHA-256, base64. Matches
    ``openssl x509 -pubkey | openssl pkey -pubin -outform der | sha256``."""
    cert = _leaf_cert(cert_pem)
    if cert is None:
        return None
    spki = cert.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return b64encode(hashlib.sha256(spki).digest()).decode()


def _sha256_pin_from_pem(cert_pem: str) -> str | None:
    return cert_sha256_hex_from_pem(cert_pem)


def _openssl_x509(cert_pem: str, *args: str) -> str:
    if not cert_pem.strip():
        return ""
    try:
        proc = subprocess.run(
            ["openssl", "x509", "-noout", *args],
            input=cert_pem,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _dn_value(line: str) -> str:
    if "=" not in line:
        return ""
    return line.split("=", 1)[1].strip()


def _dn_from_pem(cert_pem: str, which: str) -> str:
    line = _openssl_x509(cert_pem, f"-{which}", "-nameopt", "RFC2253")
    if not line:
        line = _openssl_x509(cert_pem, f"-{which}")
    return _dn_value(line)


def _normalize_dn(dn: str) -> str:
    return re.sub(r"[\s/]+", "", dn).lower()


def _parse_issuer_field(issuer_line: str, field: str) -> str:
    pattern = rf"\b{re.escape(field)}\s*=\s*([^,/]+)"
    match = re.search(pattern, issuer_line)
    return match.group(1).strip() if match else ""


def _issuer_from_pem(cert_pem: str) -> str:
    issuer = _dn_from_pem(cert_pem, "issuer")
    if not issuer:
        return ""
    return _parse_issuer_field(issuer, "CN") or _parse_issuer_field(issuer, "O") or issuer


def is_self_signed_pem(cert_pem: str) -> bool:
    issuer = _dn_from_pem(cert_pem, "issuer")
    subject = _dn_from_pem(cert_pem, "subject")
    return bool(issuer and subject and _normalize_dn(issuer) == _normalize_dn(subject))


def _auto_renew(valid_cert: bool, self_signed: bool) -> bool:
    return bool(valid_cert) and not self_signed


def _parse_cert_expiry(cert_pem: str) -> datetime | None:
    if not cert_pem.strip():
        return None
    try:
        proc = subprocess.run(
            ["openssl", "x509", "-enddate", "-noout"],
            input=cert_pem,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return None
        line = proc.stdout.strip()
        if "=" not in line:
            return None
        raw = line.split("=", 1)[1].strip()
        try:
            dt = datetime.strptime(raw, "%b %d %H:%M:%S %Y %Z")
        except ValueError:
            dt = datetime.fromisoformat(raw.replace(" GMT", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC).replace(tzinfo=None)
    except (OSError, ValueError):
        return None


def _private_key_valid(key_pem: str) -> bool:
    if not key_pem.strip():
        return False
    for args in (["openssl", "rsa", "-check", "-noout"], ["openssl", "ec", "-check", "-noout"]):
        proc = subprocess.run(
            args,
            input=key_pem,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return True
    return False


def _subject_alt_names(cert_pem: str) -> list[str]:
    """SAN entries as lowercase names and IP addresses (IPv6 compressed, as domains store it), read in-process."""
    cert = _leaf_cert(cert_pem)
    if cert is None:
        return []
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        return []
    names = [name.lower().rstrip(".") for name in san.get_values_for_type(x509.DNSName)]
    names += [str(ip) for ip in san.get_values_for_type(x509.IPAddress)]
    return names


def _subject_cn(cert_pem: str) -> str:
    subject = _dn_from_pem(cert_pem, "subject")
    return (_parse_issuer_field(subject, "CN") or "").strip().lower().rstrip(".")


def hostname_matches_cert_name(hostname: str, name: str) -> bool:
    """RFC 6125-style match: exact name, or single-label wildcard (*.example.com)."""
    host = (hostname or "").strip().lower().rstrip(".")
    cert_name = (name or "").strip().lower().rstrip(".")
    if not host or not cert_name:
        return False
    if host == cert_name:
        return True
    try:  # an IP address: compare addresses, not text (2001:db8::1 is 2001:DB8:0:0:0:0:0:1)
        return ipaddress.ip_address(host.strip("[]")) == ipaddress.ip_address(cert_name.strip("[]"))
    except ValueError:
        pass
    if cert_name.startswith("*.") and cert_name.count(".") >= 2:
        # *.example.com matches foo.example.com, not example.com or a.b.example.com
        suffix = cert_name[1:]  # .example.com
        return host.endswith(suffix) and host.count(".") == cert_name.count(".")
    return False


def cert_covers_hostname(cert_pem: str, hostname: str) -> bool:
    """True if leaf cert SAN (or CN fallback) covers ``hostname``."""
    host = domain_file_key(hostname)
    if not host or not cert_pem.strip():
        return False
    sans = _subject_alt_names(cert_pem)
    if sans:
        return any(hostname_matches_cert_name(host, n) for n in sans)
    cn = _subject_cn(cert_pem)
    return bool(cn) and hostname_matches_cert_name(host, cn)


def tls_payload(cert_pem: str, key_pem: str, domain: str) -> dict[str, Any] | None:
    """What tls_store keeps of a certificate (PEM chain + key) for ``domain``; None when there is no certificate."""
    if not (cert_pem or "").strip():
        return None
    expires_at = _parse_cert_expiry(cert_pem)
    now = datetime.utcnow()
    key_ok = _private_key_valid(key_pem)
    not_expired = expires_at is None or expires_at > now
    covers_host = cert_covers_hostname(cert_pem, domain)
    valid_cert = bool(key_ok and not_expired and covers_host)
    fingerprint = cert_sha256_hex_from_pem(cert_pem) or ""
    public_key = public_key_sha256_from_pem(cert_pem) or ""
    issuer = _issuer_from_pem(cert_pem)
    self_signed = is_self_signed_pem(cert_pem)
    cert_path, key_path = cert_paths_for_domain(domain)
    return {
        "certificate": cert_pem.strip(),
        "private_key": (key_pem or "").strip(),
        "expires_at": expires_at,
        "valid_cert": valid_cert,
        "self_signed": self_signed,
        "fingerprint": fingerprint,
        "public_key_sha256": public_key,
        "issuer": issuer,
        "auto_renew": _auto_renew(valid_cert, self_signed),
        "tls_cert_path": str(cert_path),
        "tls_key_path": str(key_path),
        "tls_cert_lines": [ln for ln in cert_pem.splitlines() if ln.strip()],
        "tls_key_lines": [ln for ln in (key_pem or "").splitlines() if ln.strip()],
        "tls_pinnedPeerCertSha256": [fingerprint] if fingerprint else [],
        "tls_public_key_sha256": public_key,
    }


def read_tls_files(domain: str, root: Path | None = None) -> dict[str, Any] | None:
    """Load ``<root>/<domain>.crt`` (+ key). Missing domain file → None (no glob fallback)."""
    cert_path, key_path = cert_paths_for_domain(domain, root)
    try:
        if not cert_path.is_file():
            return None
        cert_pem = cert_path.read_text(encoding="utf-8")
        key_pem = key_path.read_text(encoding="utf-8") if key_path.is_file() else ""
    except OSError as e:
        logger.debug(f"TLS files of {domain} in {root} not readable: {e}")
        return None
    return tls_payload(cert_pem, key_pem, domain)


def _hostname_for_domain_db(domain_db: Domain) -> str:
    return domain_file_key(domain_db.domain or "")


def _apply_tls_payload(row: TlsStore, payload: dict[str, Any]) -> None:
    row.certificate = payload["certificate"]
    row.private_key = payload["private_key"]
    row.expires_at = payload.get("expires_at")
    row.valid_cert = bool(payload.get("valid_cert"))
    row.self_signed = bool(payload.get("self_signed"))
    row.fingerprint = payload.get("fingerprint") or ""
    row.issuer = payload.get("issuer") or ""
    row.auto_renew = bool(payload.get("auto_renew"))
    row.last_renewal_error = None
    row.updated_at = datetime.utcnow()


def _import_row(domain_db: Domain, *, commit: bool = True) -> TlsStore | None:
    """Import a certificate file (data/cert, else acme.sh's data/ssl) into tls_store, when it is better than the row's.

    tls_store is the source of truth (the panel issues the certificates and writes the files from it): a file only
    replaces a row with no certificate, or one that expires before the file's. A missing file never clears a row.
    """
    hostname = _hostname_for_domain_db(domain_db)
    if not hostname:
        return None
    row = TlsStore.by_domain_id(domain_db.id)
    payload = read_tls_files(hostname) or read_tls_files(hostname, LEGACY_SSL_ROOT)
    if not payload:
        return row if row and (row.certificate or "").strip() else None
    if row and (row.certificate or "").strip():
        if row.certificate.strip() == payload["certificate"]:
            return row
        better = payload["valid_cert"] and (
            not row.valid_cert
            or (row.self_signed and not payload["self_signed"])
            or (payload["self_signed"] == bool(row.self_signed) and (payload["expires_at"] or datetime.min) > (row.expires_at or datetime.min))
        )
        if not better:
            return row

    if not row:
        row = TlsStore(domain_id=domain_db.id)
        db.session.add(row)

    _apply_tls_payload(row, payload)
    if commit:
        db.session.commit()
    logger.info(
        "TLS store imported a file for domain_id={} host={} issuer={} valid={} self_signed={} expires={}",
        domain_db.id,
        hostname,
        row.issuer,
        row.valid_cert,
        row.self_signed,
        row.expires_at,
    )
    return row


def import_legacy_certificates(child_id: int | None = None, *, commit: bool = True) -> int:
    """Upgrade only: import the certificate files left by acme.sh (data/ssl) or a previous export (data/cert) into
    tls_store. After that tls_store is the only source (the panel issues the certificates and writes the files)."""
    from hiddifypanel.models.domain import Domain

    if child_id is None:
        child_id = Child.current().id
    query = Domain.query.filter(Domain.child_id == child_id).order_by(Domain.id)
    synced = 0
    for domain_db in query.all():
        if _import_row(domain_db, commit=False):
            synced += 1
    if commit and synced:
        db.session.commit()
    return synced
