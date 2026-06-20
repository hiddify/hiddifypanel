from __future__ import annotations

import http.client
import socket
import ssl
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from hiddifypanel.database import db
from hiddifypanel.models import ConfigEnum, Domain, hconfig
from hiddifypanel.models.server_ip import ServerIp
from hiddifypanel.models.tls_store import TlsStore


def health_secret_path(child_id: int = 0) -> str:
    return (hconfig(ConfigEnum.health_secret_path, child_id) or '').strip()


def is_health_secret_request(path: str, child_id: int = 0) -> bool:
    """True when path is /<health_path>/[resource]/… (auth bypass)."""
    secret = (hconfig(ConfigEnum.health_secret_path, child_id) or '').strip()
    if not secret:
        return False
    parts = [part for part in path.split('/') if part]
    if not parts or parts[0] != secret:
        return False

    return True


def first_valid_cert_domain(child_id: int = 0) -> str | None:
    row = (
        TlsStore.query.join(Domain, TlsStore.domain_id == Domain.id)
        .filter(Domain.child_id == child_id, TlsStore.valid_cert == True)  # noqa: E712
        .order_by(Domain.id)
        .first()
    )
    if row and row.domain and row.domain.domain:
        return str(row.domain.domain).strip().lower()
    domain = (
        Domain.query.filter(Domain.child_id == child_id, Domain.sub_link_only == False)  # noqa: E712
        .order_by(Domain.id)
        .first()
    )
    return domain.domain.strip().lower() if domain and domain.domain else None


def health_check_domain_url(domain_name: str, domain_id: int, child_id: int = 0) -> str:
    secret = health_secret_path(child_id)
    host = domain_name.strip().lower()
    return f'https://{host}/{secret}/domain/{int(domain_id)}/'


def health_check_ip_url(ip_row: ServerIp, child_id: int = 0) -> str | None:
    probe_host = first_valid_cert_domain(child_id)
    if not probe_host:
        return None
    secret = health_secret_path(child_id)
    return f'https://{probe_host}/{secret}/ip/{int(ip_row.id)}/'


def _https_get(sni: str, host_header: str, connect_host: str, path: str) -> tuple[int, str]:
    ctx = ssl.create_default_context()
    sock = socket.create_connection((connect_host, 443), timeout=15)
    tls_sock = ctx.wrap_socket(sock, server_hostname=sni)
    conn = http.client.HTTPSConnection(connect_host, timeout=15, context=ctx)
    conn.sock = tls_sock
    try:
        conn.request('GET', path, headers={'Host': host_header})
        resp = conn.getresponse()
        body = resp.read().decode('utf-8', errors='replace').strip()
        return int(resp.status), body
    finally:
        conn.close()


def run_domain_health_check(domain_id: int, child_id: int = 0) -> dict[str, Any]:
    domain: Domain = Domain.query.filter(Domain.id == domain_id, Domain.child_id == child_id).first()
    if not domain or not domain.name:
        return {'ok': False, 'error': 'domain not found'}
    cert = domain.certificate
    if not cert or not cert.valid_cert:
        probe_host = first_valid_cert_domain(child_id)
        if not probe_host:
            return {'ok': False, 'error': 'no domain with valid certificate for domain probe'}
        sni = probe_host
    else:
        sni = domain.name
    url = health_check_domain_url(domain.name, domain.id, child_id)
    path = urlparse(url).path or '/'

    health_status = 'fail'
    health_error = None
    try:
        status, body = _https_get(sni, domain.name, domain.name, path)
        ok = status == 200 and body.lower() == domain.name
        health_error = None if ok else f'unexpected response {status}: {body!r}'
        health_status = 'ok' if ok else 'fail'
        if ok:
            return {'ok': True, 'url': url, 'result': body}
        return {'ok': False, 'url': url, 'error': f'unexpected response {status}: {body!r}'}
    except OSError as exc:
        health_error = str(exc)
        return {'ok': False, 'url': url, 'error': health_error}
    finally:
        domain.last_health_check = datetime.utcnow()
        domain.last_health_status = health_status
        domain.last_health_error = health_error
        db.session.commit()


def run_ip_health_check(ip_id: int, child_id: int = 0) -> dict[str, Any]:
    ip_row = ServerIp.query.filter(ServerIp.id == ip_id, ServerIp.child_id == child_id).first()
    if not ip_row:
        return {'ok': False, 'error': 'server IP not found'}
    probe_host = first_valid_cert_domain(child_id)
    if not probe_host:
        return {'ok': False, 'error': 'no domain with valid certificate for IP probe'}
    url = health_check_ip_url(ip_row, child_id)
    if not url:
        return {'ok': False, 'error': 'could not build health check URL'}
    path = urlparse(url).path or '/'
    health_status = 'fail'
    health_error = None
    try:
        status, body = _https_get(probe_host, probe_host, ip_row.address.strip(), path)

        ok = status == 200 and body == ip_row.address.strip()
        health_status = 'ok' if ok else 'fail'
        health_error = None if ok else f'unexpected response {status}: {body!r}'
        if ok:
            return {'ok': True, 'url': url, 'result': body, 'probe_host': probe_host}
        return {'ok': False, 'url': url, 'error': health_error}
    except OSError as exc:
        health_error = str(exc)
        return {'ok': False, 'url': url, 'error': str(exc)}
    finally:
        ip_row.last_health_check = datetime.utcnow()
        ip_row.last_health_status = health_status
        ip_row.last_health_error = health_error
        db.session.commit()


def handle_domain_health_request(domain_id: int, child_id: int = 0) -> tuple[str, int]:
    domain = Domain.query.filter(Domain.id == domain_id, Domain.child_id == child_id).first()
    if not domain or not domain.domain:
        return 'not found', 404
    cert = domain.certificate
    if cert and not cert.valid_cert:
        return 'certificate not valid', 503
    return domain.domain.strip(), 200


def handle_ip_health_request(ip_id: int, child_id: int = 0) -> tuple[str, int]:
    ip_row = ServerIp.query.filter(ServerIp.id == ip_id, ServerIp.child_id == child_id).first()
    if not ip_row or not ip_row.enabled:
        return 'not found', 404
    return ip_row.address.strip(), 200
