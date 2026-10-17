"""Certificates: tls_store (the source of truth) → files in data/cert → HAProxy.

HAProxy loads every ``data/cert/<name>.crt`` (+ ``.crt.key``) when it starts (``ssl crt /opt/hiddify-manager/data/cert/``).
The panel writes these files (the folder belongs to it: hiddify-panel, group hiddify-common, setgid; files 640), and
puts a new or renewed certificate into the running HAProxy through its API socket (``set ssl cert`` / ``commit``; a new
one is added to the folder's crt-list), so nothing needs a reload. A domain's files are removed with the domain.
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger
from redis import Redis

from hiddifypanel.acme import selfsigned
from hiddifypanel.acme.models import ExportStats
from hiddifypanel.database import db
from hiddifypanel.hutils import haproxy_api
from hiddifypanel.models import Child
from hiddifypanel.models.domain import Domain
from hiddifypanel.models.tls_store import TlsStore
from hiddifypanel.proxy_v3.tls_store_sync import CERT_ROOT, cert_paths_for_domain, domain_file_key, tls_payload

# One ssl transaction at a time in HAProxy (across processes too: a second "set ssl cert" while one is open fails).
_ssl_lock = threading.Lock()
_SSL_REDIS_LOCK = "hiddify:acme:haproxy-ssl-lock"
# A certificate that expires sooner than this is replaced by a self-signed one when nothing better is there.
USABLE_FOR = timedelta(days=1)


# ---------------------------------------------------------------------------------------------- files


def ensure_folder() -> bool:
    try:
        CERT_ROOT.mkdir(mode=0o2750, parents=True, exist_ok=True)
        return True
    except OSError as e:
        logger.error(f"certificates: can not create {CERT_ROOT}: {e}")
        return False


def _write(path: Path, content: str) -> None:
    """Atomic write (HAProxy never reads half a file), mode 640; the group comes from the setgid folder."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        os.chmod(tmp, 0o640)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_files(name: str, cert_pem: str, key_pem: str) -> bool:
    """Write ``<name>.crt`` and ``.crt.key`` when they differ. True when something changed."""
    if not ensure_folder():
        return False
    cert_path, key_path = cert_paths_for_domain(name)
    changed = False
    try:
        for path, content in ((key_path, key_pem), (cert_path, cert_pem)):  # the key first: HAProxy reads the pair
            want = content.strip() + "\n"
            if path.is_file() and path.read_text(encoding="utf-8") == want:
                continue
            _write(path, want)
            changed = True
    except OSError as e:
        logger.error(f"certificates: can not write {cert_path}: {e}")
        return False
    if changed:
        logger.debug(f"certificates: wrote {cert_path}")
    return changed


def remove_files(name: str) -> None:
    for path in cert_paths_for_domain(name):
        try:
            path.unlink(missing_ok=True)
        except OSError as e:
            logger.warning(f"certificates: can not remove {path}: {e}")
    logger.debug(f"certificates: removed the files of {name}")


def file_names() -> set[str]:
    """Names (file stem) of the certificates in the folder."""
    try:
        return {p.name[: -len(".crt")] for p in CERT_ROOT.glob("*.crt") if p.is_file()}
    except OSError:
        return set()


# ---------------------------------------------------------------------------------------------- HAProxy


class _SslLock:
    """The ssl transaction lock: this process (threads), and other processes through redis (the CLI, other workers)."""

    def __init__(self) -> None:
        self.redis: Redis | None = None

    def __enter__(self) -> _SslLock:
        _ssl_lock.acquire()
        try:
            from hiddifypanel.cache import redis_client

            deadline = time.monotonic() + 30
            while not redis_client.set(_SSL_REDIS_LOCK, "1", nx=True, ex=30) and time.monotonic() < deadline:
                time.sleep(0.2)  # past the deadline: a stale lock of a killed process (it expires anyway)
            self.redis = redis_client
        except Exception as e:
            logger.debug(f"certificates: redis lock unavailable ({e}); only this process is serialized")
        return self

    def __exit__(self, *exc: object) -> None:
        try:
            if self.redis is not None:
                self.redis.delete(_SSL_REDIS_LOCK)
        except Exception:
            pass
        finally:
            _ssl_lock.release()


def _ok(answer: str | None) -> bool:
    return answer is not None and any(ok in answer for ok in ("Success", "Transaction created", "Transaction updated", "New empty certificate store"))


def haproxy_install(name: str, cert_pem: str, key_pem: str) -> bool:
    """Put a certificate into the running HAProxy (no reload). False when it could not (the files are used at its
    next start anyway)."""
    cert_path = str(cert_paths_for_domain(name)[0])
    with _SslLock():
        shown = haproxy_api.command("show ssl cert")
        if shown is None:
            logger.debug(f"certificates: HAProxy not reachable; {name} is loaded at its next start")
            return False
        known = cert_path in shown.splitlines()
        steps: list[tuple[str, str | None]] = []
        if known:
            # Loaded from <name>.crt + <name>.crt.key: the key is updated under its own file name (in the same
            # transaction); a key inside the certificate's payload fails the commit ("unable to load SSL private key").
            steps += [(f"set ssl cert {cert_path}", cert_pem), (f"set ssl cert {cert_path}.key", key_pem)]
        else:
            steps += [(f"new ssl cert {cert_path}", None), (f"set ssl cert {cert_path}", cert_pem.strip() + "\n" + key_pem.strip())]
        steps.append((f"commit ssl cert {cert_path}", None))
        if not known:
            steps.append((f"add ssl crt-list {CERT_ROOT} {cert_path}", None))
        for cmd, body in steps:
            answer = haproxy_api.command(cmd, body, timeout=10)
            if not _ok(answer):
                logger.warning(f"certificates: HAProxy refused '{cmd}' for {name}: {answer}")
                haproxy_api.command(f"abort ssl cert {cert_path}")
                return False
    logger.info(f"certificates: HAProxy serves the new certificate of {name}")
    return True


def haproxy_remove(name: str) -> None:
    cert_path = str(cert_paths_for_domain(name)[0])
    with _SslLock():
        shown = haproxy_api.command("show ssl cert")
        if shown is None or cert_path not in shown.splitlines():
            return
        haproxy_api.command(f"del ssl crt-list {CERT_ROOT} {cert_path}")
        answer = haproxy_api.command(f"del ssl cert {cert_path}")
        logger.debug(f"certificates: removed {name} from HAProxy: {answer}")


# ---------------------------------------------------------------------------------------------- tls_store


def is_usable(row: TlsStore | None, host: str) -> bool:
    """The row has a certificate HAProxy can serve for ``host`` for at least a day (self-signed counts)."""
    if row is None or not (row.certificate or "").strip() or not (row.private_key or "").strip():
        return False
    payload = tls_payload(row.certificate, row.private_key, host)
    if not payload or not payload["valid_cert"]:
        return False
    return payload["expires_at"] is None or payload["expires_at"] > datetime.utcnow() + USABLE_FOR


def save(domain: Domain, cert_pem: str, key_pem: str, *, error: str | None = None, install: bool = True) -> bool:
    """Store a certificate of a domain (tls_store), write its files and put it into HAProxy. True when it changed."""
    host = domain_file_key(domain.domain or "")
    payload = tls_payload(cert_pem, key_pem, host)
    if not payload:
        raise ValueError(f"no certificate for {host}")
    row = TlsStore.by_domain_id(domain.id)
    changed = not row or (row.certificate or "").strip() != payload["certificate"]
    if not row:
        row = TlsStore(domain_id=domain.id)
        db.session.add(row)
    row.certificate = payload["certificate"]
    row.private_key = payload["private_key"]
    row.expires_at = payload["expires_at"]
    row.valid_cert = bool(payload["valid_cert"])
    row.self_signed = bool(payload["self_signed"])
    row.fingerprint = payload["fingerprint"] or ""
    row.issuer = payload["issuer"] or ""
    row.auto_renew = True
    row.last_renewal_error = error
    row.updated_at = datetime.utcnow()
    db.session.commit()
    files_changed = write_files(host, row.certificate, row.private_key)
    if install and (changed or files_changed):
        haproxy_install(host, row.certificate, row.private_key)
    return changed


def set_error(domain: Domain, error: str | None) -> None:
    row = TlsStore.by_domain_id(domain.id)
    if row is None:
        return
    row.last_renewal_error = error
    db.session.commit()


def ensure_self_signed(domain: Domain, *, error: str | None = None, install: bool = True) -> bool:
    """Give a domain a self-signed certificate when it has nothing usable. True when one was made."""
    host = domain_file_key(domain.domain or "")
    if not host or "*" in host:
        return False
    row = TlsStore.by_domain_id(domain.id)
    if is_usable(row, host):
        if error is not None:
            set_error(domain, error)
        return False
    cert_pem, key_pem = selfsigned.make(host)
    logger.info(f"certificates: self-signed certificate for {host}" + (f" ({error})" if error else ""))
    save(domain, cert_pem, key_pem, error=error, install=install)
    return True


def domains_of_this_server() -> list[Domain]:
    return Domain.query.filter(Domain.child_id == Child.current().id).order_by(Domain.id).all()


def export_all(*, install: bool = False) -> ExportStats:
    """Make data/cert match tls_store: every domain has a usable certificate (a self-signed one when it has none),
    every certificate is written, the files of removed domains are deleted. ``install``: also update the running
    HAProxy (the panel at runtime; at apply HAProxy is (re)started after this anyway)."""
    stats = ExportStats()
    if not ensure_folder():
        return stats
    wanted: set[str] = set()
    for d in domains_of_this_server():
        host = domain_file_key(d.domain or "")
        if not host:
            continue
        wanted.add(host)
        try:
            if "*" not in host and ensure_self_signed(d, install=install):
                stats.self_signed += 1
                continue
            row = TlsStore.by_domain_id(d.id)
            if row and (row.certificate or "").strip() and (row.private_key or "").strip():
                if write_files(host, row.certificate, row.private_key):
                    stats.written += 1
                    if install:
                        haproxy_install(host, row.certificate, row.private_key)
        except Exception as e:
            logger.exception(f"certificates: export of {host} failed: {e}")
    if not wanted:
        wanted.add("localhost")  # the stand-in below, while there is no domain
    for name in file_names() - wanted:
        logger.info(f"certificates: {name} is no longer a domain of this server; removing its certificate")
        if install:
            haproxy_remove(name)
        remove_files(name)
        stats.removed += 1
    if not file_names():
        # HAProxy does not start without a certificate (no domain at all yet)
        cert_pem, key_pem = selfsigned.make("localhost")
        write_files("localhost", cert_pem, key_pem)
        stats.self_signed += 1
    logger.debug(f"certificates: export done {stats}")
    return stats


def remove_domain(name: str) -> None:
    """A domain was deleted (its tls_store row goes with it): reconcile, so its certificate leaves HAProxy and the folder
    (unless another domain still has the same file name)."""
    logger.debug(f"certificates: domain {name} deleted")
    export_all(install=True)
