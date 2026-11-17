"""The links screen (telegrambot/user.links_screen): no long addresses, a copy button per link."""

import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import ui, user
from hiddifypanel.panel.commercial.telegrambot.texts import T, t

HOME = "https://panel.example.com/p/0000/"
LINKS = SimpleNamespace(home=HOME, page=HOME + "#Ann", sub=HOME + "sub/?asn=unknown#Ann", hiddify="hiddify://import/" + HOME + "#Ann")


class LinksScreenTests(unittest.TestCase):
    def setUp(self):
        self.links = LINKS
        for p in (
            mock.patch.object(user.accounts, "links", lambda u: self.links),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
        ):
            p.start()
            self.addCleanup(p.stop)

    def buttons(self, screen):
        return [b.to_dict() for row in screen.markup.keyboard for b in row]

    def test_each_link_folded_in_its_own_box_with_its_colour(self):
        screen = user.links_screen(SimpleNamespace(name="<Ann>"), "fa", [ui.btn("back", ui.Cb.back)])
        self.assertEqual(screen.text.count("<blockquote expandable>"), 3)
        for mark, link in (("🔵", LINKS.sub), ("🟢", LINKS.hiddify), ("🟣", LINKS.page)):
            self.assertIn(f"<blockquote expandable>{mark} ", screen.text)
            self.assertIn(f"<code>{link}</code>", screen.text)  # tap to copy
        self.assertLess(screen.text.index("🔵"), screen.text.index("🟢"))
        self.assertIn("&lt;Ann&gt;", screen.text)
        buttons = self.buttons(screen)
        self.assertFalse([b for b in buttons if "copy_text" in b])  # no copy buttons
        self.assertEqual([b.get("url") or b.get("callback_data") for b in buttons], [LINKS.page, "bb"])
        self.assertLess(len(screen.text), 4096)

    def test_the_admin_rows_come_last(self):
        screen = user.links_screen(SimpleNamespace(name="Ann"), "en", [ui.btn("QR", ui.Cb.qr, 3)], [ui.btn("back", ui.Cb.card, 3)])
        self.assertEqual([b.get("callback_data") for b in self.buttons(screen)][-2:], ["qr:3", "uc:3"])


if __name__ == "__main__":
    unittest.main()
