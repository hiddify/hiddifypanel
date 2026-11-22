"""Advanced mode: the subscribers group (only active users get in; ended ones leave)."""

import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import guard


class FakeBot:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args))
            if name == "get_chat_member":
                return SimpleNamespace(status="member")
            if name == "create_chat_invite_link":
                return SimpleNamespace(invite_link="https://t.me/+join")
            return None

        return call


class Base(unittest.TestCase):
    def setUp(self):
        self.bot = FakeBot()
        for p in (
            mock.patch.object(guard, "bot", self.bot),
            mock.patch.object(guard, "allowed", lambda: True),
            mock.patch.object(guard, "group_id", lambda: -100),
            mock.patch.object(guard, "with_retry", lambda call, attempts=2: call()),
            mock.patch.object(guard, "hconfig", lambda key: "x"),
        ):
            p.start()
            self.addCleanup(p.stop)

    def names(self):
        return [c[0] for c in self.bot.calls]


class JoinTests(Base):
    def request(self, tg_id):
        return SimpleNamespace(chat=SimpleNamespace(id=-100), from_user=SimpleNamespace(id=tg_id, language_code="en"), user_chat_id=tg_id)

    def test_active_users_get_in(self):
        with mock.patch.object(guard, "_active_account", lambda tg: True):
            guard.on_join_request(self.request(7))
        self.assertEqual(self.names(), ["approve_chat_join_request"])

    def test_others_are_declined_and_told(self):
        with mock.patch.object(guard, "_active_account", lambda tg: False):
            guard.on_join_request(self.request(8))
        self.assertEqual(self.names(), ["decline_chat_join_request", "send_message"])

    def test_another_group_is_not_ours(self):
        r = self.request(7)
        r.chat.id = -555
        guard.on_join_request(r)
        self.assertEqual(self.names(), [])


class ConnectTests(Base):
    def message(self, sender):
        return SimpleNamespace(chat=SimpleNamespace(id=-100, type="supergroup"), from_user=SimpleNamespace(id=sender))

    def test_only_the_owner_connects_it(self):
        owner = SimpleNamespace(telegram_id=5, lang=None)
        model = mock.MagicMock()
        model.get_super_admin.return_value = owner
        with mock.patch.object(guard, "AdminUser", model), mock.patch.object(guard, "lang_of", lambda *a, **k: "en"):
            guard.connect(self.message(9))
            self.assertEqual(self.names(), [])
            with mock.patch.object(guard, "BotPref", mock.MagicMock()) as pref, mock.patch("hiddifypanel.database.db.session", mock.MagicMock()):
                guard.connect(self.message(5))
        self.assertIn("create_chat_invite_link", self.names())
        pref.put.assert_any_call(0, "adv_guard_chat", "-100")


class SweepTests(Base):
    def test_ended_users_leave(self):
        ended = SimpleNamespace(id=1, telegram_id=11, lang=None)
        active = SimpleNamespace(id=2, telegram_id=12, lang=None)
        users = mock.MagicMock(**{"query.filter.return_value.order_by.return_value.all.return_value": [active, ended]})
        admins = mock.MagicMock(**{"query.filter.return_value.first.return_value": None})
        status = {1: guard.accounts.Status.expired, 2: guard.accounts.Status.active}
        with mock.patch.object(guard, "User", users), mock.patch.object(guard, "AdminUser", admins), mock.patch.object(guard.accounts, "status", lambda u: status[u.id]), mock.patch.object(
            guard, "redis_client", SimpleNamespace(set=lambda *a, **k: True)
        ), mock.patch.object(guard, "lang_of", lambda *a, **k: "en"):
            guard.sweep()
        self.assertEqual(self.names(), ["get_chat_member", "ban_chat_member", "unban_chat_member", "send_message"])
        self.assertEqual(self.bot.calls[1][1], (-100, 11))


if __name__ == "__main__":
    unittest.main()
