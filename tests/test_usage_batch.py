"""Usage reports from nodes are counted exactly once, and no usage is lost when a step fails.

Node: the report in flight is kept in the database and sent again unchanged until the parent answers; new usage waits.
Parent: a report is applied and recorded in one transaction; a repeat is answered without adding it again.
"""

from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime
from unittest import mock

import pytest
from flask import Flask

from hiddifypanel.database import db
from hiddifypanel.models import AdminMode, AdminUser, AppliedUsageBatch, Child, ChildMode, UnsyncedUsage, UsageBatchItem, UsageData, User
from hiddifypanel.panel import usage

GB = 1024**3
U1 = "11111111-1111-4111-8111-111111111111"
U2 = "22222222-2222-4222-8222-222222222222"


@pytest.fixture
def app():
    app = Flask("usage-batch-test")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    db.init_app(app)
    with app.app_context():
        db.create_all()
        db.session.add(Child(id=0, name="root", unique_id="root-uid", mode=ChildMode.virtual))
        db.session.add(AdminUser(id=1, uuid="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", name="Owner", mode=AdminMode.super_admin))
        db.session.add(User(uuid=U1, name="u1", usage_limit=100 * GB, package_days=30, added_by=1))
        db.session.add(User(uuid=U2, name="u2", usage_limit=100 * GB, package_days=30, added_by=1))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def quiet():
    """No cores, no Telegram, no periodic reset: only the accounting runs."""
    with ExitStack() as stack:
        stack.enter_context(mock.patch.object(usage.user_driver, "get_enabled_users", return_value={}))
        stack.enter_context(mock.patch.object(usage.user_driver, "add_client"))
        stack.enter_context(mock.patch.object(usage.user_driver, "remove_client"))
        stack.enter_context(mock.patch.object(usage, "_reset_priodic_usage", return_value=False))
        stack.enter_context(mock.patch.object(usage, "send_bot_message"))
        stack.enter_context(mock.patch("hiddifypanel.hutils.apply_users.quick_apply_users"))
        stack.enter_context(mock.patch("hiddifypanel.live.changes.publish"))
        yield


def used(uuid: str) -> int:
    db.session.expire_all()
    return int(db.session.query(User).filter(User.uuid == uuid).one().current_usage or 0)


def waiting() -> dict[str, int]:
    return {r.uuid: int(r.download) for r in UnsyncedUsage.query.all()}


# --------------------------------------------------------------------------- node


def test_node_resends_the_same_report_until_answered(app):
    batch, items = UsageBatchItem.take([UsageData(uuid=U1, download=100)])
    assert batch and [(i.uuid, i.usage) for i in items] == [(U1, 100)] and waiting() == {}

    # no answer: the same report again, the new usage waits
    again, items = UsageBatchItem.take([UsageData(uuid=U1, download=5), UsageData(uuid=U2, download=7)])
    assert again == batch and [(i.uuid, i.usage) for i in items] == [(U1, 100)]
    assert waiting() == {U1: 5, U2: 7}

    UsageBatchItem.answered(batch)
    nxt, items = UsageBatchItem.take([])
    assert nxt and nxt != batch
    assert sorted((i.uuid, i.usage) for i in items) == [(U1, 5), (U2, 7)] and waiting() == {}


def test_node_with_nothing_to_send(app):
    assert UsageBatchItem.take([]) == (None, [])
    UsageBatchItem.answered(None)  # nothing to drop


# --------------------------------------------------------------------------- parent


def test_parent_applies_a_report_once(app, quiet):
    report = [UsageData(uuid=U1, download=300), UsageData(uuid=U2, upload=50)]
    for _ in range(3):  # the node sends it again after lost answers
        res = usage._add_users_usage_new_impl(report, child_id=0, batch_id="b1")
        assert res["status"] == "success"
    assert (used(U1), used(U2)) == (300, 50)
    assert AdminUser.query.get(1).current_usage == 350  # the admins' usage too
    assert AppliedUsageBatch.is_applied(0, "b1")

    usage._add_users_usage_new_impl([UsageData(uuid=U1, download=1)], child_id=0, batch_id="b2")
    assert used(U1) == 301


def test_same_user_twice_in_a_report_is_added_up(app, quiet):
    usage._add_users_usage_new_impl([UsageData(uuid=U1, download=10), UsageData(uuid=U1, upload=5)], child_id=0)
    assert used(U1) == 15


def test_a_failed_save_adds_nothing_and_the_resend_counts_once(app, quiet):
    report = [UsageData(uuid=U1, download=300)]
    with mock.patch.object(AdminUser, "add_usages", side_effect=RuntimeError("db hiccup")):
        with pytest.raises(RuntimeError):
            usage._add_users_usage_new_impl(report, child_id=0, batch_id="b1")
    assert used(U1) == 0 and not AppliedUsageBatch.is_applied(0, "b1")  # rolled back together

    usage._add_users_usage_new_impl(report, child_id=0, batch_id="b1")
    usage._add_users_usage_new_impl(report, child_id=0, batch_id="b1")
    assert used(U1) == 300


def test_cores_failing_after_the_save_do_not_fail_the_report(app, quiet):
    with mock.patch.object(usage, "_sync_cores", side_effect=RuntimeError("xray api down")):
        res = usage._add_users_usage_new_impl([UsageData(uuid=U1, download=300)], child_id=0, batch_id="b1")
    assert res["status"] == "success" and used(U1) == 300 and AppliedUsageBatch.is_applied(0, "b1")


def test_parents_own_usage_is_kept_when_it_cannot_be_saved(app, quiet):
    with (
        mock.patch.object(usage.hutils.node, "is_child", return_value=False),
        mock.patch.object(usage.user_driver, "get_users_usage", side_effect=[{U1: UsageData(uuid=U1, download=40)}, {U1: UsageData(uuid=U1, download=2)}]),
    ):
        with mock.patch.object(usage, "_save_usage", side_effect=RuntimeError("db hiccup")), pytest.raises(RuntimeError):
            usage.update_local_usage_not_lock()
        assert used(U1) == 0 and waiting() == {U1: 40}  # the cores were reset: kept for the next run

        usage.update_local_usage_not_lock()
    assert used(U1) == 42 and waiting() == {}


# --------------------------------------------------------------------------- node and parent together


def test_lost_answers_neither_lose_nor_double_usage(app, quiet):
    """The parent applies each report but its answer is lost twice; usage keeps coming every minute."""
    from hiddifypanel.hutils.node import child
    from hiddifypanel.hutils.node.api_client import NodeApiErrorSchema
    from hiddifypanel.panel.commercial.restapi.v2.parent.schema import UsageResponseSchema

    answers = iter(["lost", "lost", "ok", "ok"])
    apply_on_parent = usage._add_users_usage_new_impl  # the node's own count (while the parent is away) is left out below

    def parent(payload):
        apply_on_parent(payload.usages, child_id=0, batch_id=payload.batch_id)
        if next(answers) == "lost":
            return NodeApiErrorSchema(msg="answer lost")
        return UsageResponseSchema(users=[], response_time=datetime.now(), admin_users=[])

    with (
        mock.patch.object(child, "_send_to_parent", side_effect=parent),
        mock.patch.object(child, "hconfig", return_value=datetime.min),
        mock.patch.object(child, "set_hconfig"),
        mock.patch.object(child, "sync_status"),
        mock.patch.object(child, "_apply_users_if_changed"),
        mock.patch.object(child.usage, "_add_users_usage_new_impl"),
    ):
        results = [child.sync_users_usage_with_parent([UsageData(uuid=U1, download=100)]) for _ in range(4)]

    assert results == [False, False, True, True]
    pending = sum(int(r.download) for r in UnsyncedUsage.query.all()) + sum(int(r.download) for r in UsageBatchItem.query.all())
    assert used(U1) + pending == 400  # every byte counted once: on the parent, or still waiting on the node
    assert used(U1) == 400 and pending == 0
