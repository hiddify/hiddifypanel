from __future__ import annotations

import hashlib
import re
import subprocess
from base64 import b64encode
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from hiddifypanel.database import db
from hiddifypanel.models.tls_store import TlsStore

SSL_ROOT = Path('/opt/hiddify-manager/ssl')


def domain_file_key(domain: str) -> str:
    return (domain or '').strip().lower()[:64]


def cert_paths_for_domain(domain: str) -> tuple[Path, Path]:
    key = domain_file_key(domain)
    return SSL_ROOT / f'{key}.crt', SSL_ROOT / f'{key}.crt.key'


def _sha256_pin_from_pem(cert_pem: str) -> str | None:
    if not cert_pem.strip():
        return None
    try:
        proc = subprocess.run(
            ['openssl', 'x509', '-pubkey', '-noout'],
            input=cert_pem,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        proc2 = subprocess.run(
            ['openssl', 'pkey', '-pubin', '-outform', 'der'],
            input=proc.stdout.encode(),
            capture_output=True,
            check=False,
        )
        if proc2.returncode != 0:
            return None
        return b64encode(hashlib.sha256(proc2.stdout).digest()).decode()
    except OSError:
        return None


def _parse_issuer_field(issuer_line: str, field: str) -> str:
    pattern = rf'\b{re.escape(field)}\s*=\s*([^,/]+)'
    match = re.search(pattern, issuer_line)
    return match.group(1).strip() if match else ''


def _issuer_from_pem(cert_pem: str) -> str:
    if not cert_pem.strip():
        return ''
    try:
        proc = subprocess.run(
            ['openssl', 'x509', '-issuer', '-noout'],
            input=cert_pem,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return ''
        line = proc.stdout.strip()
        if '=' not in line:
            return ''
        issuer = line.split('=', 1)[1].strip()
        return _parse_issuer_field(issuer, 'CN') or _parse_issuer_field(issuer, 'O') or issuer
    except OSError:
        return ''


def _auto_renew_from_issuer(issuer: str, valid_cert: bool) -> bool:
    if not valid_cert:
        return False
    low = (issuer or '').lower()
    if 'google trust services' in low:
        return False
    return True


def _parse_cert_expiry(cert_pem: str) -> datetime | None:
    if not cert_pem.strip():
        return None
    try:
        proc = subprocess.run(
            ['openssl', 'x509', '-enddate', '-noout'],
            input=cert_pem,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return None
        line = proc.stdout.strip()
        if '=' not in line:
            return None
        raw = line.split('=', 1)[1].strip()
        try:
            dt = datetime.strptime(raw, '%b %d %H:%M:%S %Y %Z')
        except ValueError:
            dt = datetime.fromisoformat(raw.replace(' GMT', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except (OSError, ValueError):
        return None


def _private_key_valid(key_pem: str) -> bool:
    if not key_pem.strip():
        return False
    for args in (['openssl', 'rsa', '-check', '-noout'], ['openssl', 'ec', '-check', '-noout']):
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


def read_tls_files(domain: str) -> dict[str, Any] | None:
    cert_path, key_path = cert_paths_for_domain(domain)
    if not cert_path.is_file():
        certs = sorted(SSL_ROOT.glob('*.crt'))
        if not certs:
            return None
        cert_path = certs[-1]
        key_path = Path(f'{cert_path}.key')
    cert_pem = cert_path.read_text(encoding='utf-8') if cert_path.is_file() else ''
    key_pem = key_path.read_text(encoding='utf-8') if key_path.is_file() else ''
    if not cert_pem.strip():
        return None
    expires_at = _parse_cert_expiry(cert_pem)
    now = datetime.utcnow()
    key_ok = _private_key_valid(key_pem)
    not_expired = expires_at is None or expires_at > now
    valid_cert = bool(key_ok and not_expired)
    fingerprint = _sha256_pin_from_pem(cert_pem) or ''
    issuer = _issuer_from_pem(cert_pem)
    return {
        'certificate': cert_pem.strip(),
        'private_key': key_pem.strip(),
        'expires_at': expires_at,
        'valid_cert': valid_cert,
        'fingerprint': fingerprint,
        'issuer': issuer,
        'auto_renew': _auto_renew_from_issuer(issuer, valid_cert),
        'tls_cert_path': str(cert_path),
        'tls_key_path': str(key_path) if key_path.is_file() else '',
        'tls_cert_lines': [ln for ln in cert_pem.splitlines() if ln.strip()],
        'tls_key_lines': [ln for ln in key_pem.splitlines() if ln.strip()],
        'tls_pinnedPeerCertSha256': [fingerprint] if fingerprint else [],
    }


def _hostname_for_domain_db(domain_db: Any) -> str:
    return domain_file_key(getattr(domain_db, 'domain', '') or '')


def _tls_material_from_row(row: TlsStore, hostname: str) -> dict[str, Any]:
    cert_pem = row.certificate or ''
    key_pem = row.private_key or ''
    pin = row.fingerprint or ''
    name = domain_file_key(hostname) or hostname
    return {
        'tls_cert_path': str(cert_paths_for_domain(name)[0]),
        'tls_key_path': str(cert_paths_for_domain(name)[1]),
        'tls_cert': cert_pem,
        'tls_key': key_pem,
        'tls_cert_lines': [ln for ln in cert_pem.splitlines() if ln.strip()],
        'tls_key_lines': [ln for ln in key_pem.splitlines() if ln.strip()],
        'tls_pinnedPeerCertSha256': [pin] if pin else [],
        'tls_public_key_sha256': pin,
        'tls_fingerprint': pin,
        'tls_valid_cert': bool(row.valid_cert),
        'tls_expires_at': row.expires_at.isoformat() if row.expires_at else None,
        'tls_issuer': row.issuer or '',
        'tls_auto_renew': bool(row.auto_renew),
        'tls_last_renewal_error': row.last_renewal_error or '',
    }


def _lookup_domain(hostname: str, child_id: int = 0) -> Any | None:
    from hiddifypanel.models.domain import Domain

    name = domain_file_key(hostname)
    if not name:
        return None
    return Domain.query.filter(
        Domain.child_id == child_id,
        db.func.lower(Domain.domain) == name,
    ).first()


def tls_material_for_domain(
    domain: str,
    child_id: int = 0,
    *,
    domain_id: int | None = None,
    auto_sync: bool = True,
) -> dict[str, Any]:
    name = domain_file_key(domain)
    row = TlsStore.by_domain_id(domain_id) if domain_id else None
    if row is None and not domain_id:
        domain_db = _lookup_domain(name, child_id)
        if domain_db:
            row = TlsStore.by_domain_id(domain_db.id)
    if row is None and auto_sync:
        if domain_id:
            sync_tls_store_for_domain_id(domain_id, commit=True)
            row = TlsStore.by_domain_id(domain_id)
        else:
            sync_tls_store_for_domain(name, child_id=child_id, commit=True)
            domain_db = _lookup_domain(name, child_id)
            row = TlsStore.by_domain_id(domain_db.id) if domain_db else None
    if row is not None:
        host = name
        if row.domain and row.domain.domain:
            host = domain_file_key(row.domain.domain)
        return _tls_material_from_row(row, host)
    files = read_tls_files(name)
    if not files:
        return {}
    pin = files.get('fingerprint', '')
    return {
        'tls_cert_path': files.get('tls_cert_path', ''),
        'tls_key_path': files.get('tls_key_path', ''),
        'tls_cert': files.get('certificate', ''),
        'tls_key': files.get('private_key', ''),
        'tls_cert_lines': files.get('tls_cert_lines', []),
        'tls_key_lines': files.get('tls_key_lines', []),
        'tls_pinnedPeerCertSha256': files.get('tls_pinnedPeerCertSha256', []),
        'tls_public_key_sha256': pin,
        'tls_fingerprint': pin,
        'tls_valid_cert': bool(files.get('valid_cert')),
        'tls_expires_at': files['expires_at'].isoformat() if files.get('expires_at') else None,
        'tls_issuer': files.get('issuer', ''),
        'tls_auto_renew': bool(files.get('auto_renew')),
        'tls_last_renewal_error': '',
    }


def _apply_tls_payload(row: TlsStore, payload: dict[str, Any]) -> None:
    row.certificate = payload['certificate']
    row.private_key = payload['private_key']
    row.expires_at = payload.get('expires_at')
    row.valid_cert = bool(payload.get('valid_cert'))
    row.fingerprint = payload.get('fingerprint') or ''
    row.issuer = payload.get('issuer') or ''
    row.auto_renew = bool(payload.get('auto_renew'))
    row.last_renewal_error = None
    row.updated_at = datetime.utcnow()


def sync_tls_store_for_domain_id(domain_id: int, *, commit: bool = True) -> TlsStore | None:
    from hiddifypanel.models.domain import Domain

    domain_db = Domain.query.filter(Domain.id == int(domain_id)).first()
    if not domain_db or not domain_db.domain:
        logger.warning('TLS store sync skipped: domain id={} not found', domain_id)
        return None
    return _sync_tls_store_row(domain_db, commit=commit)


def sync_tls_store_for_domain(domain: str, child_id: int = 0, *, commit: bool = True) -> TlsStore | None:
    domain_db = _lookup_domain(domain, child_id)
    if not domain_db:
        logger.warning('TLS store sync skipped: no Domain row for {} child_id={}', domain_file_key(domain), child_id)
        return None
    return _sync_tls_store_row(domain_db, commit=commit)


def _sync_tls_store_row(domain_db: Any, *, commit: bool = True) -> TlsStore | None:
    hostname = _hostname_for_domain_db(domain_db)
    if not hostname:
        return None
    payload = read_tls_files(hostname)
    row = TlsStore.by_domain_id(domain_db.id)
    if not payload:
        if row:
            row.last_renewal_error = f'no certificate files found for {hostname}'
            row.updated_at = datetime.utcnow()
            if commit:
                db.session.commit()
        logger.warning('TLS store sync skipped: no certificate files for domain_id={} ({})', domain_db.id, hostname)
        return None

    if not row:
        row = TlsStore(domain_id=domain_db.id)
        db.session.add(row)

    _apply_tls_payload(row, payload)
    if commit:
        db.session.commit()
    logger.info(
        'TLS store synced domain_id={} host={} issuer={} valid={} expires={}',
        domain_db.id,
        hostname,
        row.issuer,
        row.valid_cert,
        row.expires_at,
    )
    return row


def sync_tls_store_all(child_id: int | None = None, *, commit: bool = True) -> int:
    from hiddifypanel.models.domain import Domain

    query = Domain.query.order_by(Domain.id)
    if child_id is not None:
        query = query.filter(Domain.child_id == child_id)
    synced = 0
    for domain_db in query.all():
        if _sync_tls_store_row(domain_db, commit=False):
            synced += 1
    if commit and synced:
        db.session.commit()
    return synced
