"""The admin's Free Test screen: what the person gets, how it is given, and the invite link to copy or share."""

import unittest
from types import SimpleNamespace
from unittest import mock
from urllib.parse import parse_qs, urlparse

from hiddifypanel.panel.commercial.telegrambot import free, ui
from hiddifypanel.panel.commercial.telegrambot.texts import T, t

LINK = "https://t.me/hiddify_bot?start=free_abc123"


class FreeLinkTests(unittest.TestCase):
    def setUp(self):
        self.shown = []
        for p in (
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
            mock.patch.object(ui.Ctx, "toast", lambda s, text=None, alert=False: None),
            mock.patch.object(ui.Ctx, "show", lambda s, screen: self.shown.append(screen)),
            mock.patch.object(free, "link_of", lambda admin: LINK),
            mock.patch.object(free.free_test, "counts", lambda admin: {"pending": 0}),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.ctx = ui.Ctx(5, "en", admin=SimpleNamespace(id=1, name="Ann", mode="super_admin"))

    def package(self, enabled=True):
        return SimpleNamespace(enabled=enabled, approval="auto", days=7, usage_gb=0.5, owner=None)

    def test_on_with_copy_and_share(self):
        with mock.patch.object(free.free_test, "package_of", lambda admin: self.package()):
            free.show_link(self.ctx, [])
        screen = self.shown[-1]
        for key in (T.free_link_what, T.free_link_how, T.free_link_invite):
            self.assertIn(t(key, "en"), screen.text)
        self.assertIn(f"<code>{LINK}</code>", screen.text)  # a tap on it copies it
        first = screen.markup.keyboard[0]
        self.assertEqual(first[0].copy_text.text, LINK)
        share = parse_qs(urlparse(first[1].url).query)
        self.assertEqual(share["url"], [LINK])  # Telegram's share window with the link
        self.assertEqual(screen.markup.keyboard[-1][0].callback_data, "bb")

    def test_off_says_how_to_turn_it_on(self):
        with mock.patch.object(free.free_test, "package_of", lambda admin: self.package(enabled=False)):
            free.show_link(self.ctx, [])
        screen = self.shown[-1]
        self.assertIn(t(T.free_link_off, "en"), screen.text)
        self.assertNotIn("t.me", screen.text)
        self.assertEqual([b.callback_data for row in screen.markup.keyboard for b in row], ["bb"])


if __name__ == "__main__":
    unittest.main()
