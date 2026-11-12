"""Account passwords are kept as salted hashes: never stored as typed, checked through the hash on every sign-in path,
and the passwords kept before hashing are upgraded (by the migration, or at the next sign-in)."""

from __future__ import annotations

import pytest
from flask import Flask
from sqlalchemy import text

from hiddifypanel import admin_credentials as creds
from hiddifypanel import passwords
from hiddifypanel.database import db
from hiddifypanel.models import AdminMode, AdminUser, Child, ChildMode, User

STRONG = "Tr0ub4dor-and-3"
ADMIN_UUID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
AGENT_UUID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


@pytest.fixture
def app():
    app = Flask("passwords-test")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.secret_key = "test"
    db.init_app(app)
    with app.app_context():
        db.create_all()
        db.session.add(Child(id=0, name="root", unique_id="root-uid", mode=ChildMode.virtual))
        db.session.add(AdminUser(id=1, uuid=ADMIN_UUID, name="Owner", mode=AdminMode.super_admin))
        db.session.add(AdminUser(id=2, uuid=AGENT_UUID, name="Agent", mode=AdminMode.agent, parent_admin_id=1))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


def stored(table: str, row_id: int) -> str:
    return db.session.execute(text(f"SELECT password FROM {table} WHERE id = :id"), {"id": row_id}).scalar() or ""


def agent() -> AdminUser:
    return db.session.get(AdminUser, 2)


def test_a_password_is_stored_as_a_salted_hash(app):
    agent().update_password(STRONG)
    other = db.session.get(AdminUser, 1)
    other.update_password(STRONG)
    saved = stored("admin_user", 2)
    assert STRONG not in saved and saved.startswith(passwords.METHOD + "$")
    assert saved != stored("admin_user", 1)  # its own salt
    assert agent().check_password(STRONG)
    assert not agent().check_password(STRONG + "x")
    assert not agent().check_password("")


def test_no_password_stays_empty_and_only_an_empty_one_matches(app):
    agent().update_password("")
    assert stored("admin_user", 2) == ""
    assert agent().check_password("") and not agent().check_password("anything")


def test_an_old_password_kept_as_typed_still_signs_in_once_and_is_then_hashed(app):
    db.session.execute(text("UPDATE admin_user SET password = :p WHERE id = 2"), {"p": STRONG})
    db.session.commit()
    db.session.expire_all()
    assert not agent().check_password("wrong")
    assert stored("admin_user", 2) == STRONG  # a wrong one changes nothing
    assert agent().check_password(STRONG)
    db.session.commit()
    assert stored("admin_user", 2).startswith(passwords.METHOD + "$")
    assert agent().check_password(STRONG)


def test_a_new_password_is_never_answered_from_the_memo(app):
    agent().update_password(STRONG)
    assert agent().check_password(STRONG)  # remembered
    agent().update_password("An0ther-strong-one")
    assert not agent().check_password(STRONG)
    assert agent().check_password("An0ther-strong-one")


def test_username_and_password_sign_in(app):
    user = User(name="u", username="alice")
    user.password = STRONG
    db.session.add(user)
    db.session.commit()
    assert STRONG not in stored("user", user.id)
    assert User.by_username_password("alice", STRONG).id == user.id
    assert User.by_username_password("alice", "wrong") is None
    assert User.by_username_password("alice", "") is None
    assert User.by_username_password("", STRONG) is None


def test_admin_sign_in_by_link_and_by_alias(app):
    a = agent()
    a.alias = "agent-one"
    a.update_password(STRONG)
    assert a.password_strong
    assert creds.check_admin_login(AGENT_UUID, STRONG).id == 2
    assert creds.check_admin_login("agent-one", STRONG).id == 2
    assert creds.check_admin_login("agent-one", "wrong") is None
    assert creds.alias_problem("agent-one", a) is None

    a.update_password("weakweak")  # weak: no sign in by alias, and no alias
    assert not a.password_strong
    assert creds.check_admin_login(AGENT_UUID, "weakweak").id == 2
    assert creds.check_admin_login("agent-one", "weakweak") is None
    assert creds.alias_problem("agent-one", a) == "weak_password"


def test_the_migration_hashes_every_password_kept_as_typed(app):
    from hiddifypanel.panel import init_db

    user = User(name="u", username="bob")
    db.session.add(user)
    db.session.commit()
    db.session.execute(text("UPDATE admin_user SET password = :p, password_strong = 0 WHERE id = 2"), {"p": STRONG})
    db.session.execute(text("UPDATE user SET password = 'generated-0123456789' WHERE id = :id"), {"id": user.id})
    db.session.commit()
    db.session.expire_all()

    init_db._v208(0)
    db.session.expire_all()

    assert stored("admin_user", 2).startswith(passwords.METHOD + "$")
    assert stored("admin_user", 1) == ""  # no password: none made up
    assert agent().password_strong  # noted from the password before it was hashed
    assert passwords.is_hashed(stored("user", user.id)) and "generated" not in stored("user", user.id)
    assert User.by_username_password("bob", "generated-0123456789").id == user.id
    db.session.expire_all()
    assert stored("user", user.id).startswith(passwords.METHOD + "$")  # full strength after its sign-in
    init_db._v208(0)  # again: nothing hashed twice
    assert User.by_username_password("bob", "generated-0123456789").id == user.id
