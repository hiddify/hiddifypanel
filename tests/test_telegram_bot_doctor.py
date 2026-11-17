"""The connection doctor (telegrambot/doctor.py): where the problem is, the services rule, the address check, and
the admins told only once in a while."""

import datetime
import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import doctor, ui
from hiddifypanel.panel.commercial.telegrambot.accounts import Status
from hiddifypanel.panel.commercial.telegrambot.texts import T, t


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True


def user(**kw):
    base = dict(name="Ann", last_online=datetime.datetime.now() - datetime.timedelta(hours=2))
    return SimpleNamespace(**{**base, **kw})


class DiagnoseTests(unittest.TestCase):
    def setUp(self):
        self.status = Status.active
        self.down: tuple = ()
        self.reachable = True
        for p in (
            mock.patch.object(doctor.accounts, "status", lambda u: self.status),
            mock.patch.object(doctor.accounts, "is_online", lambda u: False),
            mock.patch.object(doctor.accounts, "user_host", lambda: "panel.example.com"),
            mock.patch.object(doctor, "down_units", lambda: self.down),
            mock.patch.object(doctor, "address_answers", lambda host: self.reachable),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_the_account_comes_first(self):
        self.status = Status.expired
        self.down = ("hiddify-xray",)
        d = doctor.diagnose(user(), "en")
        self.assertEqual(d.cause, "account")
        self.assertEqual(d.account.text, t(T.dr_account_expired, "en"))

    def test_then_the_server_then_the_address(self):
        self.down = ("hiddify-xray",)
        self.reachable = False
        self.assertEqual(doctor.diagnose(user(), "en").cause, "server")
        self.down = ()
        self.assertEqual(doctor.diagnose(user(), "en").cause, "address")

    def test_nothing_found_gives_tips(self):
        d = doctor.diagnose(user(last_online=datetime.datetime.min), "fa")
        self.assertEqual(d.cause, "")
        self.assertEqual(d.device.text, t(T.dr_device_never, "fa"))
        with mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False):
            screen = doctor.doctor_screen(ui.Ctx(1, "fa"), d)
        self.assertIn(t(T.dr_v_fine, "fa"), screen.text)
        self.assertIn("1. ", screen.text)
        data = [b.callback_data for row in screen.markup.keyboard for b in row]
        self.assertEqual(data, ["dr", "sp", "gd", "bb"])


class UnitsTests(unittest.TestCase):
    def run_with(self, enabled, active):
        outputs = iter([SimpleNamespace(stdout="\n".join(enabled)), SimpleNamespace(stdout="\n".join(active))])
        with mock.patch.object(doctor.subprocess, "run", lambda *a, **k: next(outputs)):
            return doctor.down_units(("a", "b", "c"))

    def test_only_enabled_units_must_run(self):
        self.assertEqual(self.run_with(["enabled", "disabled", "enabled"], ["active", "inactive", "active"]), ())
        self.assertEqual(self.run_with(["enabled", "disabled", "enabled"], ["active", "inactive", "failed"]), ("c",))

    def test_an_odd_answer_is_not_a_problem(self):
        self.assertEqual(self.run_with(["enabled"], ["failed"]), ())


class AddressTests(unittest.TestCase):
    def test_ips_and_names(self):
        self.assertTrue(doctor.address_answers("192.0.2.1"))
        self.assertFalse(doctor.address_answers(""))
        with mock.patch.object(doctor.socket, "getaddrinfo", side_effect=OSError("no")):
            self.assertFalse(doctor.address_answers("nowhere.invalid"))
        with mock.patch.object(doctor.socket, "getaddrinfo", return_value=[("x",)]):
            self.assertTrue(doctor.address_answers("panel.example.com"))


class TellAdminsTests(unittest.TestCase):
    def test_once_in_a_while_and_only_for_the_server(self):
        redis = FakeRedis()
        fake_bot = mock.MagicMock()
        model = mock.MagicMock()
        model.query.filter.return_value.all.return_value = [SimpleNamespace(id=1, telegram_id=5, lang=None)]
        d = doctor.Diagnosis(*(doctor.Finding(doctor.Level.ok, "") for _ in range(4)), cause="server", down=("hiddify-xray",))
        with mock.patch.object(doctor, "redis_client", redis), mock.patch.object(doctor, "bot", fake_bot), mock.patch.object(doctor, "AdminUser", model), mock.patch.object(doctor, "lang_of", lambda *a, **k: "en"):
            doctor.tell_admins(user(), doctor.Diagnosis(*(doctor.Finding(doctor.Level.ok, "") for _ in range(4)), cause="account"))
            fake_bot.send_message.assert_not_called()
            doctor.tell_admins(user(), d)
            doctor.tell_admins(user(), d)
        self.assertEqual(fake_bot.send_message.call_count, 1)
        self.assertIn("hiddify-xray", fake_bot.send_message.call_args.args[1])


class ProgressTests(unittest.TestCase):
    def setUp(self):
        ok = doctor.Finding(doctor.Level.ok, "fine")
        self.bot = mock.MagicMock()

        def fake_diagnose(user, lang, progress=None):
            progress([ok, ok])
            progress([ok, ok, ok])
            return doctor.Diagnosis(ok, ok, ok, ok, cause="")

        for p in (
            mock.patch.object(doctor, "bot", self.bot),
            mock.patch.object(doctor, "diagnose", fake_diagnose),
            mock.patch.object(doctor, "tell_admins", lambda *a: None),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
        ):
            p.start()
            self.addCleanup(p.stop)

    def run_from(self, on_photo):
        ctx = ui.Ctx(1, "en", user=SimpleNamespace(name="Ann"), message_id=9, call_id="c")
        ctx.on_photo = on_photo
        with mock.patch.object(ui.Ctx, "show") as show, mock.patch.object(ui.Ctx, "toast"):
            doctor.run_doctor(ctx, [])
        return show

    def test_from_the_card_each_step_is_a_draft_then_one_message(self):
        show = self.run_from(on_photo=True)
        drafts = self.bot.send_message_draft.call_args_list
        self.assertEqual(len(drafts), 3)
        self.assertEqual(len({c.args[1] for c in drafts}), 1)  # the same draft grows
        self.assertEqual(drafts[2].args[2].count("✅"), 3)
        self.assertEqual(show.call_count, 1)

    def test_a_refused_draft_falls_back_to_edits(self):
        self.bot.send_message_draft.side_effect = RuntimeError("Bad Request: method not available")
        show = self.run_from(on_photo=True)
        self.assertEqual(self.bot.send_message_draft.call_count, 1)
        self.assertEqual(show.call_count, 4)

    def test_from_its_own_screen_it_edits(self):
        show = self.run_from(on_photo=False)
        self.bot.send_message_draft.assert_not_called()
        self.assertEqual(show.call_count, 4)


if __name__ == "__main__":
    unittest.main()
