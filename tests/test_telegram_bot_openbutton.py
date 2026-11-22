"""The bot's "Open" button (Main Mini App): the owner hears when it is missing, with the steps."""

import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import openbutton, ui
from hiddifypanel.panel.commercial.telegrambot.texts import T, t


class FakeRedis(dict):
    def get(self, key):
        return dict.get(self, key)

    def set(self, key, value, **_kw):
        self[key] = value


class Base(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.me = SimpleNamespace(has_main_web_app=False)
        self.asked = 0

        def get_me():
            self.asked += 1
            return self.me

        for p in (
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
            mock.patch.object(openbutton, "redis_client", self.redis),
            mock.patch.object(openbutton, "bot", SimpleNamespace(username="hiddify_bot", get_me=get_me)),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.accounts.panel_app_url", lambda: "https://panel.example.com/p/api/v1/tgbot/app/"),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.owner = ui.Ctx(5, "en", admin=SimpleNamespace(id=1, name="Ann", mode="super_admin"))


class OpenButtonTests(Base):
    def test_missing_button_is_told_to_the_owner(self):
        lines, keys = openbutton.home_notice(self.owner)
        self.assertIn(t(T.oa_missing, "en"), "\n".join(lines))
        self.assertEqual(keys[0][0].callback_data, "oh")

    def test_nothing_once_it_is_set(self):
        self.me.has_main_web_app = True
        self.assertEqual(openbutton.home_notice(self.owner), ([], []))

    def test_not_for_other_admins(self):
        admin = ui.Ctx(6, "en", admin=SimpleNamespace(id=2, name="Bo", mode="admin"))
        self.assertEqual(openbutton.home_notice(admin), ([], []))

    def test_cached_then_asked_again_on_check(self):
        openbutton.has_open_button()
        openbutton.has_open_button()
        self.assertEqual(self.asked, 1)
        self.me.has_main_web_app = True
        self.assertTrue(openbutton.has_open_button(fresh=True))
        self.assertEqual(self.asked, 2)

    def test_steps_name_the_bot_and_give_the_link(self):
        screen = openbutton.help_screen(self.owner)
        self.assertIn("@hiddify_bot", screen.text)
        self.assertIn("https://panel.example.com/p/api/v1/tgbot/app/", screen.text)
        self.assertIn("oh:check", [b.callback_data for row in screen.markup.keyboard for b in row if b.callback_data])


if __name__ == "__main__":
    unittest.main()
