"""The bot in groups (telegrambot/groups.py, handlers.on_other): /me answers the asker only, other things are left
alone. Updates go through the bot's real handlers; Telegram's API is recorded, not called."""

import json
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from telebot import apihelper, types

from hiddifypanel.panel.commercial.restapi.v1.tgbot import bot
from hiddifypanel.panel.commercial.telegrambot import groups, handlers
from hiddifypanel.panel.commercial.telegrambot.texts import T, t

GROUP = -100123


class GroupTests(unittest.TestCase):
    def setUp(self):
        self.sent = []

        def fake(token, method_name, method="get", params=None, files=None):
            self.sent.append((method_name, dict(params or {})))
            return {"message_id": 1, "date": 0, "chat": {"id": GROUP, "type": "supergroup"}} if method_name == "sendMessage" else True

        self.user = None
        user_model = mock.MagicMock()
        user_model.query.filter.return_value.first.side_effect = lambda: self.user
        admin_model = mock.MagicMock()
        admin_model.query.filter.return_value.first.return_value = None
        for p in (
            mock.patch.object(apihelper, "_make_request", fake),
            mock.patch.object(groups, "User", user_model),
            mock.patch.object(groups, "AdminUser", admin_model),
            mock.patch.object(groups, "lang_of", lambda *a, **k: "en"),
            mock.patch.object(groups.accounts, "links", lambda u: SimpleNamespace(page="https://panel.example.com/u/#Ann")),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.user.account_card", lambda u, lang: "CARD of " + u.name),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
            mock.patch.object(handlers, "context", mock.MagicMock(return_value=SimpleNamespace(chat_id=5, lang="en", admin=None, user=None, tr=lambda k: t(k, "en")))),
        ):
            p.start()
            self.addCleanup(p.stop)
        bot.username = "crawl_bot"

    def feed(self, chat_type, **message):
        update = {"update_id": int(time.time() * 1000) % 10**9, "message": {"message_id": 5, "date": 0, "chat": {"id": GROUP if chat_type != "private" else 7, "type": chat_type}, "from": {"id": 7, "is_bot": False, "first_name": "Ann", "language_code": "en"}, **message}}
        bot.process_new_updates([types.Update.de_json(update)])

    def command(self, chat_type="supergroup", text="/me"):
        self.feed(chat_type, text=text, entities=[{"type": "bot_command", "offset": 0, "length": len(text)}])

    def sends(self):
        return [p for m, p in self.sent if m == "sendMessage"]

    def test_me_answers_only_the_asker(self):
        self.user = SimpleNamespace(name="Ann")
        self.command()
        (sent,) = self.sends()
        self.assertEqual(sent["text"], "CARD of Ann")
        self.assertEqual(json.loads(sent["ephemeral_message_parameters"])["receiver_user_id"], 7)
        self.assertIn("deleteMessage", [m for m, _ in self.sent])

    def test_a_stranger_is_shown_the_way_in(self):
        self.command(text="/me@crawl_bot")
        (sent,) = self.sends()
        self.assertIn(t(T.grp_not_linked, "en"), sent["text"])
        self.assertIn("https://t.me/crawl_bot?start=start", sent["reply_markup"])
        self.assertIn("receiver_user_id", sent["ephemeral_message_parameters"])

    def test_stickers_and_photos_in_a_group_get_no_answer(self):
        self.feed("supergroup", sticker={"file_id": "x", "file_unique_id": "x", "type": "regular", "width": 1, "height": 1, "is_animated": False, "is_video": False})
        self.feed("group", photo=[{"file_id": "x", "file_unique_id": "x", "width": 1, "height": 1}])
        self.assertEqual(self.sends(), [])

    def test_a_sticker_in_private_says_how_to_write_to_support(self):
        # not while writing a message to support: it stays here, and one line says how to write one
        from hiddifypanel.panel.commercial.telegrambot import support

        for p in (mock.patch.object(support, "relay_media", lambda ctx, message: False), mock.patch.object(handlers.free_test, "current_conversation", lambda chat, user: object())):
            p.start()
            self.addCleanup(p.stop)
        self.feed("private", sticker={"file_id": "x", "file_unique_id": "x", "type": "regular", "width": 1, "height": 1, "is_animated": False, "is_video": False})
        self.assertEqual(len(self.sends()), 1)


if __name__ == "__main__":
    unittest.main()
