"""Staged usage alerts (telegrambot/notify.py) and the user's settings screen (settings.py)."""

import datetime
import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import notify, settings, ui
from hiddifypanel.panel.commercial.telegrambot.accounts import Status
from hiddifypanel.panel.commercial.telegrambot.texts import T, t

GB = 1024**3


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None, nx=False):
        self.data[key] = str(value).encode()
        return True


def user(used_gb=0.0, days_left=30, **kw):
    u = SimpleNamespace(
        id=7, name="Ann", telegram_id=55, lang=None, usage_limit=10 * GB, current_usage=int(used_gb * GB),
        usage_limit_GB=10, current_usage_GB=used_gb, start_date=datetime.date.today(), remaining_days=days_left,
    )
    u.__dict__.update(kw)
    return u


class AlertTests(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.bot = mock.MagicMock()
        self.prefs = {}
        self.status = Status.active
        for p in (
            mock.patch.object(notify, "redis_client", self.redis),
            mock.patch.object(notify, "bot", self.bot),
            mock.patch.object(notify, "alerts_on", lambda chat: self.prefs.get(chat, True)),
            mock.patch.object(notify.accounts, "status", lambda u: self.status),
            mock.patch.object(notify.accounts, "links", lambda u: SimpleNamespace(home="https://panel.example.com/p/u/")),
            mock.patch.object(notify, "lang_of", lambda *a, **k: "en"),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
        ):
            p.start()
            self.addCleanup(p.stop)

    def texts(self):
        return [c.args[1] for c in self.bot.send_message.call_args_list]

    def test_each_data_stage_once(self):
        self.assertFalse(notify.alert(user(7.9)))
        self.assertTrue(notify.alert(user(8.0)))
        self.assertFalse(notify.alert(user(8.5)))  # still 80%: nothing again
        self.assertTrue(notify.alert(user(9.2)))
        self.assertFalse(notify.alert(user(9.9)))
        self.assertEqual(len(self.texts()), 2)
        self.assertIn("<b>80%</b>", self.texts()[0])
        self.assertIn("<b>92%</b>", self.texts()[1])

    def test_a_renewal_arms_it_again(self):
        notify.alert(user(9.0))
        notify.alert(user(0.5))  # renewed: back to stage 0
        self.assertTrue(notify.alert(user(8.1)))
        self.assertEqual(len(self.texts()), 2)

    def test_days_only_in_the_daily_run(self):
        self.assertFalse(notify.alert(user(days_left=3)))
        self.assertTrue(notify.alert(user(days_left=3), days=True))
        self.assertTrue(notify.alert(user(days_left=1), days=True))
        self.assertIn(t(T.alert_last_day, "en", name="Ann"), self.texts()[-1])
        self.assertFalse(notify.alert(user(days_left=0), days=True))

    def test_off_means_silent_but_the_stage_is_kept(self):
        self.prefs[55] = False
        self.assertFalse(notify.alert(user(8.0)))
        self.prefs[55] = True
        self.assertFalse(notify.alert(user(8.4)))  # no burst when turned back on
        self.assertTrue(notify.alert(user(9.0)))

    def test_not_for_an_ended_or_unlinked_account(self):
        self.status = Status.no_data
        self.assertFalse(notify.alert(user(11)))
        self.status = Status.active
        self.assertFalse(notify.alert(user(9, telegram_id=None)))
        self.bot.send_message.assert_not_called()

    def test_a_failure_is_swallowed(self):
        self.bot.send_message.side_effect = RuntimeError("blocked")
        self.assertFalse(notify.alert(user(8.0)))

    def test_the_alert_can_turn_alerts_off(self):
        notify.alert(user(8.0))
        markup = self.bot.send_message.call_args.kwargs["reply_markup"].to_dict()
        data = [b.get("callback_data") for row in markup["inline_keyboard"] for b in row]
        self.assertIn("pf:alerts:0", data)


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.on = True
        for p in (
            mock.patch.object(notify, "alerts_on", lambda chat: self.on),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
        ):
            p.start()
            self.addCleanup(p.stop)

    def data(self, screen):
        return [b.callback_data for row in screen.markup.keyboard for b in row]

    def test_the_screen_shows_the_state_and_the_opposite_button(self):
        ctx = ui.Ctx(55, "fa", user=SimpleNamespace())
        screen = settings.settings_screen(ctx)
        self.assertIn(t(T.on, "fa"), screen.text)
        self.assertEqual(self.data(screen), ["lg", "pf:alerts:0:s", "bb"])
        self.on = False
        self.assertIn("pf:alerts:1:s", self.data(settings.settings_screen(ctx)))

    def test_set_pref_keeps_only_known_values(self):
        ctx = ui.Ctx(55, "en", user=SimpleNamespace())
        stored = {}
        fake_pref = SimpleNamespace(put=lambda chat, key, value: stored.__setitem__((chat, key), value))
        with mock.patch("hiddifypanel.models.BotPref", fake_pref), mock.patch.object(settings, "db"), mock.patch.object(ui.Ctx, "toast"), mock.patch.object(ui.Ctx, "show") as show:
            settings.set_pref(ctx, ["alerts", "x"])
            settings.set_pref(ctx, ["evil", "1"])
            self.assertEqual(stored, {})
            settings.set_pref(ctx, ["alerts", "0"])
            show.assert_not_called()  # from an alert: the alert message stays as it is
            settings.set_pref(ctx, ["alerts", "1", "s"])
            show.assert_called_once()
        self.assertEqual(stored, {(55, "alerts"): "1"})


if __name__ == "__main__":
    unittest.main()
