"""Server down / back notices (telegrambot/outage.py)."""

import datetime
import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import outage
from hiddifypanel.panel.commercial.telegrambot.texts import T, t


class FakeRedis:
    def __init__(self):
        self.data = {}
        self.sets = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.data:
            return False
        self.data[key] = str(value).encode()
        return True

    def delete(self, *keys):
        for k in keys:
            self.data.pop(k, None)
            self.sets.pop(k, None)

    def sadd(self, key, *values):
        self.sets.setdefault(key, set()).update(str(v).encode() for v in values)

    def smembers(self, key):
        return self.sets.get(key, set())

    def expire(self, key, ttl):
        pass


class OutageTests(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.now = 1_000_000.0
        self.down: tuple = ()
        self.busy = False
        self.sent: list[tuple[int, str]] = []
        self.admins = [SimpleNamespace(telegram_id=1, lang=None)]
        self.users = [SimpleNamespace(telegram_id=10, lang=None), SimpleNamespace(telegram_id=11, lang=None)]
        self.alerts = {10: True, 11: False}
        user_model = mock.MagicMock()
        user_model.query.filter.return_value.first.return_value = SimpleNamespace(lang=None)
        for p in (
            mock.patch.object(outage, "redis_client", self.redis),
            mock.patch.object(outage, "hconfig", lambda key: "token"),
            mock.patch.object(outage.time, "time", lambda: self.now),
            mock.patch.object(outage.doctor, "down_units", lambda: self.down),
            mock.patch.object(outage, "_busy", lambda: self.busy),
            mock.patch.object(outage, "_admins", lambda: self.admins),
            mock.patch.object(outage, "_recent_users", lambda: self.users),
            mock.patch.object(outage, "User", user_model),
            mock.patch.object(outage, "lang_of", lambda *a, **k: "en"),
            mock.patch.object(outage, "_send", lambda chat, text, markup, lang: self.sent.append((chat, text)) or True),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.notify.alerts_on", lambda chat: self.alerts.get(chat, True)),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
        ):
            p.start()
            self.addCleanup(p.stop)

    def tick(self, minutes=2):
        self.now += minutes * 60
        outage.check()

    def test_a_short_restart_is_not_an_outage(self):
        self.down = ("hiddify-xray",)
        outage.check()
        self.tick()
        self.down = ()
        self.tick()
        self.assertEqual(self.sent, [])

    def test_an_outage_is_told_once_and_its_end_to_the_same_people(self):
        self.down = ("hiddify-xray",)
        outage.check()
        self.tick(3)
        self.assertEqual(self.sent, [])
        self.tick(3)  # 6 minutes down
        self.assertEqual([c for c, _ in self.sent], [1, 10])  # the admin, and the user with alerts on
        self.assertIn("hiddify-xray", self.sent[0][1])
        self.assertIn(t(T.out_user, "en"), self.sent[1][1])
        self.tick()
        self.tick()
        self.assertEqual(len(self.sent), 2)  # nothing more while it stays down
        self.down = ()
        self.tick()
        back = self.sent[2:]
        self.assertEqual(sorted(c for c, _ in back), [1, 10])
        self.assertTrue(any(t(T.back_user, "en") in text for _, text in back))
        self.assertTrue(any("min" in text for c, text in back if c == 1))
        self.tick()
        self.assertEqual(len(self.sent), 4)

    def test_nothing_while_an_apply_runs(self):
        self.down = ("hiddify-xray",)
        self.busy = True
        for _ in range(6):
            self.tick()
        self.assertEqual(self.sent, [])
        self.busy = False
        outage.check()  # the clock starts again after the action
        self.tick(3)
        self.assertEqual(self.sent, [])

    def test_a_user_hears_of_outages_at_most_every_six_hours(self):
        for _ in range(2):
            self.down = ("hiddify-haproxy",)
            outage.check()
            self.tick(6)
            self.down = ()
            self.tick()
        user_notes = [text for c, text in self.sent if c == 10 and t(T.out_user, "en") in text]
        self.assertEqual(len(user_notes), 1)

    def test_no_bot_no_check(self):
        with mock.patch.object(outage, "hconfig", lambda key: ""), mock.patch.object(outage.doctor, "down_units", side_effect=AssertionError("checked")):
            outage.check()


if __name__ == "__main__":
    unittest.main()
