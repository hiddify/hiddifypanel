"""ACME accounts and clients (RFC 8555, the ``acme`` library of certbot): Let's Encrypt and ZeroSSL.

One account per CA, its key in the ``acme_accounts`` setting (hidden). The contact email is the ``acme_email`` setting
(the admin can change it; a new account is registered with the new email). ZeroSSL needs an External Account Binding:
its credentials are asked from ZeroSSL's API with the email.

Tests: ``HIDDIFY_ACME_DIRECTORY_LETSENCRYPT`` / ``HIDDIFY_ACME_DIRECTORY_ZEROSSL`` replace a CA's directory URL (e.g.
Let's Encrypt staging or pebble), ``HIDDIFY_ACME_INSECURE=1`` skips TLS verification of the CA (pebble).
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass

import josepy as jose
import requests
from acme import client as acme_client
from acme import errors as acme_errors
from acme import messages
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from loguru import logger

from hiddifypanel.models import ConfigEnum, hconfig, set_hconfig

LETSENCRYPT = "letsencrypt"
ZEROSSL = "zerossl"
DIRECTORIES = {
    LETSENCRYPT: "https://acme-v02.api.letsencrypt.org/directory",
    ZEROSSL: "https://acme.zerossl.com/v2/DV90",
}
ZEROSSL_EAB_URL = "https://api.zerossl.com/acme/eab-credentials-email"
USER_AGENT = "hiddify-manager"
TIMEOUT = 30

_accounts_lock = threading.Lock()


def directory_url(ca: str) -> str:
    return os.environ.get(f"HIDDIFY_ACME_DIRECTORY_{ca.upper()}") or DIRECTORIES[ca]


def _verify_ssl() -> bool:
    return os.environ.get("HIDDIFY_ACME_INSECURE") != "1"


def contact_email() -> str:
    """The ``acme_email`` setting; one is made (and kept, so the admin sees and can change it) when it is empty:
    ZeroSSL does not issue without an email."""
    email = (hconfig(ConfigEnum.acme_email) or "").strip()
    if not email:
        email = f"hiddify-{uuid.uuid4().hex[:12]}@gmail.com"
        set_hconfig(ConfigEnum.acme_email, email)
        logger.info(f"ACME: no contact email set; using {email} (setting acme_email)")
    return email


@dataclass(slots=True)
class Account:
    """A stored ACME account of one CA (``acme_accounts`` setting: {ca: Account})."""

    directory: str
    email: str
    key: str  # PEM
    uri: str


def _load_accounts() -> dict[str, Account]:
    try:
        data = json.loads(hconfig(ConfigEnum.acme_accounts) or "{}")
    except (TypeError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    accounts: dict[str, Account] = {}
    for ca, item in data.items():
        try:
            accounts[ca] = Account(**item)
        except TypeError:
            logger.warning(f"ACME: ignoring a malformed stored account of {ca}")
    return accounts


def _save_accounts(accounts: dict[str, Account]) -> None:
    set_hconfig(ConfigEnum.acme_accounts, json.dumps({ca: asdict(acc) for ca, acc in accounts.items()}))


def _new_key() -> jose.JWKEC:
    return jose.JWKEC(key=ec.generate_private_key(ec.SECP256R1()))


def _key_from_pem(pem: str) -> jose.JWK:
    key = serialization.load_pem_private_key(pem.encode(), password=None)
    return jose.JWKEC(key=key) if isinstance(key, ec.EllipticCurvePrivateKey) else jose.JWKRSA(key=key)


def _key_pem(key: jose.JWK) -> str:
    return key.key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()


def _alg(key: jose.JWK):
    return jose.ES256 if isinstance(key, jose.JWKEC) else jose.RS256


@dataclass
class Acme:
    ca: str
    client: acme_client.ClientV2

    @property
    def key(self) -> jose.JWK:
        return self.client.net.key

    def profiles(self) -> set[str]:
        meta = self.client.directory.meta
        return set(meta.profiles or {}) if meta is not None else set()


def _zerossl_eab(email: str) -> tuple[str, str]:
    resp = requests.post(ZEROSSL_EAB_URL, data={"email": email}, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
    try:
        data = resp.json()
    except ValueError:
        data = {}
    if not data.get("success") or not data.get("eab_kid") or not data.get("eab_hmac_key"):
        raise RuntimeError(f"ZeroSSL did not give account credentials for {email}: HTTP {resp.status_code} {resp.text[:300]}")
    return data["eab_kid"], data["eab_hmac_key"]


def _client(key: jose.JWK, url: str) -> acme_client.ClientV2:
    net = acme_client.ClientNetwork(key, alg=_alg(key), user_agent=USER_AGENT, verify_ssl=_verify_ssl(), timeout=TIMEOUT)
    directory = acme_client.ClientV2.get_directory(url, net)
    return acme_client.ClientV2(directory, net)


def get(ca: str) -> Acme:
    """A client of ``ca`` with its account (registered the first time, or again when the email changed)."""
    email = contact_email()
    url = directory_url(ca)
    with _accounts_lock:
        accounts = _load_accounts()
        acc = accounts.get(ca)
        if acc and acc.directory == url and acc.email == email and acc.uri:
            client = _client(_key_from_pem(acc.key), url)
            client.net.account = messages.RegistrationResource(uri=acc.uri, body=messages.Registration())
            return Acme(ca, client)
        key = _new_key()
        client = _client(key, url)
        meta = client.directory.meta
        eab = None
        if ca == ZEROSSL or (meta is not None and meta.external_account_required):
            kid, hmac_key = _zerossl_eab(email)
            eab = messages.ExternalAccountBinding.from_data(account_public_key=key.public_key(), kid=kid, hmac_key=hmac_key, directory=client.directory)
        reg = messages.NewRegistration.from_data(email=email, terms_of_service_agreed=True, external_account_binding=eab)
        try:
            regr = client.new_account(reg)
        except acme_errors.ConflictError as e:  # the key has an account already
            regr = messages.RegistrationResource(uri=str(e.location), body=messages.Registration())
            client.net.account = regr
        accounts[ca] = Account(directory=url, email=email, key=_key_pem(key), uri=str(regr.uri))
        _save_accounts(accounts)
        logger.info(f"ACME: registered an account at {ca} ({url}) for {email}")
        return Acme(ca, client)


def forget(ca: str) -> None:
    """Drop the stored account of ``ca`` (it was deactivated or the CA does not know it): the next use registers again."""
    with _accounts_lock:
        accounts = _load_accounts()
        if accounts.pop(ca, None) is not None:
            _save_accounts(accounts)
            logger.warning(f"ACME: forgot the account at {ca}; a new one is registered next time")
