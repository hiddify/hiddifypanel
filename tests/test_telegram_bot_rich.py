"""Buttons inside the message (telegrambot/rich.py): a text message with a keyboard is sent as a rich message,
its text as rich HTML and its rows as soft pill buttons; anything Telegram refuses goes as it was."""

import json
import unittest
from types import SimpleNamespace
from unittest import mock

from telebot import apihelper

from hiddifypanel.panel.commercial.telegrambot import rich


class BodyTests(unittest.TestCase):
    def test_lines_paragraphs_quotes_and_code(self):
        text = "👥 <b>Users</b>\n<i>31 users</i>\n\n<blockquote expandable>a\nb</blockquote>\n<pre>x\ny</pre>\nend"
        self.assertEqual(
            rich.body_html(text),
            "<p>👥 <b>Users</b><br><i>31 users</i></p><blockquote expandable>a<br>b</blockquote><pre><code>x\ny</code></pre><p>end</p>",
        )

    def test_buttons_and_their_colours(self):
        markup = {"inline_keyboard": [
            [{"text": "✅ Create", "callback_data": "ng:1:2:3", "style": "success"}, {"text": "🗑 Delete", "callback_data": "ua:5:del", "style": "danger"}],
            [{"text": "‹ Back", "callback_data": "bb"}, {"text": "🌐 Page", "url": "https://panel.example.com/p/?a=1&b=2"}],
            [{"text": "📋 Copy <link>", "copy_text": {"text": "vless://x"}}],
        ]}
        page = rich.rich_html("Hi", markup)
        self.assertIn('<tg-button type="callback_data" data="ng:1:2:3" style="success">✅ Create</tg-button>', page)
        self.assertIn('style="danger"', page)
        self.assertIn('<tg-button type="callback_data" data="bb" style="link">‹ Back</tg-button>', page)  # no colour: soft grey
        self.assertIn('url="https://panel.example.com/p/?a=1&amp;b=2" style="primary"', page)  # a link: blue
        self.assertIn('<tg-button type="copy_text" text="vless://x">📋 Copy &lt;link&gt;</tg-button>', page)
        self.assertEqual(page.count("<tg-button-row>"), 3)

    def test_a_kind_rich_buttons_do_not_take_keeps_the_classic_keyboard(self):
        self.assertIsNone(rich.rich_html("x", {"inline_keyboard": [[{"text": "Pay", "pay": True}]]}))


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.refuse = set()

        def request(token, method_name, method="get", params=None, files=None):
            self.calls.append((method_name, params))
            if method_name in self.refuse:
                raise apihelper.ApiTelegramException(method_name, None, {"error_code": 400, "description": "Bad Request: refused"})
            return {"message_id": 9, "chat": {"id": 5}}

        for p in (mock.patch.object(apihelper, "_make_request", request), mock.patch.object(rich, "_off", lambda: False), mock.patch.object(rich, "_turn_off")):
            p.start()
            self.addCleanup(p.stop)
        rich.install()
        self.keys = json.dumps({"inline_keyboard": [[{"text": "Go", "callback_data": "h", "style": "primary"}]]})

    def test_a_message_with_buttons_goes_rich(self):
        apihelper._make_request("t", "sendMessage", "post", {"chat_id": 5, "text": "<b>Hi</b>", "parse_mode": "HTML", "reply_markup": self.keys, "disable_notification": True})
        method, params = self.calls[-1]
        self.assertEqual(method, "sendRichMessage")
        self.assertTrue(params["disable_notification"])
        self.assertNotIn("reply_markup", params)
        self.assertIn('style="primary">Go</tg-button>', json.loads(params["rich_message"])["html"])

    def test_refused_it_goes_classic_without_blue(self):
        self.refuse = {"sendRichMessage"}
        apihelper._make_request("t", "sendMessage", "post", {"chat_id": 5, "text": "Hi", "reply_markup": self.keys})
        method, params = self.calls[-1]
        self.assertEqual(method, "sendMessage")
        self.assertNotIn("style", json.loads(params["reply_markup"])["inline_keyboard"][0][0])  # blue on blue: none
        rich._turn_off.assert_called_once()

    def test_an_older_classic_message_is_edited_classic(self):
        self.refuse = {"editMessageText_rich"}
        calls = []

        def request(token, method_name, method="get", params=None, files=None):
            calls.append(params)
            if "rich_message" in params:
                raise apihelper.ApiTelegramException(method_name, None, {"error_code": 400, "description": "Bad Request: can't edit"})
            return True

        with mock.patch.object(apihelper, "_make_request", request):
            rich.install()
            apihelper._make_request("t", "editMessageText", "post", {"chat_id": 5, "message_id": 3, "text": "Hi", "reply_markup": self.keys})
        self.assertIn("rich_message", calls[0])
        self.assertEqual(calls[1]["text"], "Hi")

    def test_not_modified_is_not_retried(self):
        def request(token, method_name, method="get", params=None, files=None):
            raise apihelper.ApiTelegramException(method_name, None, {"error_code": 400, "description": "Bad Request: message is not modified"})

        with mock.patch.object(apihelper, "_make_request", request):
            rich.install()
            with self.assertRaises(apihelper.ApiTelegramException):
                apihelper._make_request("t", "editMessageText", "post", {"chat_id": 5, "message_id": 3, "text": "Hi", "reply_markup": self.keys})

    def test_a_photo_and_a_reply_keyboard_stay_classic(self):
        apihelper._make_request("t", "sendPhoto", "post", {"chat_id": 5, "caption": "c", "reply_markup": self.keys})
        self.assertEqual(self.calls[-1][0], "sendPhoto")
        self.assertNotIn("style", self.calls[-1][1]["reply_markup"])
        reply_keys = json.dumps({"keyboard": [[{"text": "Menu"}]]})
        apihelper._make_request("t", "sendMessage", "post", {"chat_id": 5, "text": "x", "reply_markup": reply_keys})
        self.assertEqual(self.calls[-1][0], "sendMessage")



class CardTests(unittest.TestCase):
    def test_an_odd_answer_means_the_classic_photo(self):
        with mock.patch.object(apihelper, "_make_request", lambda *a, **k: True), mock.patch.object(rich, "_off", lambda: False):
            self.assertIsNone(rich.send_card(5, "card", {"inline_keyboard": [[{"text": "Go", "callback_data": "h"}]]}, b"png"))

    def test_the_photo_goes_inside_the_message(self):
        got = []

        def request(token, method_name, method="get", params=None, files=None):
            got.append((method_name, params, files))
            return {"message_id": 3, "chat": {"id": 5}}

        with mock.patch.object(apihelper, "_make_request", request), mock.patch.object(rich, "_off", lambda: False):
            self.assertEqual(rich.send_card(5, "card", None, b"png")["message_id"], 3)
        method, params, files = got[0]
        rich_message = json.loads(params["rich_message"])
        self.assertEqual(method, "sendRichMessage")
        self.assertTrue(rich_message["html"].startswith('<img src="tg://photo?id=card"/>'))
        self.assertEqual(rich_message["media"][0]["media"]["media"], "attach://card")
        self.assertIn("card", files)



class DocumentTests(unittest.TestCase):
    def test_the_file_goes_on_top_with_its_name(self):
        import io

        got = []

        def request(token, method_name, method="get", params=None, files=None):
            got.append((method_name, params, files))
            return {"message_id": 4, "chat": {"id": 5}}

        keys = {"inline_keyboard": [[{"text": "🔒 panel.example.com", "url": "https://panel.example.com/p/", "style": "success"}], [{"text": "✖️ Close", "callback_data": "x"}]]}
        with mock.patch.object(apihelper, "_make_request", request), mock.patch.object(rich, "_off", lambda: False):
            self.assertEqual(rich.send_document(5, "💾 <b>Backup</b>", keys, io.BytesIO(b"{}"), "2026.11.18_03.12.json")["message_id"], 4)
        method, params, files = got[0]
        page = json.loads(params["rich_message"])
        self.assertEqual(method, "sendRichMessage")
        self.assertTrue(page["html"].startswith('<tg-document src="tg://document?id=file"/>'))
        self.assertIn('style="success"', page["html"])
        self.assertEqual(files["file"][0], "2026.11.18_03.12.json")


class PictureTests(unittest.TestCase):
    def ctx(self, on_photo=False):
        from types import SimpleNamespace

        from hiddifypanel.panel.commercial.telegrambot import ui

        c = ui.Ctx(5, "en", user=SimpleNamespace(), message_id=40, call_id="c")
        c.on_photo = on_photo
        return c

    def test_in_place_new_or_the_classic_photo(self):
        from hiddifypanel.panel.commercial.telegrambot import ui

        state = mock.MagicMock()
        with mock.patch.object(ui.Ctx, "state", property(lambda s: state)), mock.patch.object(ui, "bot") as fake_bot:
            with mock.patch.object(rich, "edit_card", lambda *a, **k: True):
                self.assertIsNone(ui.show_picture(self.ctx(), b"png", "t", None, in_place=True))  # the screen became the chart
            with mock.patch.object(rich, "send_card", lambda *a, **k: {"message_id": 41}):
                self.assertEqual(ui.show_picture(self.ctx(), b"png", "t", None, in_place=False), (41, False))  # a new rich one
            fake_bot.send_photo.return_value = SimpleNamespace(message_id=42)
            with mock.patch.object(rich, "send_card", lambda *a, **k: None):
                self.assertEqual(ui.show_picture(self.ctx(), b"png", "t", None, in_place=False), (42, True))  # refused: classic
            self.assertIsNone(ui.show_picture(self.ctx(on_photo=True), b"png", "t", None, in_place=True))  # an older photo: its media
            fake_bot.edit_message_media.assert_called_once()


if __name__ == "__main__":
    unittest.main()
