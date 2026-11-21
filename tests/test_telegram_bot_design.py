"""The Telegram bot's design system: button colours, animated icons from custom emoji sets, and the fallback to
plain emoji when Telegram refuses the icons (telegrambot/icons.py, ui.py)."""

import json
import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import icons, ui

MAP = {"👥": "111", "🔄": "222", "➕": "333", "♻": "444", "🚫": "555"}


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None):
        self.data[key] = value


class IconsTestCase(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.config = {"telegram_bot_animated_icons": True, "telegram_bot_icon_sets": ""}
        patches = [
            mock.patch.object(icons, "redis_client", self.redis),
            mock.patch.object(icons, "hconfig", lambda key: self.config.get(key.name)),
            mock.patch.object(icons, "icon_map", lambda: MAP),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)


class SplitTests(IconsTestCase):
    def test_a_known_leading_emoji_becomes_the_icon(self):
        self.assertEqual(icons.split("👥 Users"), ("111", "Users"))

    def test_the_variation_selector_does_not_matter(self):
        self.assertEqual(icons.split("♻️ Renew"), ("444", "Renew"))

    def test_an_emoji_no_set_has_stays_in_the_label(self):
        self.assertEqual(icons.split("📷 QR"), (None, "📷 QR"))

    def test_an_emoji_no_set_has_borrows_a_close_one(self):
        # 🗑 is in no set: ❌ is not either, 🚫 is
        self.assertEqual(icons.split("🗑 Delete"), ("555", "Delete"))

    def test_a_label_without_an_emoji_is_unchanged(self):
        self.assertEqual(icons.split("‹ Back"), (None, "‹ Back"))
        self.assertEqual(icons.split("Users"), (None, "Users"))

    def test_icons_off_keep_every_label(self):
        self.config["telegram_bot_animated_icons"] = False
        self.assertEqual(icons.split("👥 Users"), (None, "👥 Users"))

    def test_a_refusal_turns_them_off(self):
        self.redis.set(icons._REFUSED_KEY, "1")
        self.assertEqual(icons.split("👥 Users"), (None, "👥 Users"))

    def test_sets_come_from_the_setting_in_order(self):
        self.assertEqual(icons.sets(), icons.DEFAULT_SETS)
        self.config["telegram_bot_icon_sets"] = " PremiumIcons , RestrictedEmoji\nMajorEmojis "
        self.assertEqual(icons.sets(), ("PremiumIcons", "RestrictedEmoji", "MajorEmojis"))


class LoadMapTests(unittest.TestCase):
    def test_the_first_set_that_has_an_emoji_wins_and_the_map_is_kept(self):
        redis = FakeRedis()
        sticker = lambda emoji, cid: SimpleNamespace(emoji=emoji, custom_emoji_id=cid)
        sets = {
            "A": SimpleNamespace(stickers=[sticker("👥", "a1"), sticker("⭐️", "a2")]),
            "B": SimpleNamespace(stickers=[sticker("👥", "b1"), sticker("🔄", "b2")]),
        }
        fake_bot = mock.MagicMock()
        fake_bot.get_sticker_set.side_effect = lambda name: sets[name] if name in sets else (_ for _ in ()).throw(RuntimeError("no set"))
        with mock.patch.object(icons, "redis_client", redis), mock.patch("hiddifypanel.panel.commercial.telegrambot.bot", fake_bot):
            found = icons._load_map(("Missing", "A", "B"))
            self.assertEqual(found, {"👥": "a1", "⭐": "a2", "🔄": "b2"})
            fake_bot.get_sticker_set.reset_mock()
            self.assertEqual(icons._load_map(("Missing", "A", "B")), found)
            fake_bot.get_sticker_set.assert_not_called()


class ButtonTests(IconsTestCase):
    def test_style_and_icon_go_on_the_button(self):
        button = ui.btn("➕ New user", ui.Cb.new, 0, 0, 0, style=ui.Style.success).to_dict()
        self.assertEqual(button["text"], "New user")
        self.assertEqual(button["icon_custom_emoji_id"], "333")
        self.assertEqual(button["style"], "success")
        self.assertEqual(button["callback_data"], "nw:0:0:0")

    def test_blue_only_inside_a_rich_message(self):
        # A classic keyboard draws blue as blue text on light blue (unreadable); buttons inside a rich message draw it
        # well. The button keeps it, and rich.classic() takes it off whatever stays a classic keyboard.
        import json

        from hiddifypanel.panel.commercial.telegrambot import rich

        button = ui.btn("Open", ui.Cb.me, style=ui.Style.primary).to_dict()
        self.assertEqual(button["style"], "primary")
        keys = json.dumps({"inline_keyboard": [[button, ui.url_btn("Open", "https://panel.example.com/x", ui.Style.primary).to_dict()]]})
        classic = json.loads(rich.classic({"reply_markup": keys})["reply_markup"])["inline_keyboard"][0]
        self.assertTrue(all("style" not in b for b in classic))

    def test_without_icons_or_style_the_button_is_as_before(self):
        self.config["telegram_bot_animated_icons"] = False
        button = ui.btn("➕ New user", ui.Cb.new, 0, 0, 0).to_dict()
        self.assertEqual(button, {"text": "➕ New user", "callback_data": "nw:0:0:0"})

    def test_url_and_app_buttons_take_style_too(self):
        self.assertEqual(ui.url_btn("🔗 Links", "https://example.com", ui.Style.success).to_dict()["style"], "success")
        app = ui.app_btn("🔄 Open", "https://panel.example.com/x", ui.Style.danger).to_dict()
        self.assertEqual((app["text"], app["icon_custom_emoji_id"], app["style"]), ("Open", "222", "danger"))


class RefusalTests(IconsTestCase):
    def test_strip_icons_puts_the_emoji_back(self):
        markup = {"inline_keyboard": [[{"text": "Users", "icon_custom_emoji_id": "111", "callback_data": "ul"}, {"text": "‹ Back", "callback_data": "h"}]]}
        stripped = json.loads(icons.strip_icons(json.dumps(markup)))
        self.assertEqual(stripped["inline_keyboard"][0][0], {"text": "👥 Users", "callback_data": "ul"})
        self.assertEqual(stripped["inline_keyboard"][0][1], {"text": "‹ Back", "callback_data": "h"})

    def test_a_borrowed_icon_gives_its_own_emoji_back(self):
        markup = {"inline_keyboard": [[{"text": "Delete", "icon_custom_emoji_id": "555", "callback_data": "x"}]]}
        self.assertEqual(json.loads(icons.strip_icons(json.dumps(markup)))["inline_keyboard"][0][0]["text"], "🗑 Delete")

    def test_no_alias_is_a_label_emoji(self):
        from hiddifypanel.panel.commercial.telegrambot import accounts, texts

        labels = {icons._norm(m.group(1)) for text in texts._table("en").values() if (m := icons._LEADING_EMOJI.match(text))}
        labels |= {icons._norm(e) for e in accounts.STATUS_ICON.values()}
        borrowed = {icons._norm(a) for options in icons.ALIASES.values() for a in options}
        self.assertEqual(borrowed & labels, set())

    def _guard(self, original):
        from telebot import apihelper

        with mock.patch.object(apihelper, "_make_request", original):
            icons.install_refusal_guard()
            return apihelper._make_request

    def test_a_refused_icon_is_sent_again_without_it_and_icons_go_off(self):
        from telebot import apihelper

        calls = []

        def original(token, method_name, method="get", params=None, files=None):
            calls.append(params)
            if "icon_custom_emoji_id" in params["reply_markup"]:
                raise apihelper.ApiTelegramException(method_name, None, {"error_code": 400, "description": "Bad Request: BUTTON_ICON_CUSTOM_EMOJI_INVALID"})
            return {"ok": True}

        markup = json.dumps({"inline_keyboard": [[{"text": "Users", "icon_custom_emoji_id": "111", "callback_data": "ul"}]]})
        guarded = self._guard(original)
        self.assertEqual(guarded("T", "sendMessage", "post", {"chat_id": 1, "reply_markup": markup}), {"ok": True})
        self.assertEqual(len(calls), 2)
        self.assertNotIn("icon_custom_emoji_id", calls[1]["reply_markup"])
        self.assertIn("👥 Users", calls[1]["reply_markup"])
        self.assertTrue(self.redis.get(icons._REFUSED_KEY))
        self.assertFalse(icons.enabled())

    def test_icons_dropped_silently_get_the_emoji_back_and_go_off(self):
        calls = []

        def original(token, method_name, method="get", params=None, files=None):
            calls.append((method_name, params))
            if method_name == "sendMessage":  # accepted, but the icons are gone (no Premium)
                return {"message_id": 5, "chat": {"id": 1}, "reply_markup": {"inline_keyboard": [[{"text": "Users", "callback_data": "ul"}]]}}
            return {"ok": True}

        markup = json.dumps({"inline_keyboard": [[{"text": "Users", "icon_custom_emoji_id": "111", "callback_data": "ul"}]]})
        self._guard(original)("T", "sendMessage", "post", {"chat_id": 1, "reply_markup": markup})
        self.assertEqual([c[0] for c in calls], ["sendMessage", "editMessageReplyMarkup"])
        self.assertEqual((calls[1][1]["chat_id"], calls[1][1]["message_id"]), (1, 5))
        self.assertIn("👥 Users", calls[1][1]["reply_markup"])
        self.assertFalse(icons.enabled())

    def test_icons_kept_by_telegram_change_nothing(self):
        calls = []

        def original(token, method_name, method="get", params=None, files=None):
            calls.append(method_name)
            return {"message_id": 5, "chat": {"id": 1}, "reply_markup": {"inline_keyboard": [[{"text": "Users", "icon_custom_emoji_id": "111", "callback_data": "ul"}]]}}

        markup = json.dumps({"inline_keyboard": [[{"text": "Users", "icon_custom_emoji_id": "111", "callback_data": "ul"}]]})
        self._guard(original)("T", "sendMessage", "post", {"chat_id": 1, "reply_markup": markup})
        self.assertEqual(calls, ["sendMessage"])
        self.assertTrue(icons.enabled())

    def test_other_errors_are_not_retried(self):
        from telebot import apihelper

        def original(token, method_name, method="get", params=None, files=None):
            raise apihelper.ApiTelegramException(method_name, None, {"error_code": 403, "description": "Forbidden: bot was blocked by the user"})

        guarded = self._guard(original)
        with self.assertRaises(apihelper.ApiTelegramException):
            guarded("T", "sendMessage", "post", {"chat_id": 1, "reply_markup": json.dumps({"inline_keyboard": [[{"text": "x", "icon_custom_emoji_id": "1"}]]})})
        self.assertIsNone(self.redis.get(icons._REFUSED_KEY))


if __name__ == "__main__":
    unittest.main()
