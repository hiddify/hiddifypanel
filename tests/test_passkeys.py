"""Passkeys: a passkey signs its admin in only when every WebAuthn check passes, and only on its own domain.

A software authenticator (keys from ``cryptography``) plays the admin's device.
"""

from __future__ import annotations

import base64
import hashlib
import json

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from flask import Flask

from hiddifypanel import passkeys
from hiddifypanel.database import db
from hiddifypanel.models import AdminMode, AdminPasskey, AdminUser, Child, ChildMode, Domain

RP = "panel.example.com"
ORIGIN = f"https://{RP}"
ADMIN_UUID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class Device:
    """A passkey on a device: makes it and signs in with it, like a browser + authenticator would."""

    def __init__(self, alg: int = passkeys.ES256):
        self.alg = alg
        if alg == passkeys.ES256:
            self.key = ec.generate_private_key(ec.SECP256R1())
        elif alg == passkeys.EDDSA:
            self.key = ed25519.Ed25519PrivateKey.generate()
        else:
            self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.cred_id = b"cred-" + alg.to_bytes(2, "big", signed=True) + bytes(range(16))
        self.count = 0

    def _client(self, kind: str, challenge: str, origin: str, top: str | None = None) -> bytes:
        data = {"type": kind, "challenge": challenge, "origin": origin, "crossOrigin": top is not None}
        if top:  # made in a frame: the browser names the page on top (Chrome)
            data["topOrigin"] = top
        return json.dumps(data).encode()

    def create(self, options: dict, *, origin: str = ORIGIN, rp: str | None = None, flags: int = 0x45, top: str | None = None) -> dict:
        rp_hash = hashlib.sha256((rp or options["rp"]["id"]).encode()).digest()
        auth = rp_hash + bytes([flags]) + self.count.to_bytes(4, "big") + bytes(16) + len(self.cred_id).to_bytes(2, "big") + self.cred_id + b"\xa0"
        spki = self.key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        return {
            "id": b64u(self.cred_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64u(self._client("webauthn.create", options["challenge"], origin, top)),
                "authenticatorData": b64u(auth),
                "publicKey": b64u(spki),
                "publicKeyAlgorithm": self.alg,
            },
        }

    def get(self, options: dict, *, origin: str = ORIGIN, rp: str | None = None, flags: int = 0x05, count: int | None = None, tamper: bool = False) -> dict:
        self.count = self.count + 1 if count is None else count
        auth = hashlib.sha256((rp or options["rpId"]).encode()).digest() + bytes([flags]) + self.count.to_bytes(4, "big")
        client = self._client("webauthn.get", options["challenge"], origin)
        signed = auth + hashlib.sha256(client).digest()
        if self.alg == passkeys.ES256:
            sig = self.key.sign(signed, ec.ECDSA(hashes.SHA256()))
        elif self.alg == passkeys.EDDSA:
            sig = self.key.sign(signed)
        else:
            sig = self.key.sign(signed, padding.PKCS1v15(), hashes.SHA256())
        if tamper:
            client = client.replace(b'"crossOrigin": false', b'"crossOrigin": false ')
        return {
            "id": b64u(self.cred_id),
            "type": "public-key",
            "response": {"clientDataJSON": b64u(client), "authenticatorData": b64u(auth), "signature": b64u(sig), "userHandle": None},
        }


@pytest.fixture
def app():
    app = Flask("passkeys-test")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.secret_key = "test"
    db.init_app(app)
    with app.app_context():
        db.create_all()
        db.session.add(Child(id=0, name="root", unique_id="root-uid", mode=ChildMode.virtual))
        db.session.add(AdminUser(id=1, uuid=ADMIN_UUID, name="Owner", mode=AdminMode.super_admin))
        db.session.add(Domain(domain=RP))
        db.session.add(Domain(domain="other.example.net"))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def ctx(app):
    with app.test_request_context("/", base_url=ORIGIN):
        yield


def admin() -> AdminUser:
    return db.session.get(AdminUser, 1)


def add_passkey(device: Device) -> AdminPasskey:
    options = passkeys.creation_options(admin(), RP, "Hiddify")
    return passkeys.register(admin(), device.create(options), "My phone", origin=ORIGIN)


# --------------------------------------------------------------------------- making and using a passkey


@pytest.mark.parametrize("alg", [passkeys.ES256, passkeys.EDDSA, passkeys.RS256])
def test_a_passkey_signs_its_admin_in(ctx, alg):
    device = Device(alg)
    row = add_passkey(device)
    assert (row.rp_id, row.name, row.alg) == (RP, "My phone", alg)
    assert passkeys.has_passkeys(RP, 1) and not passkeys.has_passkeys("other.example.net")

    for _ in range(2):
        assert passkeys.authenticate(device.get(passkeys.request_options(RP)), origin=ORIGIN).id == 1
    assert db.session.get(AdminPasskey, row.id).sign_count == 2 and db.session.get(AdminPasskey, row.id).last_used_at


def test_the_options_hide_the_admins_uuid_and_ask_for_verification(ctx):
    options = passkeys.creation_options(admin(), RP, "Hiddify")
    assert ADMIN_UUID not in json.dumps(options)
    assert options["authenticatorSelection"]["userVerification"] == "required"
    assert options["authenticatorSelection"]["residentKey"] == "required"


@pytest.mark.parametrize(
    "bad",
    [
        {"origin": "https://evil.example"},  # a phishing page
        {"rp": "evil.example"},  # a passkey of another site
        {"flags": 0x41},  # present but not verified (no fingerprint/PIN)
    ],
)
def test_a_new_passkey_is_refused_when_a_check_fails(ctx, bad):
    options = passkeys.creation_options(admin(), RP, "Hiddify")
    with pytest.raises(passkeys.PasskeyError):
        passkeys.register(admin(), Device().create(options, **bad), "x", origin=ORIGIN)
    assert AdminPasskey.query.count() == 0


@pytest.mark.parametrize(
    "bad",
    [
        {"origin": "https://evil.example"},
        {"rp": "evil.example"},
        {"flags": 0x01},  # not verified
        {"tamper": True},  # signature does not match what was sent
        {"count": 0},  # the counter went back: a copied authenticator
    ],
)
def test_a_sign_in_is_refused_when_a_check_fails(ctx, bad):
    device = Device()
    add_passkey(device)
    passkeys.authenticate(device.get(passkeys.request_options(RP)), origin=ORIGIN)  # counter 1
    with pytest.raises(passkeys.PasskeyError):
        passkeys.authenticate(device.get(passkeys.request_options(RP), **bad), origin=ORIGIN)


def test_a_challenge_is_used_once(ctx):
    device = Device()
    add_passkey(device)
    signed = device.get(passkeys.request_options(RP))
    passkeys.authenticate(signed, origin=ORIGIN)
    with pytest.raises(passkeys.PasskeyError) as err:
        passkeys.authenticate(signed, origin=ORIGIN)  # replayed
    assert err.value.code == "expired"


def test_another_devices_key_can_not_sign_for_a_passkey(ctx):
    device, thief = Device(), Device()
    add_passkey(device)
    forged = thief.get(passkeys.request_options(RP))  # same credential ID, other key
    with pytest.raises(passkeys.PasskeyError):
        passkeys.authenticate(forged, origin=ORIGIN)


def test_a_removed_passkey_or_deleted_admin_can_not_sign_in(ctx):
    device = Device()
    row = add_passkey(device)
    admin().deleted = True
    db.session.commit()
    with pytest.raises(passkeys.PasskeyError) as err:
        passkeys.authenticate(device.get(passkeys.request_options(RP)), origin=ORIGIN)
    assert err.value.code == "unknown"

    AdminUser.query_with_deleted().filter(AdminUser.id == 1).one().deleted = False
    db.session.delete(row)
    db.session.commit()
    with pytest.raises(passkeys.PasskeyError):
        passkeys.authenticate(device.get(passkeys.request_options(RP)), origin=ORIGIN)


def test_a_challenge_for_one_admin_does_not_add_a_passkey_to_another(ctx):
    db.session.add(AdminUser(id=2, uuid="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", name="Agent", mode=AdminMode.agent))
    db.session.commit()
    options = passkeys.creation_options(admin(), RP, "Hiddify")
    with pytest.raises(passkeys.PasskeyError):
        passkeys.register(db.session.get(AdminUser, 2), Device().create(options), "x", origin=ORIGIN)


def test_garbage_is_refused_cleanly(ctx):
    for junk in (None, "x", {"id": "!!", "type": "public-key", "response": {}}, {"type": "public-key", "response": {"clientDataJSON": "a" * 100_000}}):
        passkeys.request_options(RP)
        with pytest.raises(passkeys.PasskeyError):
            passkeys.authenticate(junk, origin=ORIGIN)


# --------------------------------------------------------------------------- hosts and hops


def test_passkeys_belong_to_the_domain_of_the_page():
    assert passkeys.rp_id_for("Panel.Example.com:8443") == "panel.example.com"
    assert passkeys.rp_id_for("203.0.113.7") is None and passkeys.rp_id_for("[2001:db8::1]:443") is None  # no passkeys on an IP
    assert passkeys.rp_id_for("localhost") is None
    assert passkeys.split_host("[2001:db8::1]:443") == ("2001:db8::1", ":443")


def test_a_passkey_of_one_domain_does_not_sign_in_on_another(app):
    device = Device()
    with app.test_request_context("/", base_url=ORIGIN):
        add_passkey(device)
    with app.test_request_context("/", base_url="https://other.example.net"):
        options = passkeys.request_options("other.example.net")
        with pytest.raises(passkeys.PasskeyError):  # the browser would not even offer it; a forged one is refused
            passkeys.authenticate(device.get(options, rp=RP, origin="https://other.example.net"), origin="https://other.example.net")


# --------------------------------------------------------------------------- the suggestion after a password sign-in


def test_a_passkey_is_suggested_once_after_a_password_sign_in(app):
    from flask import session

    from hiddifypanel.panel.commercial.restapi.v2.admin import passkeys_api as api

    with app.test_request_context("/", base_url=ORIGIN):
        assert api.take_suggestion(admin()) is None  # no password sign-in: nothing to suggest
        api.after_password_login(admin())
        assert api.take_suggestion(admin()) == {"domain": RP, "missing": [RP, "other.example.net"]}
        assert api.take_suggestion(admin()) is None  # once

        add_passkey(Device())
        api.after_password_login(admin())
        assert api.take_suggestion(admin()) == {"domain": RP, "missing": ["other.example.net"]}  # still missing there
    with app.test_request_context("/", base_url="https://other.example.net"):
        options = passkeys.creation_options(admin(), "other.example.net", "Hiddify")
        device = Device()
        device.cred_id += b"2"
        passkeys.register(admin(), device.create(options, origin="https://other.example.net"), "", origin="https://other.example.net")
    with app.test_request_context("/", base_url=ORIGIN):
        api.after_password_login(admin())
        assert api.take_suggestion(admin()) is None  # a passkey on every domain
        assert "passkey_suggest" not in session


def test_a_domain_without_my_passkey_offers_one_on_sign_in(app):
    """Signed in on another domain (e.g. with the admin link) while I use a passkey elsewhere: offered there once."""
    from hiddifypanel.panel.commercial.restapi.v2.admin import passkeys_api as api

    with app.test_request_context("/", base_url="https://other.example.net"):
        assert api.take_suggestion(admin()) is None  # no passkey anywhere yet: only after a password sign-in
    with app.test_request_context("/", base_url=ORIGIN):
        add_passkey(Device())
        assert api.take_suggestion(admin()) is None  # this domain has mine
    with app.test_request_context("/", base_url="https://other.example.net"):
        assert api.take_suggestion(admin()) == {"domain": "other.example.net", "missing": ["other.example.net"]}
        assert api.take_suggestion(admin()) is None  # once per sign-in


def test_on_an_ip_the_suggestion_covers_the_domains(app):
    from hiddifypanel.panel.commercial.restapi.v2.admin import passkeys_api as api

    with app.test_request_context("/", base_url="https://203.0.113.7"):
        api.after_password_login(admin())
        assert api.take_suggestion(admin()) == {"domain": None, "missing": [RP, "other.example.net"]}


def test_a_passkey_is_named_after_the_device_that_made_it(ctx):
    android = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36"
    assert passkeys.device_name(android) == "Chrome on Android"
    assert passkeys.device_name("") == "Passkey"

    names = []
    for _ in range(2):
        options = passkeys.creation_options(admin(), RP, "Hiddify")
        device = Device()
        device.cred_id += bytes([len(names)])
        names.append(passkeys.register(admin(), device.create(options), "", origin=ORIGIN, user_agent=android).name)
    assert names == ["Chrome on Android", "Chrome on Android (2)"]


# --------------------------------------------------------------------------- adding the passkey on every domain


class FakeRedis:
    def __init__(self):
        self.values: dict[str, str] = {}

    def set(self, key, value, ex=None, px=None, keepttl=False):
        self.values[key] = value

    def pttl(self, key):
        return 600_000 if key in self.values else -2

    def get(self, key):
        return self.values.get(key)

    def getdel(self, key):
        return self.values.pop(key, None)


@pytest.fixture
def domains_setup():
    from unittest import mock

    redis = FakeRedis()
    domains = [Domain(domain=RP, child_id=0), Domain(domain="other.example.net", child_id=0), Domain(domain="*.wild.example", child_id=0), Domain(domain="node.example.org", child_id=5)]
    with mock.patch("hiddifypanel.cache.redis_client", redis), mock.patch.object(Domain, "get_domains", return_value=domains), mock.patch("hiddifypanel.models.Child.current", return_value=mock.Mock(id=0)):
        yield redis


def test_the_other_domains_are_framed_steps(ctx, domains_setup):
    assert passkeys.panel_domains() == [RP, "other.example.net"]  # no wildcard, no node's domain
    assert passkeys.missing_domains(admin(), RP) == [RP, "other.example.net"]

    add_passkey(Device())  # here first
    (step,) = passkeys.plan_enrollment(admin(), f"{RP}:8443", "/p/passkey/enroll/")
    assert step["domain"] == "other.example.net" and step["origin"] == "https://other.example.net:8443"
    assert step["url"].startswith("https://other.example.net:8443/p/passkey/enroll/?t=")
    token = step["url"].split("t=", 1)[1]
    assert token not in json.dumps(domains_setup.values)  # stored hashed
    assert passkeys.peek_enrollment(token, RP) is None  # only on its own domain
    assert passkeys.peek_enrollment(token, "other.example.net:8443")["parent"] == f"https://{RP}:8443"  # who may frame it
    assert passkeys.peek_enrollment(token, "other.example.net:8443")["lang"] == ""
    (step,) = passkeys.plan_enrollment(admin(), RP, "/p/passkey/enroll/", "fa")  # the dashboard's language
    assert passkeys.peek_enrollment(step["url"].split("t=", 1)[1], "other.example.net")["lang"] == "fa"
    (step,) = passkeys.plan_enrollment(admin(), RP, "/p/passkey/enroll/", "../en")  # not a language
    assert passkeys.peek_enrollment(step["url"].split("t=", 1)[1], "other.example.net")["lang"] == ""


def test_a_framed_step_adds_the_passkey_on_its_domain_once(app, domains_setup):
    with app.test_request_context("/", base_url=ORIGIN):
        (step,) = passkeys.plan_enrollment(admin(), RP, "/p/passkey/enroll/")
    token, host = step["url"].split("t=", 1)[1], "other.example.net"
    with app.test_request_context("/", base_url=f"https://{host}"):  # no session: a frame of another domain has no cookies
        with pytest.raises(passkeys.PasskeyError):
            passkeys.finish_enrollment(token, host, {})  # no challenge asked yet: refused, and the token is spent
    with app.test_request_context("/", base_url=ORIGIN):
        (step,) = passkeys.plan_enrollment(admin(), RP, "/p/passkey/enroll/")
    token = step["url"].split("t=", 1)[1]
    with app.test_request_context("/", base_url=f"https://{host}"):
        options = passkeys.enrollment_options(token, host, "Hiddify")
        assert options["rp"]["id"] == host
        device = Device()
        row = passkeys.finish_enrollment(token, host, device.create(options, origin=f"https://{host}"))
        assert (row.rp_id, row.admin_id) == (host, 1)
        with pytest.raises(passkeys.PasskeyError):  # used once
            passkeys.enrollment_options(token, host, "Hiddify")
        # and it signs in there
        assert passkeys.authenticate(device.get(passkeys.request_options(host), origin=f"https://{host}"), origin=f"https://{host}").id == 1
    with app.test_request_context("/", base_url=ORIGIN):
        assert passkeys.missing_domains(admin(), RP) == [RP]


def test_a_step_refuses_a_passkey_for_another_domain(app, domains_setup):
    with app.test_request_context("/", base_url=ORIGIN):
        (step,) = passkeys.plan_enrollment(admin(), RP, "/p/passkey/enroll/")
    token, host = step["url"].split("t=", 1)[1], "other.example.net"
    with app.test_request_context("/", base_url=f"https://{host}"):
        options = passkeys.enrollment_options(token, host, "Hiddify")
        with pytest.raises(passkeys.PasskeyError):  # made by a page of another site
            passkeys.finish_enrollment(token, host, Device().create(options, origin="https://evil.example"))


def test_a_step_accepts_a_passkey_made_in_the_frame_of_its_own_page_only(app, domains_setup):
    """Chrome marks a passkey made in another site's frame (crossOrigin, topOrigin): fine under the page that asked."""
    host = "other.example.net"
    with app.test_request_context("/", base_url=ORIGIN):
        (step,) = passkeys.plan_enrollment(admin(), RP, "/p/passkey/enroll/")
    token = step["url"].split("t=", 1)[1]
    with app.test_request_context("/", base_url=f"https://{host}"):
        options = passkeys.enrollment_options(token, host, "Hiddify")
        with pytest.raises(passkeys.PasskeyError) as e:  # in a frame of another page
            passkeys.finish_enrollment(token, host, Device().create(options, origin=f"https://{host}", top="https://evil.example"))
        assert e.value.code == "invalid"
        # the failed try spent only its challenge: the next one (new options) works
        options = passkeys.enrollment_options(token, host, "Hiddify")
        row = passkeys.finish_enrollment(token, host, Device().create(options, origin=f"https://{host}", top=ORIGIN))
        assert row.rp_id == host
        with pytest.raises(passkeys.PasskeyError):  # and now the step is spent
            passkeys.enrollment_options(token, host, "Hiddify")


def test_outside_a_step_a_framed_passkey_is_refused(ctx):
    options = passkeys.creation_options(admin(), RP, "Hiddify")
    with pytest.raises(passkeys.PasskeyError):
        passkeys.register(admin(), Device().create(options, top=ORIGIN), "", origin=ORIGIN)
