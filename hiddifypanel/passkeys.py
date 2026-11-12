"""Passkeys (WebAuthn) for admins: sign in with the device's fingerprint, face or PIN instead of a password.

**One passkey per domain.** A browser ties a passkey to the domain it was made on (its RP ID), and lets it sign in
there and on its subdomains only. So an admin gets one passkey on each domain of the panel (``panel_domains``): adding
a passkey makes it on the page's domain, then shows each other domain's step page in a frame (``plan_enrollment``), one
fingerprint/face prompt per domain, without leaving the page. The sign-in page of a domain offers its passkeys and asks for the
username and password when there is none. (Browsers can share one passkey between unrelated domains only through a
public ``/.well-known/webauthn`` file listing them all: anyone could then find every domain of the panel from one of
them, so the panel does not do that.) Passkeys do not work on an IP address.

**Checked on every passkey** (``verify_registration`` / ``verify_assertion``): the challenge (random, used once,
``CHALLENGE_SECONDS``, kept in the server-side session), the ceremony type, the page's origin, the domain (RP ID hash),
that the admin was present *and verified* (fingerprint/face/PIN), the signature with the stored public key, and the
signature counter (a counter going back means a copied authenticator). No attestation is asked for: the panel needs
only the public key, which the browser gives (``getPublicKey()``) in a form ``cryptography`` reads directly.
"""

from __future__ import annotations

import base64
import binascii
import datetime
import hashlib
import hmac
import ipaddress
import json
import re
import secrets
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa

if TYPE_CHECKING:
    from hiddifypanel.models import AdminPasskey, AdminUser

ES256, EDDSA, RS256 = -7, -8, -257
ALGORITHMS = (ES256, EDDSA, RS256)
CHALLENGE_SECONDS = 5 * 60
TIMEOUT_MS = 120_000
NAME_MAX = 64
_MAX_FIELD = 64 * 1024  # a passkey response is a few hundred bytes; refuse anything absurd before decoding it

_UP, _UV, _AT = 0x01, 0x04, 0x40
_SESSION_KEY = "passkey_challenge"


class PasskeyError(ValueError):
    """A passkey could not be made or checked. ``code`` is shown translated by the page."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail or code)
        self.code = code


# --------------------------------------------------------------------------- encoding


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64url(value: Any) -> bytes:
    if not isinstance(value, str) or not value or len(value) > _MAX_FIELD:
        raise PasskeyError("invalid", "missing or oversized field")
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (binascii.Error, ValueError) as e:
        raise PasskeyError("invalid", "not base64url") from e


def user_handle(admin: AdminUser) -> bytes:
    """A stable, opaque handle for the admin on their authenticator (the UUID itself is their secret link)."""
    return hashlib.sha256(f"hiddify-passkey:{admin.uuid}".encode()).digest()[:16]


# --------------------------------------------------------------------------- hosts


def split_host(host: str) -> tuple[str, str]:
    """``host[:port]`` → (lowercase hostname, ":port" or ""). IPv6 keeps its brackets off."""
    host = (host or "").strip().lower()
    if host.startswith("["):
        name, _, rest = host[1:].partition("]")
        return name, rest if rest.startswith(":") and rest[1:].isdigit() else ""
    name, sep, port = host.rpartition(":")
    if sep and port.isdigit() and ":" not in name:
        return name, f":{port}"
    return host, ""


def is_ip(name: str) -> bool:
    try:
        ipaddress.ip_address(name)
        return True
    except ValueError:
        return False


def rp_id_for(host: str) -> str | None:
    """The domain passkeys of the page at ``host`` belong to: its hostname (None on an IP or a bare name)."""
    name, _ = split_host(host)
    return name if name and "." in name and not is_ip(name) else None


def has_passkeys(rp_id: str | None, admin_id: int | None = None) -> bool:
    """Any passkey for ``rp_id`` (of ``admin_id`` when given)."""
    from hiddifypanel.models import AdminPasskey

    if not rp_id:
        return False
    query = AdminPasskey.query.filter(AdminPasskey.rp_id == rp_id)
    if admin_id is not None:
        query = query.filter(AdminPasskey.admin_id == admin_id)
    return query.first() is not None


# --------------------------------------------------------------------------- challenges (server-side session)


def new_challenge(kind: str, rp_id: str, admin_id: int | None = None) -> str:
    from flask import session

    challenge = b64url(secrets.token_bytes(32))
    session[_SESSION_KEY] = {"c": challenge, "kind": kind, "rp": rp_id, "admin": admin_id, "exp": time.time() + CHALLENGE_SECONDS}
    return challenge


def take_challenge(kind: str) -> dict:
    """The pending challenge of ``kind``, removed from the session (used once, even when the check then fails)."""
    from flask import session

    pending = session.pop(_SESSION_KEY, None)
    if not isinstance(pending, dict) or pending.get("kind") != kind or float(pending.get("exp") or 0) < time.time():
        raise PasskeyError("expired", "no pending challenge")
    return pending


# --------------------------------------------------------------------------- WebAuthn checks


@dataclass(frozen=True, slots=True)
class NewPasskey:
    credential_id: str
    public_key: str  # base64 DER SubjectPublicKeyInfo
    alg: int
    sign_count: int


def _client_data(field: Any, kind: str, challenge: str, origin: str, framed_by: str | None = None) -> bytes:
    """The checked clientDataJSON. Made inside a frame of another site: refused, unless ``framed_by`` (the dashboard
    page that showed this domain's step page in its frame; only it may frame that page) is the page on top."""
    raw = unb64url(field)
    try:
        data = json.loads(raw)
    except ValueError as e:
        raise PasskeyError("invalid", "clientDataJSON is not JSON") from e
    if not isinstance(data, dict) or data.get("type") != kind:
        raise PasskeyError("invalid", "wrong ceremony type")
    if not hmac.compare_digest(str(data.get("challenge") or ""), challenge):
        raise PasskeyError("expired", "challenge mismatch")
    if data.get("origin") != origin:
        raise PasskeyError("invalid", f"origin {data.get('origin')!r} is not {origin!r}")
    if data.get("crossOrigin") is True:
        top = data.get("topOrigin")
        if not framed_by or (top is not None and top != framed_by.removesuffix(":443")):
            raise PasskeyError("invalid", f"made inside a frame of {top or 'another site'}")
    return raw


def _authenticator_data(field: Any, rp_id: str) -> tuple[bytes, int, int]:
    """(raw authenticator data, flags, signature counter), after checking the domain and the admin's verification."""
    raw = unb64url(field)
    if len(raw) < 37:
        raise PasskeyError("invalid", "authenticator data too short")
    if not hmac.compare_digest(raw[:32], hashlib.sha256(rp_id.encode()).digest()):
        raise PasskeyError("invalid", "made for another domain")
    flags = raw[32]
    if not flags & _UP or not flags & _UV:
        raise PasskeyError("not_verified", "user not present or not verified")
    return raw, flags, int.from_bytes(raw[33:37], "big")


def _public_key(der: bytes, alg: int):
    try:
        key = serialization.load_der_public_key(der)
    except (ValueError, UnsupportedAlgorithm) as e:
        raise PasskeyError("unsupported", "unreadable public key") from e
    if alg == ES256 and isinstance(key, ec.EllipticCurvePublicKey) and isinstance(key.curve, ec.SECP256R1):
        return key
    if alg == EDDSA and isinstance(key, ed25519.Ed25519PublicKey):
        return key
    if alg == RS256 and isinstance(key, rsa.RSAPublicKey) and key.key_size >= 2048:
        return key
    raise PasskeyError("unsupported", f"key does not match algorithm {alg}")


def _check_signature(der: bytes, alg: int, signature: bytes, signed: bytes) -> None:
    key = _public_key(der, alg)
    try:
        if alg == ES256:
            key.verify(signature, signed, ec.ECDSA(hashes.SHA256()))
        elif alg == EDDSA:
            key.verify(signature, signed)
        else:
            key.verify(signature, signed, padding.PKCS1v15(), hashes.SHA256())
    except InvalidSignature as e:
        raise PasskeyError("invalid", "bad signature") from e


def verify_registration(credential: Any, *, challenge: str, origin: str, rp_id: str, framed_by: str | None = None) -> NewPasskey:
    """Check a new passkey (``navigator.credentials.create`` result, serialised by the page) and return what to store.
    ``framed_by``: the only page it may have been made in a frame of (see ``_client_data``)."""
    if not isinstance(credential, dict) or not isinstance(credential.get("response"), dict):
        raise PasskeyError("invalid", "no credential")
    response = credential["response"]
    cred_id = unb64url(credential.get("id"))
    if credential.get("type") != "public-key" or len(cred_id) > 1023:
        raise PasskeyError("invalid", "not a public-key credential")
    _client_data(response.get("clientDataJSON"), "webauthn.create", challenge, origin, framed_by)
    raw, flags, count = _authenticator_data(response.get("authenticatorData"), rp_id)
    if not flags & _AT or len(raw) < 37 + 18:
        raise PasskeyError("invalid", "no credential data")
    id_len = int.from_bytes(raw[37 + 16 : 37 + 18], "big")
    if not hmac.compare_digest(raw[37 + 18 : 37 + 18 + id_len], cred_id):
        raise PasskeyError("invalid", "credential ID mismatch")
    try:
        alg = int(response.get("publicKeyAlgorithm"))
    except (TypeError, ValueError) as e:
        raise PasskeyError("unsupported", "no algorithm") from e
    if alg not in ALGORITHMS or not response.get("publicKey"):
        raise PasskeyError("unsupported", f"algorithm {alg}")
    der = unb64url(response.get("publicKey"))
    _public_key(der, alg)
    return NewPasskey(credential_id=b64url(cred_id), public_key=base64.b64encode(der).decode(), alg=alg, sign_count=count)


def verify_assertion(credential: Any, passkey: AdminPasskey, *, challenge: str, origin: str, rp_id: str) -> int:
    """Check a passkey sign-in against the stored ``passkey``; return its new signature counter."""
    if not isinstance(credential, dict) or not isinstance(credential.get("response"), dict) or credential.get("type") != "public-key":
        raise PasskeyError("invalid", "no credential")
    response = credential["response"]
    client_raw = _client_data(response.get("clientDataJSON"), "webauthn.get", challenge, origin)
    raw, _, count = _authenticator_data(response.get("authenticatorData"), rp_id)
    _check_signature(base64.b64decode(passkey.public_key), passkey.alg, unb64url(response.get("signature")), raw + hashlib.sha256(client_raw).digest())
    if (count or passkey.sign_count) and count <= int(passkey.sign_count or 0):
        raise PasskeyError("cloned", f"signature counter went from {passkey.sign_count} to {count}")
    return count


# --------------------------------------------------------------------------- ceremonies


def creation_options(admin: AdminUser, rp_id: str, title: str, challenge: str | None = None) -> dict:
    """``PublicKeyCredentialCreationOptions`` (binary fields base64url) for a new passkey of ``admin``.

    The challenge is kept in the session, unless one is given (kept by the caller: the other domains' pages)."""
    from hiddifypanel.models import AdminPasskey

    existing = AdminPasskey.query.filter(AdminPasskey.admin_id == admin.id, AdminPasskey.rp_id == rp_id).all()
    name = (admin.name or "admin")[:64]
    return {
        "challenge": challenge or new_challenge("create", rp_id, admin.id),
        "rp": {"id": rp_id, "name": (title or "Hiddify")[:64]},
        "user": {"id": b64url(user_handle(admin)), "name": name, "displayName": name},
        "pubKeyCredParams": [{"type": "public-key", "alg": alg} for alg in ALGORITHMS],
        "timeout": TIMEOUT_MS,
        "attestation": "none",
        "authenticatorSelection": {"residentKey": "required", "requireResidentKey": True, "userVerification": "required"},
        "excludeCredentials": [{"type": "public-key", "id": p.credential_id} for p in existing],
    }


def request_options(rp_id: str) -> dict:
    """``PublicKeyCredentialRequestOptions``: any passkey of this domain (the device lists them; no username asked)."""
    return {"challenge": new_challenge("get", rp_id), "rpId": rp_id, "timeout": TIMEOUT_MS, "userVerification": "required", "allowCredentials": []}


def device_name(user_agent: str) -> str:
    """A name for a passkey from the browser that made it ("Chrome on Android"), so the admin does not have to type one."""
    try:
        import user_agents

        ua = user_agents.parse(user_agent or "")
        browser = "" if ua.browser.family == "Other" else ua.browser.family
        system = "" if ua.os.family == "Other" else ua.os.family
        name = f"{browser} on {system}" if browser and system else browser or system
    except Exception:
        name = ""
    return (name or "Passkey")[: NAME_MAX - 4]


def register(admin: AdminUser, credential: Any, name: str, origin: str, user_agent: str = "", pending: dict | None = None) -> AdminPasskey:
    """Store a new passkey for ``admin`` after checking it against the challenge given to the same admin.

    Without a ``name``, it is named after the browser and system it was made on (numbered when that name is taken)."""
    from hiddifypanel.database import db
    from hiddifypanel.models import AdminPasskey

    pending = pending or take_challenge("create")
    if pending.get("admin") != admin.id:
        raise PasskeyError("expired", "challenge of another admin")
    rp_id = str(pending.get("rp") or "")
    new = verify_registration(credential, challenge=pending["c"], origin=origin, rp_id=rp_id, framed_by=pending.get("framed_by"))
    if AdminPasskey.query.filter(AdminPasskey.credential_id == new.credential_id).first():
        raise PasskeyError("exists", "passkey already added")
    name = (name or "").strip()[:NAME_MAX]
    if not name:
        base = device_name(user_agent)
        taken = {n for (n,) in db.session.query(AdminPasskey.name).filter(AdminPasskey.admin_id == admin.id)}
        name = next(candidate for candidate in (base if i == 1 else f"{base} ({i})" for i in range(1, len(taken) + 2)) if candidate not in taken)
    row = AdminPasskey(
        admin_id=admin.id,
        credential_id=new.credential_id,
        public_key=new.public_key,
        alg=new.alg,
        sign_count=new.sign_count,
        rp_id=rp_id,
        name=name,
    )
    db.session.add(row)
    db.session.commit()
    return row


def authenticate(credential: Any, origin: str) -> AdminUser:
    """The admin a passkey sign-in belongs to, after every check; updates the passkey's counter and last use."""
    from hiddifypanel.database import db
    from hiddifypanel.models import AdminPasskey, AdminUser

    pending = take_challenge("get")
    rp_id = str(pending.get("rp") or "")
    cred_id = credential.get("id") if isinstance(credential, dict) else None
    if not isinstance(cred_id, str) or len(cred_id) > 1400:
        raise PasskeyError("invalid", "no credential ID")
    passkey = AdminPasskey.query.filter(AdminPasskey.credential_id == cred_id, AdminPasskey.rp_id == rp_id).first()
    if passkey is None:
        raise PasskeyError("unknown", "no such passkey (removed?)")
    admin = AdminUser.query.filter(AdminUser.id == passkey.admin_id).first()
    if admin is None or admin.deleted:
        raise PasskeyError("unknown", "the admin of this passkey is gone")
    handle = credential["response"].get("userHandle") if isinstance(credential.get("response"), dict) else None
    if handle and not hmac.compare_digest(unb64url(handle), user_handle(admin)):
        raise PasskeyError("invalid", "user handle mismatch")
    count = verify_assertion(credential, passkey, challenge=pending["c"], origin=origin, rp_id=rp_id)
    # Only this row's own columns: a passkey sign-in is not a change of the admin (no parent/node sync).
    AdminPasskey.query.filter(AdminPasskey.id == passkey.id).update({"sign_count": count, "last_used_at": datetime.datetime.now()})
    db.session.commit()
    return admin


# --------------------------------------------------------------------------- adding a passkey on every domain


ENROLL_SECONDS = 10 * 60
_ENROLL_KEY = "hiddify:passkey:enroll:"


def panel_domains() -> list[str]:
    """The domains an admin gets a passkey for: the sub-link-only domains when the panel has some, else the domains its
    admin links use (``Domain.get_domains``), this panel's own only (a node's domain opens the node's panel)."""
    from hiddifypanel.models import Child, Domain

    child_id = Child.current().id
    out: list[str] = []
    for d in Domain.get_domains():
        name = (d.domain or "").strip().lower()
        if d.child_id == child_id and "*" not in name and rp_id_for(name) and name not in out:
            out.append(name)
    return out


def missing_domains(admin: AdminUser, here: str | None) -> list[str]:
    """The panel's domains (and ``here``, the page's domain, first) where ``admin`` has no passkey yet."""
    from hiddifypanel.database import db
    from hiddifypanel.models import AdminPasskey

    have = {rp for (rp,) in db.session.query(AdminPasskey.rp_id).filter(AdminPasskey.admin_id == admin.id)}
    domains = ([here] if here else []) + [d for d in panel_domains() if d != here]
    return [d for d in domains if d not in have]


def _enroll_key(token: str) -> str:
    return _ENROLL_KEY + hashlib.sha256(token.encode()).hexdigest()


_LANG_RE = re.compile(r"[a-z]{2,3}(_[A-Za-z]{2,4})?")


def plan_enrollment(admin: AdminUser, here_host: str, page_path: str, lang: str = "") -> list[dict]:
    """One step per other domain where ``admin`` has no passkey yet: ``{domain, url, origin}``. My account shows each
    ``url`` in a frame (the page tells My account, at ``origin``, when it is done).

    Each step page is opened with a one-time token, kept hashed in Redis for ``ENROLL_SECONDS``. A frame of another
    domain gets no cookies, so the token holds the step's state (the challenge too) instead of a session. It only lets
    a passkey be added for that admin on that domain, and only framed by the page that asked for it; it signs nobody
    in. It is spent when the passkey is saved. ``lang``: the dashboard's language, so the step page speaks it too."""
    from hiddifypanel.cache import redis_client

    here, port = split_host(here_host)
    steps = []
    for name in missing_domains(admin, here):
        if name == here:
            continue
        host = name + port
        token = secrets.token_urlsafe(32)
        payload = {"admin": admin.id, "host": host, "parent": f"https://{here_host.lower()}", "lang": lang if _LANG_RE.fullmatch(lang or "") else ""}
        redis_client.set(_enroll_key(token), json.dumps(payload), ex=ENROLL_SECONDS)
        steps.append({"domain": name, "url": f"https://{host}{page_path}?t={token}", "origin": f"https://{host}"})
    return steps


def peek_enrollment(token: str, host: str) -> dict | None:
    """The step of ``token`` (kept) when it was made for ``host``, else None."""
    from hiddifypanel.cache import redis_client

    if not token or len(token) > 100:
        return None
    raw = redis_client.get(_enroll_key(token))
    payload = json.loads(raw) if raw else None
    return payload if payload and payload.get("host") == (host or "").lower() else None


def enrollment_options(token: str, host: str, title: str) -> dict:
    """The creation options for the step of ``token``; its challenge is kept with the step."""
    from hiddifypanel.cache import redis_client
    from hiddifypanel.models import AdminUser

    step = peek_enrollment(token, host)
    admin = AdminUser.query.filter(AdminUser.id == step["admin"]).first() if step else None
    rp_id = rp_id_for(host)
    if admin is None or admin.deleted or not rp_id:
        raise PasskeyError("expired", "no such step")
    challenge = b64url(secrets.token_bytes(32))
    redis_client.set(_enroll_key(token), json.dumps({**step, "c": challenge}), keepttl=True)
    return creation_options(admin, rp_id, title, challenge=challenge)


def finish_enrollment(token: str, host: str, credential: Any, user_agent: str = "") -> AdminPasskey:
    """Check and save the passkey of the step of ``token``. The step is spent once saved; a passkey that fails a check
    spends only its challenge (the page asks for a new one on the next try)."""
    from hiddifypanel.cache import redis_client
    from hiddifypanel.models import AdminUser

    key = _enroll_key(token) if token and len(token) <= 100 else None
    left = redis_client.pttl(key) if key else 0
    raw = redis_client.getdel(key) if key else None
    step = json.loads(raw) if raw else None
    if not step or step.get("host") != (host or "").lower() or not step.get("c"):
        raise PasskeyError("expired", "no such step")
    admin = AdminUser.query.filter(AdminUser.id == step["admin"]).first()
    rp_id = rp_id_for(host)
    if admin is None or admin.deleted or not rp_id:
        raise PasskeyError("expired", "the admin is gone")
    pending = {"c": step["c"], "rp": rp_id, "admin": admin.id, "framed_by": step.get("parent")}
    try:
        return register(admin, credential, "", origin=f"https://{host}", user_agent=user_agent, pending=pending)
    except PasskeyError:
        if left and left > 0:
            redis_client.set(key, json.dumps({k: v for k, v in step.items() if k != "c"}), px=left)
        raise
