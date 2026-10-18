"""Getting and renewing the certificates of this server's domains.

- Only domains that need a real certificate (``Domain.need_valid_ssl``: valid TLS mode), no wildcard (the CDN has it), at
  most 64 characters; in the order sub-link-only, direct, relay, CDN, worker; a domain that failed before goes last.
- Renewed 14 days before it expires (3 days for an IP address: those last ~6 days).
- Several domains at once (``WORKERS``); HAProxy's map and ssl transactions are serialized (``haproxy_api.map_lock``,
  ``store``), and a domain is never issued twice at once (``state.domain_lock``).
- A failure is remembered: the scheduled run waits longer before each new try, and waits out a rate limit (as long as
  the CA said, else 3 hours). Meanwhile a domain with no usable certificate gets a self-signed one, and the error
  ("rate limited ..." for a rate limit) is shown on the domains page.
- When a certificate changed, hiddify-core's config (certificates inline) is rebuilt (``apply-users``).
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import cast

from flask import Flask, current_app
from loguru import logger

from hiddifypanel.acme import issue as acme_issue
from hiddifypanel.acme import state, store
from hiddifypanel.acme.models import CertJob, DomainResult, JobState, RenewSummary
from hiddifypanel.database import db
from hiddifypanel.models.domain import Domain, DomainType
from hiddifypanel.models.tls_store import TlsStore
from hiddifypanel.proxy_v3.tls_store_sync import tls_payload

WORKERS = 4
RENEW_BEFORE_DOMAIN = timedelta(days=14)
RENEW_BEFORE_IP = timedelta(days=3)
RATE_LIMIT_WAIT = 3 * 3600
RETRY_MIN = 30 * 60  # first wait after a failure (scheduled runs); doubles each time
RETRY_MAX = 12 * 3600
MODE_ORDER: tuple[DomainType, ...] = (DomainType.sub_link_only, DomainType.direct, DomainType.relay, DomainType.cdn, DomainType.worker)


def _utc(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, UTC)


def _app() -> Flask:
    """The app behind ``current_app`` (worker threads push its context)."""
    return cast(Flask, getattr(current_app, "_get_current_object")())


# ---------------------------------------------------------------------------------------------- which domains


def host_of(domain: Domain) -> str:
    return (domain.domain or "").strip().lower()


def mode_rank(domain: Domain) -> int:
    return MODE_ORDER.index(domain.mode) if domain.mode in MODE_ORDER else len(MODE_ORDER)


def can_issue(domain: Domain) -> bool:
    host = host_of(domain)
    return bool(domain.need_valid_ssl and host and "*" not in host and len(host) <= acme_issue.MAX_NAME)


def renewal_due(domain: Domain, now: datetime | None = None) -> str | None:
    """Why ``domain`` needs a (new) certificate, or None when its one is fine."""
    host = host_of(domain)
    row = TlsStore.by_domain_id(domain.id)
    if row is None or not (row.certificate or "").strip():
        return "no certificate"
    payload = tls_payload(row.certificate, row.private_key or "", host)
    if not payload or not payload["valid_cert"]:
        return "invalid or expired certificate"
    if payload["self_signed"]:
        return "self-signed certificate"
    before = RENEW_BEFORE_IP if acme_issue.ip_of(host) else RENEW_BEFORE_DOMAIN
    expires: datetime | None = payload["expires_at"]
    if expires is not None and expires - (now or datetime.utcnow()) < before:
        return f"expires {expires:%Y-%m-%d %H:%M} UTC"
    return None


def waiting(host: str) -> str | None:
    """Why a scheduled run should not try ``host`` now (a rate limit, or the wait after a failure)."""
    fail = state.get_failure(host)
    if fail is None:
        return None
    if fail.rate_limited:
        return f"rate limited until {_utc(fail.rate_limited_until):%Y-%m-%d %H:%M} UTC"
    wait = min(RETRY_MAX, RETRY_MIN * 2 ** max(0, fail.count - 1))
    if fail.at + wait > time.time():
        return f"failed {fail.count} time(s); next try after {_utc(fail.at + wait):%H:%M} UTC"
    return None


def ordered(domains: list[Domain]) -> list[Domain]:
    """sub-link-only, direct, relay, CDN, worker; the ones that failed before last."""
    return sorted(domains, key=lambda d: (state.get_failure(host_of(d)) is not None, mode_rank(d), d.id))


# ---------------------------------------------------------------------------------------------- one domain


def _failed(domain: Domain, res: DomainResult, error: str, *, rate_limited: bool = False) -> DomainResult:
    res.error, res.rate_limited = error, rate_limited
    store.ensure_self_signed(domain, error=error[-1000:], install=True)
    state.set_job(domain.id, CertJob(JobState.failed, finished=time.time(), error=error[-500:], rate_limited=rate_limited))
    return res


def _issue(domain: Domain, res: DomainResult) -> DomainResult:
    host = res.domain
    started = time.time()
    state.set_job(domain.id, CertJob(JobState.running, started=started))
    try:
        issued = acme_issue.issue(host)
    except acme_issue.IssueError as e:
        fail = state.add_failure(host, str(e), (e.retry_after or RATE_LIMIT_WAIT) if e.rate_limited else None)
        if e.rate_limited:
            return _failed(domain, res, f"rate limited (until {_utc(fail.rate_limited_until):%Y-%m-%d %H:%M} UTC): {e}", rate_limited=True)
        return _failed(domain, res, str(e))
    res.changed = store.save(domain, issued.cert_pem, issued.key_pem, error=None, install=True)
    res.ok, res.ca = True, issued.ca
    state.clear_failure(host)
    state.set_job(domain.id, CertJob(JobState.done, started=started, finished=time.time(), ca=issued.ca))
    logger.info(f"ACME {host}: certificate from {issued.ca} installed in {time.time() - started:.1f}s ({'; '.join(issued.log)})")
    return res


def process(domain_id: int) -> DomainResult:
    """Get a certificate for one domain now (in the caller's app context). Never raises."""
    res = DomainResult(domain_id)
    with state.domain_lock(domain_id) as got:
        if not got:
            res.error = "a certificate is already being requested for this domain"
            return res
        domain = db.session.get(Domain, domain_id)
        if domain is None:
            res.error = "domain not found"
            return res
        res.domain = host_of(domain)
        try:
            if not can_issue(domain):
                store.ensure_self_signed(domain, install=True)
                res.error = "this domain does not get a real certificate"
                return res
            return _issue(domain, res)
        except Exception as e:
            logger.exception(f"ACME {res.domain}: unexpected error: {e}")
            db.session.rollback()
            try:
                return _failed(domain, res, f"{type(e).__name__}: {e}")
            except Exception:
                logger.exception(f"ACME {res.domain}: self-signed fallback failed")
                return res


def _in_context(app: Flask, domain_id: int) -> DomainResult:
    with app.app_context():
        try:
            return process(domain_id)
        finally:
            db.session.remove()


def start(domain_id: int) -> bool:
    """Get a certificate for one domain in the background (the domains page). False when one is being requested already."""
    if state.domain_busy(domain_id):
        return False
    app = _app()
    state.set_job(domain_id, CertJob(JobState.running, started=time.time()))

    def work() -> None:
        if _in_context(app, domain_id).changed:
            refresh_cores()

    threading.Thread(target=work, name=f"acme-{domain_id}", daemon=True).start()
    return True


# ---------------------------------------------------------------------------------------------- all domains


def refresh_cores() -> None:
    """hiddify-core has the certificates inline: rebuild its config (apply-users: dump + reload, no panel restart)."""
    from hiddifypanel.panel import hiddify

    try:
        hiddify.quick_apply_users()
        logger.info("ACME: certificates changed; rebuilding the cores' configs (apply-users)")
    except Exception as e:
        logger.warning(f"ACME: could not refresh the cores after a certificate change: {e}")


def due_domains(summary: RenewSummary, *, force: bool) -> list[int]:
    due: list[int] = []
    for d in ordered([d for d in store.domains_of_this_server() if can_issue(d)]):
        reason = renewal_due(d)
        if reason is None:
            continue
        host = host_of(d)
        if not force and (why := waiting(host)):
            logger.debug(f"ACME {host}: due ({reason}) but {why}")
            summary.skipped.append(f"{host}: {why}")
            continue
        logger.info(f"ACME {host}: certificate needed ({reason})")
        due.append(d.id)
    return due


def has_real_certificate() -> bool:
    return any(renewal_due(d) is None for d in store.domains_of_this_server() if can_issue(d))


def run(*, force: bool = False, wait_lock: bool = False, apply: bool = True, only_without_valid: bool = False) -> RenewSummary:
    """Renew what is due (in the caller's app context).

    ``force``: also the domains waiting after a failure or a rate limit. ``wait_lock``: wait for another process's run
    instead of skipping. ``only_without_valid``: nothing when a domain has a real certificate already (legacy
    ``--first``; the installer issues every due domain instead). ``apply``: rebuild the cores' configs when a
    certificate changed.
    """
    summary = RenewSummary()
    with state.renewal_lock(1800 if wait_lock else 0) as got:
        if not got:
            summary.skipped.append("another renewal is running")
            return summary
        try:
            store.export_all(install=True)  # self-signed stand-ins, files of removed domains, the folder itself
        except Exception as e:
            logger.exception(f"ACME: export before renewal failed: {e}")
        if only_without_valid and has_real_certificate():
            summary.skipped.append("a real certificate exists")
            return summary
        due = due_domains(summary, force=force)
        summary.due = len(due)
        if not due:
            return summary
        app = _app()
        with ThreadPoolExecutor(max_workers=min(WORKERS, len(due)), thread_name_prefix="acme") as pool:
            for res in pool.map(lambda domain_id: _in_context(app, domain_id), due):
                summary.add(res)
    logger.info(f"ACME: renewal done: {summary.issued} issued, {summary.failed} failed ({summary.rate_limited} rate limited)")
    if summary.changed and apply:
        refresh_cores()
    return summary
