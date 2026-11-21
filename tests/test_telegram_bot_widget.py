"""The live usage card (telegrambot/widget.py): Telegram's widget limits, the sandbox rules, its state, and when it
is updated."""

import datetime
import json
import re
import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import texts, widget
from hiddifypanel.panel.commercial.telegrambot.accounts import Status

GB = 1024**3


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.data:
            return False
        self.data[key] = value if isinstance(value, bytes) else str(value).encode()
        return True


def user(**kw):
    base = dict(id=3, name="Ann", telegram_id=55, lang=None, usage_limit=10 * GB, current_usage=4 * GB, usage_limit_GB=10, current_usage_GB=4.0, start_date=datetime.date.today(), remaining_days=12, package_days=30)
    return SimpleNamespace(**{**base, **kw})


class HtmlTests(unittest.TestCase):
    def test_every_language_fits_telegrams_limits(self):
        for lang in texts.LANGUAGES:
            self.assertTrue(widget.fits(widget.html(lang)), lang)

    def test_only_what_the_sandbox_allows(self):
        markup = widget.html("en")
        for banned in ("color-mix", ":has(", "@font-face", "@import", "http://", "https://", "<link", "<iframe", "vh;", "overflow:auto", "\x00"):
            self.assertNotIn(banned, markup)

    def test_right_to_left_and_words_in_the_language(self):
        self.assertIn('dir="rtl"', widget.html("fa"))
        self.assertIn('dir="ltr"', widget.html("en"))
        self.assertIn(texts.t(texts.T.wg_title, "fa"), widget.html("fa"))
        script = re.search(r"var L=(\{.*?\}),C=", widget.html("fa")).group(1)
        self.assertEqual(json.loads(script)["st"]["active"], texts.t(texts.T.status_active, "fa"))


class StateTests(unittest.TestCase):
    def setUp(self):
        for p in (
            mock.patch.object(widget.accounts, "status", lambda u: Status.active),
            mock.patch.object(widget.accounts, "is_online", lambda u: False),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_short_and_complete(self):
        data = json.loads(widget.state(user(), "fa", datetime.datetime(2026, 11, 17, 9, 5)))
        self.assertEqual((data["s"], data["p"], data["d"], data["D"], data["o"], data["h"]), ("active", 40, 12, 30, 0, "09:05"))
        self.assertLessEqual(len(widget.state(user(), "my").encode()), widget.DATA_MAX)

    def test_not_started_and_huge_usage(self):
        data = json.loads(widget.state(user(start_date=None, current_usage=200 * GB, current_usage_GB=200.0), "en"))
        self.assertEqual((data["d"], data["p"]), (-1, 999))


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.prefs = {(55, "widget"): "777"}
        self.calls = []
        self.status = Status.active
        fake_pref = SimpleNamespace(get=lambda chat, key, default="": self.prefs.get((chat, key), default), put=lambda chat, key, value: self.prefs.__setitem__((chat, key), value))
        for p in (
            mock.patch.object(widget, "redis_client", self.redis),
            mock.patch.object(widget, "BotPref", fake_pref),
            mock.patch.object(widget, "lang_of", lambda *a, **k: "en"),
            mock.patch.object(widget, "_api", lambda method, **params: self.calls.append((method, params)) or {"message_id": 900}),
            mock.patch.object(widget.accounts, "status", lambda u: self.status),
            mock.patch.object(widget.accounts, "is_online", lambda u: False),
            mock.patch("hiddifypanel.database.db"),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_only_a_change_and_not_too_often(self):
        self.assertTrue(widget.refresh(user()))
        self.assertEqual(self.calls[0][1]["message_id"], 777)
        self.assertFalse(widget.refresh(user()))  # nothing changed
        self.assertFalse(widget.refresh(user(current_usage=5 * GB, current_usage_GB=5.0)))  # changed, but too soon
        self.redis.data.pop(widget._THROTTLE.format(3))
        self.assertTrue(widget.refresh(user(current_usage=5 * GB, current_usage_GB=5.0)))
        self.assertEqual(len(self.calls), 2)

    def test_no_card_no_call(self):
        self.prefs.clear()
        self.assertFalse(widget.refresh(user()))
        self.assertEqual(self.calls, [])

    def test_a_deleted_card_is_forgotten(self):
        def gone(method, **params):
            raise RuntimeError("Bad Request: message to edit not found")

        with mock.patch.object(widget, "_api", gone):
            self.assertFalse(widget.refresh(user()))
        self.assertEqual(self.prefs[(55, "widget")], "")

    def test_send_keeps_the_new_card(self):
        self.assertEqual(widget.send(user(), "fa"), 900)
        method, params = self.calls[0]
        self.assertEqual(method, "sendWidget")
        self.assertEqual(params["chat_id"], 55)
        self.assertIn("Ann", params["caption"])
        self.assertEqual(self.prefs[(55, "widget")], "w:900")


class PinnedCardTests(unittest.TestCase):
    """Where Telegram does not allow widgets for the bot yet: a message pinned at the top that the bot edits."""

    def setUp(self):
        self.redis = FakeRedis()
        self.prefs = {}
        self.bot = mock.MagicMock()
        self.bot.send_message.side_effect = lambda *a, **k: SimpleNamespace(message_id=600 + self.bot.send_message.call_count)
        self.api_calls = []

        def api(method, **params):
            self.api_calls.append(method)
            raise RuntimeError("Bad Request: INPUT_MEDIA_WIDGET_NOT_ALLOWED")

        fake_pref = SimpleNamespace(get=lambda chat, key, default="": self.prefs.get((chat, key), default), put=lambda chat, key, value: self.prefs.__setitem__((chat, key), value))
        for p in (
            mock.patch.object(widget, "redis_client", self.redis),
            mock.patch.object(widget, "BotPref", fake_pref),
            mock.patch.object(widget, "bot", self.bot),
            mock.patch.object(widget, "_api", api),
            mock.patch.object(widget, "lang_of", lambda *a, **k: "en"),
            mock.patch.object(widget.accounts, "status", lambda u: Status.active),
            mock.patch.object(widget.accounts, "is_online", lambda u: True),
            mock.patch("hiddifypanel.database.db"),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_refused_widgets_give_a_pinned_card(self):
        self.assertEqual(widget.send(user(), "en"), 601)
        self.assertEqual(self.api_calls, ["sendWidget"])
        self.bot.pin_chat_message.assert_called_once_with(55, 601, disable_notification=True)
        self.assertEqual(self.prefs[(55, "widget")], "t:601")
        self.assertFalse(widget.available())  # tried again tomorrow
        text = self.bot.send_message.call_args.args[1]
        self.assertIn(texts.t(texts.T.wg_title, "en"), text)
        self.assertIn("40%", text)
        self.assertIn("12</b> / 30", text)

    def test_next_time_straight_to_the_pinned_card_and_the_old_one_unpinned(self):
        widget.send(user(), "en")
        widget.send(user(), "en")
        self.assertEqual(self.api_calls, ["sendWidget"])  # not asked again today
        self.bot.unpin_chat_message.assert_called_once_with(55, 601)
        self.assertEqual(self.prefs[(55, "widget")], "t:602")

    def test_the_pinned_card_is_edited_in_place(self):
        widget.send(user(), "en")
        self.assertTrue(widget.refresh(user(current_usage=6 * GB, current_usage_GB=6.0)))
        edit = self.bot.edit_message_text.call_args
        self.assertEqual(edit.args[1:], (55, 601))
        self.assertIn("60%", edit.args[0])


if __name__ == "__main__":
    unittest.main()
