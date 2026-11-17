"""Message effects (ui.celebrate, send_card festive) and where they are used (notify.status_changed)."""

import unittest
from types import SimpleNamespace
from unittest import mock

from telebot.apihelper import ApiTelegramException

from hiddifypanel.panel.commercial.telegrambot import notify, ui


def refusal(text):
    return ApiTelegramException("sendMessage", None, {"error_code": 400, "description": f"Bad Request: {text}"})


class CelebrateTests(unittest.TestCase):
    def test_confetti_is_added(self):
        send = mock.MagicMock(return_value="ok")
        self.assertEqual(ui.celebrate(send, 1, "hi", reply_markup=None), "ok")
        send.assert_called_once_with(1, "hi", reply_markup=None, message_effect_id=ui.EFFECT_CONFETTI)

    def test_a_refused_effect_is_sent_again_without_it(self):
        send = mock.MagicMock(side_effect=[refusal("EFFECT_ID_INVALID"), "ok"])
        self.assertEqual(ui.celebrate(send, 1, "hi"), "ok")
        self.assertEqual(send.call_args_list[1], mock.call(1, "hi"))

    def test_other_errors_still_raise(self):
        send = mock.MagicMock(side_effect=refusal("chat not found"))
        with self.assertRaises(ApiTelegramException):
            ui.celebrate(send, 1, "hi")
        self.assertEqual(send.call_count, 1)


class SendCardTests(unittest.TestCase):
    def test_festive_only_when_asked(self):
        fake_bot = mock.MagicMock()
        # the classic photo (a rich card refused): its own confetti
        with mock.patch.object(ui, "bot", fake_bot), mock.patch("hiddifypanel.panel.commercial.telegrambot.qr.render", lambda data: b"png"), mock.patch("hiddifypanel.panel.commercial.telegrambot.rich.send_card", lambda *a, **k: None):
            ui.send_card(1, ui.Screen("t", None, qr="x"))
            ui.send_card(1, ui.Screen("t", None, qr="x"), festive=True)
            ui.send_card(1, ui.Screen("t"), festive=True)
        photo_calls = fake_bot.send_photo.call_args_list
        self.assertNotIn("message_effect_id", photo_calls[0].kwargs)
        self.assertEqual(photo_calls[1].kwargs["message_effect_id"], ui.EFFECT_CONFETTI)
        self.assertEqual(fake_bot.send_message.call_args.kwargs["message_effect_id"], ui.EFFECT_CONFETTI)


    def test_a_card_is_one_rich_message_with_its_confetti(self):
        got = []
        raw = {"message_id": 7, "date": 0, "chat": {"id": 1, "type": "private"}, "rich_message": {"blocks": []}}
        with (
            mock.patch("hiddifypanel.panel.commercial.telegrambot.qr.render", lambda data: b"png"),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.rich.send_card", lambda *a, **k: got.append(k) or raw),
            mock.patch.object(ui, "bot") as fake_bot,
        ):
            sent = ui.send_card(1, ui.Screen("t", None, qr="x"), festive=True)
        self.assertEqual(sent.message_id, 7)
        self.assertEqual(got[0]["effect"], ui.EFFECT_CONFETTI)
        fake_bot.send_photo.assert_not_called()


class StatusNoticeTests(unittest.TestCase):
    def test_confetti_when_on_again_not_when_it_ends(self):
        fake_bot = mock.MagicMock()
        with (
            mock.patch.object(notify, "bot", fake_bot),
            mock.patch.object(notify, "hconfig", lambda key: "token"),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.user.account_card", lambda user, lang: "CARD"),
            mock.patch.object(notify.accounts, "links", lambda user: SimpleNamespace(home="https://panel.example.com/u/")),
            mock.patch.object(notify, "lang_of", lambda *a, **k: "en"),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
        ):
            notify.status_changed(SimpleNamespace(telegram_id=5, uuid="u", is_active=True))
            notify.status_changed(SimpleNamespace(telegram_id=5, uuid="u", is_active=False))
        on, off = fake_bot.send_message.call_args_list
        self.assertEqual(on.kwargs.get("message_effect_id"), ui.EFFECT_CONFETTI)
        self.assertNotIn("message_effect_id", off.kwargs)


if __name__ == "__main__":
    unittest.main()
