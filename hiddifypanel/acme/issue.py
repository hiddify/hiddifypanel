"""Issuing one certificate over ACME HTTP-01: a domain name, or an IPv4 / IPv6 address.

Let's Encrypt first, ZeroSSL when it fails (not for an IP: only Let's Encrypt issues them, with its ``shortlived``
profile, ~6 days, and not for the TLDs ZeroSSL refuses). HAProxy answers the challenges (``challenges.py``).
"""

from __future__ import annotations

import datetime
import ipaddress
import socket
from dataclasses import dataclass, field

from acme import challenges as acme_challenges
from acme import crypto_util, messages
from acme import errors as acme_errors
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from loguru import logger

from hiddifypanel.acme import challenges, client

MAX_NAME = 64  # x509 CN limit; acme.sh did not issue longer names either (they get a self-signed certificate)
ORDER_TIMEOUT = 150  # seconds for validation and finalization
IP_PROFILE = "shortlived"
# ZeroSSL refuses these (acme.sh's restricted_tlds)
ZEROSSL_RESTRICTED = (".ir", ".ru", ".cn", ".by", ".cu", ".kp", ".sy", "amazonaws.com", "azurewebsites.net", "cloudapp.net")


class IssueError(Exception):
    """Issuing failed. ``rate_limited``: every CA tried refused because of its rate limits (``retry_after``: seconds)."""

    def __init__(self, message: str, *, rate_limited: bool = False, retry_after: int | None = None):
        super().__init__(message)
        self.rate_limited = rate_limited
        self.retry_after = retry_after


@dataclass
class Issued:
    cert_pem: str  # full chain
    key_pem: str
    ca: str
    log: list[str] = field(default_factory=list)


def ip_of(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return None


def zerossl_allowed(host: str) -> bool:
    return not any(host == tld.lstrip(".") or host.endswith(tld if tld.startswith(".") else "." + tld) for tld in ZEROSSL_RESTRICTED)


def cas_for(host: str) -> list[str]:
    if ip_of(host):
        return [client.LETSENCRYPT]
    return [client.LETSENCRYPT] + ([client.ZEROSSL] if zerossl_allowed(host) else [])


def check_dns(host: str) -> str | None:
    """A warning when the name does not point to this server (issuing is still tried: a CDN or NAT may be in between)."""
    if ip_of(host):
        return None
    try:
        from hiddifypanel.hutils.network import get_ips_lazy

        mine = {str(ip) for ip in get_ips_lazy()}
    except Exception:
        mine = set()
    try:
        resolved = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except OSError as e:
        return f"{host} does not resolve ({e})"
    if mine and not resolved & mine:
        return f"{host} resolves to {', '.join(sorted(resolved))}, not to this server ({', '.join(sorted(mine))})"
    return None


def _rate_limit_of(err: Exception) -> tuple[bool, int | None]:
    """Whether an ACME error is a rate limit, and its Retry-After (seconds) when the CA gave one."""
    if isinstance(err, messages.Error) and (err.code == "rateLimited" or "rateLimited" in str(err.typ or "")):
        return True, None
    if isinstance(err, acme_errors.ValidationError):
        for authzr in err.failed_authzrs:
            for ch in authzr.body.challenges:
                if ch.error is not None and ch.error.code == "rateLimited":
                    return True, None
    text = str(err).lower()
    return ("ratelimited" in text or "rate limit" in text or "too many" in text), None


def _describe(err: Exception) -> str:
    if isinstance(err, acme_errors.ValidationError):
        parts = []
        for authzr in err.failed_authzrs:
            for ch in authzr.body.challenges:
                if ch.error is not None:
                    parts.append(f"{authzr.body.identifier.value}: {ch.error.detail or ch.error.typ}")
        return "validation failed: " + ("; ".join(parts) or "no detail")
    if isinstance(err, acme_errors.TimeoutError):
        return "the CA did not finish in time"
    if isinstance(err, messages.Error):
        return f"{err.code or err.typ}: {err.detail}"
    return f"{type(err).__name__}: {err}"


def _self_check(path: str, expected: str) -> str:
    """Debug: is the challenge answered locally (HAProxy on port 80)?"""
    import requests

    try:
        resp = requests.get(f"http://127.0.0.1{path}", timeout=3, headers={"Host": "acme.local"})
        return "ok" if resp.status_code == 200 and resp.text.strip() == expected else f"HTTP {resp.status_code} {resp.text[:80]!r}"
    except requests.RequestException as e:
        return f"not reachable ({e})"


def _order(acme: client.Acme, host: str, log: list[str]) -> tuple[str, str]:
    key = ec.generate_private_key(ec.SECP256R1())
    key_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    ip = ip_of(host)
    csr = crypto_util.make_csr(key_pem, ipaddrs=[ip]) if ip else crypto_util.make_csr(key_pem, [host])
    profile = None
    if ip:
        if IP_PROFILE not in acme.profiles():
            raise IssueError(f"{acme.ca} offers no '{IP_PROFILE}' profile: no certificate for an IP address")
        profile = IP_PROFILE
    order = acme.client.new_order(csr, profile=profile)
    log.append(f"{acme.ca}: order created{f' (profile {profile})' if profile else ''}")
    tokens: list[str] = []
    try:
        for authzr in order.authorizations:
            if authzr.body.status == messages.STATUS_VALID:
                continue  # validated recently for this account
            challb = next((c for c in authzr.body.challenges if isinstance(c.chall, acme_challenges.HTTP01)), None)
            if challb is None:
                raise IssueError(f"{acme.ca} offers no HTTP-01 challenge for {authzr.body.identifier.value}")
            response, validation = challb.response_and_validation(acme.key)
            token = challb.chall.encode("token")
            tokens.append(token)
            if not challenges.add(token, validation):
                # Answering now would only cost a failed validation at the CA (they count toward its limits)
                raise IssueError("HAProxy does not answer ACME challenges: its API socket is not reachable (apply the configs so HAProxy gets the ACME map)")
            logger.debug(f"ACME {host}: challenge {challb.chall.path} local check: {_self_check(challb.chall.path, validation)}")
            acme.client.answer_challenge(challb, response)
        log.append(f"{acme.ca}: challenges answered")
        deadline = datetime.datetime.now() + datetime.timedelta(seconds=ORDER_TIMEOUT)
        done = acme.client.poll_and_finalize(order, deadline)
    finally:
        for token in tokens:
            challenges.remove(token)
    if not done.fullchain_pem:
        raise IssueError(f"{acme.ca} returned no certificate")
    log.append(f"{acme.ca}: certificate issued")
    return done.fullchain_pem, key_pem.decode()


def issue(host: str) -> Issued:
    """A certificate for ``host``; raises IssueError (``rate_limited`` when every CA refused for its rate limits)."""
    host = (host or "").strip().lower().strip("[]")
    if not host or "*" in host:
        raise IssueError(f"no ACME certificate for {host!r} (wildcards come from the CDN)")
    if len(host) > MAX_NAME:
        raise IssueError(f"{host} is longer than {MAX_NAME} characters: no ACME certificate")
    log: list[str] = []
    if warning := check_dns(host):
        logger.warning(f"ACME {host}: {warning}")
        log.append(f"warning: {warning}")
    errors: list[str] = []
    limited: list[bool] = []
    retry_after: int | None = None
    for ca in cas_for(host):
        for attempt in (1, 2):  # a second time only with a fresh account, when the CA did not know the stored one
            try:
                logger.info(f"ACME {host}: asking {ca}")
                acme = client.get(ca)
                cert_pem, key_pem = _order(acme, host, log)
                logger.info(f"ACME {host}: issued by {ca}")
                return Issued(cert_pem, key_pem, ca, log)
            except Exception as e:
                code = e.code if isinstance(e, messages.Error) else None
                if attempt == 1 and code in ("accountDoesNotExist", "unauthorized") and "account" in str(e).lower():
                    client.forget(ca)
                    continue
                is_limited, after = _rate_limit_of(e)
                if isinstance(e, IssueError):
                    is_limited, after = e.rate_limited, e.retry_after
                msg = f"{ca}: {_describe(e)}"
                logger.warning(f"ACME {host}: {msg}")
                logger.opt(exception=e).debug(f"ACME {host}: {ca} failed")
                errors.append(msg)
                limited.append(is_limited)
                retry_after = after or retry_after
                break
    message = " | ".join(errors) or "no CA tried"
    raise IssueError(message, rate_limited=bool(limited) and all(limited), retry_after=retry_after)
