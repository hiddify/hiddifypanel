"""Advanced mode: update the panel of this server or of a node from the bot."""

import json
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import ui, updates
from hiddifypanel.panel.commercial.telegrambot.texts import T, t

ADV = "hiddifypanel.panel.commercial.telegrambot.advanced.is_on"


class FakeRedis:
    def __init__(self):
        self.h = {}

    def hset(self, name, key, value):
        self.h[key] = value

    def hgetall(self, name):
        return dict(self.h)

    def hdel(self, name, key):
        self.h.pop(key, None)


def node(id, name, ok=True, version="14.5.0"):
    return SimpleNamespace(id=id, name=name, ok=ok, host=SimpleNamespace(panel_version=version))


class Base(unittest.TestCase):
    def setUp(self):
        self.shown, self.toasts = [], []
        self.redis = FakeRedis()
        self.servers = [node(0, "this-server"), node(2, "Berlin"), node(3, "Paris", ok=False)]
        for p in (
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
            mock.patch(ADV, lambda: True),
            mock.patch.object(ui.Ctx, "toast", lambda s, text=None, alert=False: self.toasts.append(text)),
            mock.patch.object(ui.Ctx, "show", lambda s, screen: self.shown.append(screen)),
            mock.patch.object(updates, "_servers", lambda: list(self.servers)),
            mock.patch.object(updates, "redis_client", self.redis),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.ctx = ui.Ctx(5, "en", admin=SimpleNamespace(id=1, name="Ann", mode="super_admin"), message_id=70)


class ScreenTests(Base):
    def test_green_online_red_offline(self):
        updates.show_update(self.ctx, [])
        keys = [b for row in self.shown[-1].markup.keyboard for b in row]
        self.assertEqual([(b.callback_data, b.to_dict().get("style")) for b in keys[:3]], [("up:0", "success"), ("up:2", "success"), ("up:3", "danger")])

    def test_an_offline_one_cannot_be_updated(self):
        updates.show_update(self.ctx, ["3"])
        self.assertEqual(self.toasts[-1], t(T.up_cannot_offline, "en"))
        self.assertEqual(self.shown, [])

    def test_asks_first(self):
        updates.show_update(self.ctx, ["2"])
        self.assertIn(t(T.up_confirm, "en"), self.shown[-1].text)
        self.assertIn("up:2:go", [b.callback_data for row in self.shown[-1].markup.keyboard for b in row])

    def test_super_admins_only(self):
        agent = ui.Ctx(6, "en", admin=SimpleNamespace(id=2, name="Bo", mode="admin"))
        updates.show_update(agent, [])
        self.assertEqual(self.shown, [])


class StartTests(Base):
    def test_start_waits_and_is_watched(self):
        with mock.patch.object(updates, "start", lambda ctx, n: (True, 1000.0)), mock.patch("hiddifypanel.panel.commercial.telegrambot.miniapp.needs_unlock", lambda *a: False):
            updates.show_update(self.ctx, ["2", "go"])
        self.assertIn(t(T.up_running, "en", name="Berlin"), self.shown[-1].text)
        entry = json.loads(self.redis.h["5:70"])
        self.assertEqual((entry["server"], entry["server_started"]), (2, 1000.0))

    def test_not_started_says_so(self):
        with mock.patch.object(updates, "start", lambda ctx, n: (False, 0.0)), mock.patch("hiddifypanel.panel.commercial.telegrambot.miniapp.needs_unlock", lambda *a: False):
            updates.show_update(self.ctx, ["2", "go"])
        self.assertEqual(self.toasts[-1], t(T.up_not_started, "en"))
        self.assertEqual(self.redis.h, {})


class OutcomeTests(unittest.TestCase):
    def entry(self, ago):
        now = time.time()
        return {"started": now - ago, "server_started": now - ago}

    def test_each_case(self):
        now = time.time()
        e = self.entry(600)
        self.assertIsNone(updates.outcome(e, {"running": ["update"]}, now))  # still running
        self.assertIsNone(updates.outcome(e, None, now))  # restarting: cannot be asked
        self.assertIsNone(updates.outcome(self.entry(30), {"running": [], "last": {}}, now))  # just started
        self.assertIsNone(updates.outcome(e, {"running": [], "last": {"update": {"mtime": now - 10_000, "finished": True}}}, now))  # an older log
        self.assertEqual(updates.outcome(e, {"running": [], "last": {"update": {"mtime": now, "finished": True}}}, now), "ok")
        self.assertEqual(updates.outcome(e, {"running": [], "last": {"update": {"mtime": now, "finished": False}}}, now), "failed")
        self.assertEqual(updates.outcome(self.entry(updates.WATCH_FOR + 5), {"running": ["update"]}, now), "unknown")

    def test_the_message_says_how_it_ended(self):
        redis = FakeRedis()
        redis.hset("x", "5:70", json.dumps({"chat": 5, "msg": 70, "server": 2, "name": "Berlin", "lang": "en", "started": time.time() - 600, "server_started": time.time() - 600}))
        edited = []
        fake_bot = SimpleNamespace(username="b", edit_message_text=lambda text, chat, msg, reply_markup=None: edited.append(text))
        state = {"running": [], "last": {"update": {"mtime": time.time(), "finished": True}}}
        with mock.patch.object(updates, "redis_client", redis), mock.patch.object(updates, "bot", fake_bot), mock.patch.object(updates, "_state_of", lambda i: state), mock.patch(
            "hiddifypanel.models.hconfig", lambda key: "x"
        ), mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False):
            updates.watch_updates()
        self.assertIn(t(T.up_done, "en", name="Berlin"), edited[-1])
        self.assertEqual(redis.h, {})


if __name__ == "__main__":
    unittest.main()
