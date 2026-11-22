"""The bot's Open button (Main Mini App) signs people in: only Telegram's own signature counts, it is fresh, and each
Telegram account reaches only the account linked to it: an admin their panel, a person their own page, nobody else's."""

import hashlib
import hmac
import json
import time
import unittest
from types import SimpleNamespace
from unittest import mock
from urllib.parse import urlencode

from hiddifypanel.panel.commercial.telegrambot import webapp

BOT_KEY = "test-only-signing-key"  # stands for the bot's own key (never a real one)


def signed(user_id: int, *, key: str = BOT_KEY, age: int = 0, tamper: bool = False) -> str:
    fields = {"auth_date": str(int(time.time()) - age), "query_id": "q", "user": json.dumps({"id": user_id, "first_name": "A"})}
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    derived = hmac.new(b"WebAppData", key.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(derived, check.encode(), hashlib.sha256).hexdigest()
    if tamper:  # someone changes the id to another person's after Telegram signed it
        fields["user"] = json.dumps({"id": user_id + 1, "first_name": "A"})
    return urlencode(fields)


class SignatureTests(unittest.TestCase):
    def test_only_telegrams_fresh_signature_counts(self):
        self.assertEqual(webapp.telegram_user_id(signed(42), BOT_KEY), 42)
        self.assertIsNone(webapp.telegram_user_id(signed(42, tamper=True), BOT_KEY))  # another id slipped in
        self.assertIsNone(webapp.telegram_user_id(signed(42, key="another-bots-key"), BOT_KEY))  # signed for another bot
        self.assertIsNone(webapp.telegram_user_id(signed(42, age=2 * 3600), BOT_KEY))  # an old copy
        self.assertIsNone(webapp.telegram_user_id("user=%7B%22id%22%3A42%7D", BOT_KEY))  # no signature at all
        self.assertIsNone(webapp.telegram_user_id("", BOT_KEY))


class DestinationTests(unittest.TestCase):
    def setUp(self):
        self.admins = {7: SimpleNamespace(id=1, telegram_id=7)}
        self.users = {8: SimpleNamespace(id=5, telegram_id=8, uuid="u-8")}

        def model(rows):
            m = mock.MagicMock()
            m.query.filter.side_effect = lambda cond, *rest: SimpleNamespace(first=lambda: rows.get(cond.right.value))
            m.telegram_id = mock.MagicMock()
            m.telegram_id.__eq__ = lambda _s, v: SimpleNamespace(right=SimpleNamespace(value=v))
            m.deleted.is_.return_value = True
            return m

        for p in (
            mock.patch("hiddifypanel.models.AdminUser", model(self.admins)),
            mock.patch("hiddifypanel.models.User", model(self.users)),
            mock.patch("hiddifypanel.models.hconfig", lambda key: "admin-path"),
            mock.patch("hiddifypanel.panel.hiddify.get_account_panel_link", lambda user, host: f"https://{host}/p/{user.uuid}/#home"),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_only_known_panel_pages_get_into_the_address(self):
        self.assertEqual(webapp.destination(7, "panel.example.com", "scanner")[2]["redirect"], "/admin-path/admin/v2/scanner")
        self.assertEqual(webapp.destination(7, "panel.example.com", "../../evil")[2]["redirect"], "/admin-path/admin/v2/")
        self.assertNotIn("scanner", webapp.destination(8, "panel.example.com", "scanner")[2]["redirect"])  # a person: their own page

    def test_each_one_reaches_only_their_own(self):
        kind, account, answer = webapp.destination(7, "panel.example.com")
        self.assertEqual((kind, account.id), ("admin", 1))
        self.assertNotIn("keep_telegram", answer)  # the admin panel's address never carries Telegram's data

        kind, account, answer = webapp.destination(8, "panel.example.com")
        self.assertEqual((kind, account.id), ("user", 5))
        self.assertIn("/p/u-8/", answer["redirect"])  # their own page, by their own key
        self.assertNotIn("admin", answer["redirect"])
        self.assertTrue(answer["keep_telegram"])

        kind, account, answer = webapp.destination(9, "panel.example.com")  # linked to nothing
        self.assertEqual((kind, account), ("none", None))
        self.assertNotIn("redirect", answer)

    def test_the_page_asks_for_full_screen_on_a_phone_and_marks_the_tab(self):
        self.assertIn("sessionStorage.setItem('hiddify.tg', '1')", webapp.PAGE)
        self.assertIn("tg.requestFullscreen()", webapp.PAGE)
        self.assertIn("tg.platform === 'ios' || tg.platform === 'android'", webapp.PAGE)

    def test_the_page_passes_telegrams_data_only_where_allowed(self):
        self.assertIn("body.keep_telegram ? body.redirect.split('#')[0] + location.hash : body.redirect", webapp.PAGE)


if __name__ == "__main__":
    unittest.main()
