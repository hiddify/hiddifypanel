"""The admin's Telegram bot page API (restapi/v2/admin/telegram_bot_api.py): the bot's state from Telegram, a test
message, and the icons option."""

import unittest
from types import SimpleNamespace
from unittest import mock

from apiflask import APIFlask
from telebot.apihelper import ApiTelegramException

from hiddifypanel.panel.commercial.restapi.v2.admin import telegram_bot_api as api

EXPECTED = "https://panel.example.com/adminpath/api/v1/tgbot/"


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None):
        self.data[key] = value

    def delete(self, key):
        self.data.pop(key, None)


def telegram_error(code):
    return ApiTelegramException("getMe", None, {"error_code": code, "description": "x"})


class PageApiTestCase(unittest.TestCase):
    def setUp(self):
        self.config = {"telegram_bot_token": "1:abc", "telegram_bot_animated_icons": False, "telegram_bot_icon_sets": "", "proxy_path_admin": "adminpath"}
        self.calls = {"getMe": {"id": 7, "first_name": "Hiddify", "username": "hiddify_bot"}, "getWebhookInfo": {"url": EXPECTED, "pending_update_count": 0}}
        self.redis = FakeRedis()
        model = mock.MagicMock()
        model.query.filter.return_value.count.return_value = 3

        def call(method, **params):
            result = self.calls[method]
            if isinstance(result, Exception):
                raise result
            return result

        self.account = SimpleNamespace(telegram_id=None, lang=None)
        patches = [
            mock.patch.object(api, "hconfig", lambda key: self.config.get(key.name)),
            mock.patch.object(api, "_call", call),
            mock.patch.object(api, "_expected_webhook", lambda: ("panel.example.com", EXPECTED)),
            mock.patch.object(api, "redis_client", self.redis),
            mock.patch.object(api, "AdminUser", model),
            mock.patch.object(api, "User", model),
            mock.patch.object(api, "g", SimpleNamespace(account=self.account)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)


class StateTests(PageApiTestCase):
    def test_no_token_asks_telegram_nothing(self):
        self.config["telegram_bot_token"] = ""
        self.calls["getMe"] = AssertionError("called")
        state = api._state()
        self.assertEqual((state["configured"], state["bot"], state["error"]), (False, None, None))

    def test_a_working_bot(self):
        state = api._state()
        self.assertEqual(state["bot"]["username"], "hiddify_bot")
        self.assertEqual(state["webhook"]["matches"], True)
        self.assertEqual(state["webhook"]["domain"], "panel.example.com")
        self.assertEqual((state["admins_connected"], state["users_connected"]), (3, 3))
        self.assertNotIn("adminpath", str(state))  # the admin path never reaches the page

    def test_a_webhook_elsewhere_or_missing(self):
        self.calls["getWebhookInfo"] = {"url": "https://other.example.com/hook", "pending_update_count": 4, "last_error_message": "Connection refused", "last_error_date": 1700000000}
        hook = api._state()["webhook"]
        self.assertEqual((hook["set"], hook["matches"], hook["pending"], hook["last_error"]), (True, False, 4, "Connection refused"))
        self.assertTrue(hook["last_error_at"].startswith("2023-11-1"))
        self.calls["getWebhookInfo"] = {"url": ""}
        self.assertEqual(api._state()["webhook"]["set"], False)

    def test_a_rejected_token_and_an_unreachable_telegram(self):
        self.calls["getMe"] = telegram_error(401)
        self.assertEqual(api._state()["error"], "token_rejected")
        self.calls["getMe"] = ConnectionError("timed out")
        state = api._state()
        self.assertEqual((state["error"], state["bot"]), ("unreachable", None))


class TestMessageTests(PageApiTestCase):
    def setUp(self):
        super().setUp()
        self.app = APIFlask(__name__)
        self.fake_bot = mock.MagicMock()
        p = mock.patch("hiddifypanel.panel.commercial.restapi.v1.tgbot.bot", self.fake_bot)
        p.start()
        self.addCleanup(p.stop)
        for p in (
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.ui.hconfig", lambda key: "en"),
        ):
            p.start()
            self.addCleanup(p.stop)

    def post(self):
        with self.app.test_request_context():
            # login_required is in ``decorators``: only the routed view has it
            return api.TelegramBotTestApi().post()

    def test_not_connected(self):
        self.assertEqual(self.post(), {"ok": False, "error": "not_connected"})
        self.fake_bot.send_message.assert_not_called()

    def test_sent_and_blocked(self):
        self.account.telegram_id = 99
        self.assertEqual(self.post(), {"ok": True, "error": None})
        self.assertEqual(self.fake_bot.send_message.call_args.args[0], 99)
        self.fake_bot.send_message.side_effect = telegram_error(403)
        self.assertEqual(self.post(), {"ok": False, "error": "blocked"})


class IconsApiTests(PageApiTestCase):
    def setUp(self):
        super().setUp()
        self.app = APIFlask(__name__)
        self.saved = {}
        patches = [
            mock.patch.object(api, "set_hconfig", lambda key, value, commit=True: self.saved.__setitem__(key.name, value) or self.config.__setitem__(key.name, value)),
            mock.patch.object(api, "db"),
            mock.patch.object(api, "_forget", lambda *keys: self.saved.__setitem__("forgotten", [k.name for k in keys])),
            mock.patch.object(api, "_icons", lambda load: {"enabled": self.config["telegram_bot_animated_icons"], "sets": self.config["telegram_bot_icon_sets"]}),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def put(self, body):
        with self.app.test_request_context(json=body):
            return api.TelegramBotIconsApi().put()

    def test_saving_turns_on_and_lifts_a_refusal(self):
        from hiddifypanel.panel.commercial.telegrambot import icons

        self.redis.set(icons._REFUSED_KEY, "1")
        self.assertEqual(self.put({"enabled": True})["enabled"], True)
        self.assertIsNone(self.redis.get(icons._REFUSED_KEY))
        self.assertEqual(self.saved["forgotten"], ["telegram_bot_animated_icons", "telegram_bot_icon_sets"])

    def test_set_names_are_cleaned_and_checked(self):
        self.assertEqual(self.put({"sets": " PremiumIcons ,\nRestrictedEmoji ,"})["sets"], "PremiumIcons,RestrictedEmoji")
        from apiflask.exceptions import HTTPError as HTTPException

        for bad in ({"sets": "bad name!"}, {"enabled": "yes"}, {"sets": "a" * 2000}):
            with self.assertRaises(HTTPException):
                self.put(bad)


if __name__ == "__main__":
    unittest.main()
