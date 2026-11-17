"""Telegram bot fixes: no raw error reaches a person, messages sent outside an update speak the person's language,
the on/off notice keeps the account card, big broadcasts go out after the answer, and the server check and the Mini
App page are translated (telegrambot/handlers.py, settings.py, free.py, notify.py, status.py, webapp.py,
restapi/v1/tgmsg.py)."""

import json
import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.models import Lang
from hiddifypanel.panel.commercial.telegrambot import free, handlers, notify, settings, status, texts, ui, webapp
from hiddifypanel.panel.commercial.telegrambot.texts import T, t


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None, nx=False):
        self.data[key] = value


class FakeCtx(ui.Ctx):
    """A Ctx whose show / toast are recorded (Ctx itself has slots)."""


def fake_ctx(lang="en", **kw):
    c = FakeCtx(42, lang, **kw)
    c.show = mock.MagicMock()
    c.toast = mock.MagicMock()
    return c


def patch(test, *patches):
    started = [p.start() for p in patches]
    for p in patches:
        test.addCleanup(p.stop)
    return started


class ErrorToastTests(unittest.TestCase):
    def test_a_failing_button_shows_a_plain_sentence_not_the_error(self):
        c = fake_ctx("fa", admin=SimpleNamespace())

        def boom(ctx, args):
            raise RuntimeError("secret path /opt/x and token 123:abc")

        db = mock.MagicMock()
        patch(
            self,
            mock.patch.object(handlers, "context", lambda *a, **k: c),
            mock.patch.dict(ui.ROUTES, {ui.Cb.check: ui.Route(boom, admin=True)}),
            mock.patch.object(handlers, "db", db),
        )
        message = mock.MagicMock(spec=handlers.types.Message, chat=SimpleNamespace(id=42), message_id=7, content_type="text")
        call = SimpleNamespace(data=ui.Cb.check.value, id="9", from_user=None, message=message)
        handlers.on_button(call)
        text = c.toast.call_args_list[0].args[0]
        self.assertIn(t(T.error_generic, "fa"), text)
        self.assertNotIn("secret", text)
        self.assertTrue(c.toast.call_args_list[0].kwargs.get("alert"))
        db.session.rollback.assert_called_once()


class PersonLangTests(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        patch(self, mock.patch.object(settings, "redis_client", self.redis), mock.patch.object(ui, "hconfig", lambda key: "en"))

    def test_the_account_language_comes_first(self):
        settings.remember_telegram_lang(42, "fa")
        self.assertEqual(settings.person_lang(42, SimpleNamespace(lang=Lang.ru)), "ru")

    def test_then_the_language_chosen_in_the_bot_then_the_telegram_one(self):
        settings.remember_telegram_lang(42, "fa-IR")
        self.assertEqual(settings.person_lang(42), "fa")
        self.redis.set(settings._CHAT_LANG.format(42), b"de")
        self.assertEqual(settings.person_lang(42, SimpleNamespace(lang=None)), "de")

    def test_then_the_panel_default(self):
        settings.remember_telegram_lang(42, "xx")
        self.assertEqual(settings.person_lang(42), "en")

    def test_a_stranger_update_keeps_their_telegram_language(self):
        model = mock.MagicMock()
        model.query.filter.return_value.first.return_value = None
        patch(self, mock.patch.object(handlers, "AdminUser", model), mock.patch.object(handlers, "User", model))
        self.assertEqual(handlers.context(42, telegram_lang="ru").lang, "ru")
        self.assertEqual(settings.person_lang(42), "ru")


class ConversationLangTests(unittest.TestCase):
    def test_the_support_answer_and_the_decline_go_in_the_person_language(self):
        redis = FakeRedis()
        patch(
            self,
            mock.patch.object(settings, "redis_client", redis),
            mock.patch.object(ui, "hconfig", lambda key: "en"),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
        )
        settings.remember_telegram_lang(55, "fa")
        conv = SimpleNamespace(telegram_id=55, user_uuid=None, id=3)
        fake_bot = mock.MagicMock()
        with mock.patch.object(free, "bot", fake_bot):
            free.tell_declined(conv)
        self.assertIn(t(T.free_declined, "fa"), fake_bot.send_message.call_args.args[1])

    def test_an_account_language_wins(self):
        account = SimpleNamespace(lang=Lang.ru)
        with mock.patch.object(free.User, "by_uuid", lambda uuid: account):
            self.assertEqual(free._conv_lang(SimpleNamespace(telegram_id=55, user_uuid="u")), "ru")


class StatusNoticeTests(unittest.TestCase):
    def setUp(self):
        self.bot = mock.MagicMock()
        self.config = {"telegram_bot_token": "x"}
        patch(
            self,
            mock.patch.object(notify, "bot", self.bot),
            mock.patch.object(notify, "hconfig", lambda key: self.config.get(key.name)),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.user.account_card", lambda user, lang: "CARD"),
            mock.patch.object(notify.accounts, "links", lambda user: SimpleNamespace(home="https://example.com/u/")),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
        )

    def user(self, active):
        return SimpleNamespace(telegram_id=42, uuid="u", is_active=active, lang=Lang.fa)

    def test_on_and_off_both_keep_the_card_in_the_user_language(self):
        notify.status_changed(self.user(True))
        text = self.bot.send_message.call_args.args[1]
        self.assertIn(t(T.notify_on, "fa"), text)
        self.assertIn("CARD", text)
        notify.status_changed(self.user(False))
        text = self.bot.send_message.call_args.args[1]
        self.assertIn(t(T.notify_off, "fa"), text)
        self.assertIn("CARD", text)

    def test_nothing_without_a_chat_or_a_bot(self):
        notify.status_changed(SimpleNamespace(telegram_id=None, uuid="u", is_active=True, lang=None))
        self.config["telegram_bot_token"] = ""
        notify.status_changed(self.user(True))
        self.bot.send_message.assert_not_called()

    def test_a_refusal_never_stops_the_usage_update(self):
        self.bot.send_message.side_effect = RuntimeError("blocked")
        notify.status_changed(self.user(True))


class BroadcastTests(unittest.TestCase):
    def setUp(self):
        from hiddifypanel.panel.commercial.restapi.v1 import tgmsg

        self.tgmsg = tgmsg
        self.bot = mock.MagicMock()
        patch(
            self,
            mock.patch.object(tgmsg, "bot", self.bot),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.Usage.get_usage_msg", lambda uuid: "CARD"),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.Usage.user_keyboard", lambda uuid: None),
        )

    def test_each_error_is_kept_and_the_others_still_get_it(self):
        self.bot.send_message.side_effect = [RuntimeError("blocked"), None]
        errors = self.tgmsg._send_all([("a", "Ann", 1), ("b", "Bob", 2)], "Hi")
        self.assertEqual(list(errors), ["a"])
        self.assertEqual(self.bot.send_message.call_args.args, (2, "Hi\n\nCARD"))


class CheckReportTests(unittest.TestCase):
    def test_labels_are_translated_outside_the_monospaced_table(self):
        patch(
            self,
            mock.patch("hiddifypanel.hutils.network.get_ip_str", lambda v: "192.0.2.1" if v == 4 else None),
            mock.patch.object(status, "_geo", lambda ip: {"country": "Germany", "code": "DE", "city": "Berlin", "org": "<Org>"}),
            mock.patch.object(status, "service_states", lambda: {"hiddify-panel": "active", "hiddify-xray": "failed"}),
        )
        text = status.check_text(fake_ctx("fa"))
        pre = text[text.index("<pre>") :]
        for key in (T.check_ip, T.check_country, T.check_city, T.check_services):
            self.assertIn(t(key, "fa"), text)
            self.assertNotIn(t(key, "fa"), pre)
        self.assertIn("&lt;Org&gt;", text)
        self.assertIn("✅", pre)
        self.assertIn("❌", pre)


class ServicesTests(unittest.TestCase):
    def test_each_service_with_its_time_memory_and_restarts(self):
        out = "\n\n".join(
            [
                "Id=hiddify-xray.service\nLoadState=loaded\nActiveState=active\nSubState=running\nActiveEnterTimestampMonotonic=1000000\nMemoryCurrent=52428800\nNRestarts=2",
                "Id=hiddify-mysql.service\nLoadState=loaded\nActiveState=failed\nSubState=failed\nActiveEnterTimestampMonotonic=0\nMemoryCurrent=[not set]\nNRestarts=0",
                "Id=wg-quick@hiddifywg.service\nLoadState=not-found\nActiveState=inactive\nSubState=dead",
            ]
        )
        patch(
            self,
            mock.patch.object(status.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=out)),
            mock.patch.object(status, "_monotonic_now_us", lambda: 3_601_000_000),
        )
        lines = status._services_lines(fake_ctx("en"))
        self.assertIn(t(T.st_running, "en", ok=1, n=2), lines[0])  # a unit not installed is not counted
        self.assertIn("⚠️", lines[0])
        body = lines[1]
        self.assertIn("✅ <b>xray</b>", body)
        self.assertIn("50.0 MB", body)
        self.assertIn("↻ 2", body)
        self.assertIn("❌ <b>mysql</b> · failed (failed)", body)
        self.assertNotIn("wg-quick", body)
        self.assertTrue(body.startswith("<blockquote expandable>"))

    def test_a_process_shows_only_its_programs_name(self):
        self.assertEqual(status._process_name("/usr/bin/redis-server 127.0.0.1:6379"), "redis-server")
        self.assertEqual(status._process_name(""), "?")

    def test_rates(self):
        self.assertEqual(status._rate(1536, "en"), "1.5 KB/s")
        self.assertEqual(status._rate(10, "en"), "10 B/s")


class MiniAppPageTests(unittest.TestCase):
    def test_every_language_is_in_the_page_and_nothing_closes_the_script(self):
        with mock.patch("hiddifypanel.models.hconfig", lambda key: "fa"):
            html = webapp.page()
        payload = html[html.index("const TEXTS = ") + len("const TEXTS = ") : html.index(", RTL = ")]
        found = json.loads(payload.replace("<\\/", "</"))
        self.assertEqual(set(found), set(texts.LANGUAGES))
        self.assertEqual(found["fa"]["failed"], t(T.app_sign_in_failed, "fa"))
        self.assertIn("'fa'", html[html.index("const lang") :])
        self.assertNotIn("__TEXTS__", html)
        self.assertNotIn("__DEFAULT__", html)
        self.assertNotIn("</", payload)


class TranslationTests(unittest.TestCase):
    def test_english_and_persian_have_every_bot_text(self):
        for lang in ("en", "fa"):
            table = texts._table(lang)
            missing = [key.value for key in T if key.value not in table]
            self.assertEqual(missing, [], lang)

    def test_placeholders_match_english(self):
        import re

        names = lambda s: sorted(re.findall(r"{(\w+)}", s))
        en = texts._table("en")
        for lang in ("fa",):
            table = texts._table(lang)
            wrong = [key.value for key in T if key.value in table and names(table[key.value]) != names(en.get(key.value, ""))]
            self.assertEqual(wrong, [], lang)


if __name__ == "__main__":
    unittest.main()
