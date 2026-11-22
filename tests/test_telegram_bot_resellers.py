"""Advanced mode: an agent's own bot (managed bots): the shared code answers from it, for their accounts only."""

import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.restapi.v1.tgbot import bot, managed_bot
from hiddifypanel.panel.commercial.telegrambot import resellers, ui

M = resellers.Managed(77, "agent", 4, "shop_vpn_bot")


class TokenTests(unittest.TestCase):
    def test_the_agents_bot_during_its_update(self):
        before = bot.token
        mark = managed_bot.set(M)
        try:
            self.assertEqual(bot.token, M.token)
            self.assertEqual(bot.username, "shop_vpn_bot")
        finally:
            managed_bot.reset(mark)
        self.assertEqual(bot.token, before)

    def test_setting_the_token_keeps_the_panels(self):
        before = bot.token
        try:
            bot.token = "1:pnl"
            mark = managed_bot.set(M)
            self.assertEqual(bot.token, M.token)
            managed_bot.reset(mark)
            self.assertEqual(bot.token, "1:pnl")
        finally:
            bot.token = before

    def test_chat_state_apart_per_bot(self):
        self.assertEqual(ui.ChatState(5)._key, "tgbot:state:5")
        mark = managed_bot.set(M)
        try:
            self.assertEqual(ui.ChatState(5)._key, "tgbot:state:m77:5")
        finally:
            managed_bot.reset(mark)


class ScopeTests(unittest.TestCase):
    def setUp(self):
        agent = SimpleNamespace(id=4, deleted=False, recursive_sub_admins_ids=lambda: [4, 9])
        p = mock.patch("hiddifypanel.models.AdminUser.by_id", lambda i: agent if i == 4 else None, create=True)
        try:
            p.start()
        except Exception:
            model = mock.MagicMock()
            model.by_id = lambda i: agent if i == 4 else None
            p = mock.patch("hiddifypanel.models.AdminUser", model)
            p.start()
        self.addCleanup(p.stop)

    def test_everyone_in_the_panels_bot(self):
        self.assertIsNone(resellers.scope_ids())
        self.assertTrue(resellers.user_in_scope(SimpleNamespace(added_by=1)))

    def test_only_the_agents_tree_in_their_bot(self):
        mark = managed_bot.set(M)
        try:
            self.assertEqual(resellers.scope_ids(), {4, 9})
            self.assertTrue(resellers.user_in_scope(SimpleNamespace(added_by=9)))
            self.assertFalse(resellers.user_in_scope(SimpleNamespace(added_by=1)))
            self.assertTrue(resellers.admin_in_scope(SimpleNamespace(id=4)))
            self.assertFalse(resellers.admin_in_scope(SimpleNamespace(id=1)))  # not even the owner
        finally:
            managed_bot.reset(mark)

    def test_secret_follows_the_token(self):
        self.assertNotEqual(resellers.webhook_secret("a:1"), resellers.webhook_secret("a:2"))
        self.assertEqual(len(resellers.webhook_secret("a:1")), 48)


class SwitchTests(unittest.TestCase):
    def test_needs_its_own_switch(self):
        with mock.patch("hiddifypanel.panel.commercial.telegrambot.advanced.feature", lambda key: False):
            ctx = ui.Ctx(5, "en", admin=SimpleNamespace(id=4, name="Shop", mode="agent"))
            self.assertEqual(resellers.settings_rows(ctx), [])


if __name__ == "__main__":
    unittest.main()
