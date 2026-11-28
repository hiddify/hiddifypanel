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

    def get(self, key):
        return self.h.get("@" + key)

    def set(self, key, value, ex=None):
        self.h["@" + key] = value


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
            mock.patch.object(updates.AdminUser, "get_super_admin", lambda: SimpleNamespace(id=1)),
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

    def test_the_owner_only(self):
        other_super = ui.Ctx(6, "en", admin=SimpleNamespace(id=2, name="Bo", mode="super_admin"))
        updates.show_update(other_super, [])
        self.assertEqual(self.shown, [])  # another super admin: no access
        admin = ui.Ctx(7, "en", admin=SimpleNamespace(id=3, name="Cy", mode="admin"))
        updates.show_update(admin, [])
        self.assertEqual(self.shown, [])
        self.assertTrue(updates.allowed(self.ctx))  # the owner (id 1)

    def test_the_key_on_the_status_screen_for_the_owner_only(self):
        from hiddifypanel.panel.commercial.telegrambot import ops

        with mock.patch.object(ops, "app_url", lambda page: None):
            owner_keys = [b.callback_data for row in ops.status_rows(self.ctx) for b in row]
            other = ui.Ctx(6, "en", admin=SimpleNamespace(id=2, name="Bo", mode="super_admin"))
            other_keys = [b.callback_data for row in ops.status_rows(other) for b in row]
        self.assertIn("up", owner_keys)
        self.assertNotIn("up", other_keys)
        self.assertIn("ap", other_keys)  # the other operations stay for super admins


class StartTests(Base):
    def test_start_waits_in_a_message_of_its_own_and_is_watched(self):
        sent = []
        fake_bot = SimpleNamespace(send_message=lambda chat, text, **k: sent.append(text) or SimpleNamespace(message_id=88))
        with mock.patch.object(updates, "start", lambda ctx, n: (True, 1000.0)), mock.patch.object(updates, "bot", fake_bot), mock.patch(
            "hiddifypanel.panel.commercial.telegrambot.miniapp.needs_unlock", lambda *a: False
        ):
            updates.show_update(self.ctx, ["2", "go"])
        self.assertIn(t(T.up_running, "en", name="Berlin"), sent[-1])  # not over the bot's screen
        self.assertNotIn(t(T.up_running, "en", name="Berlin"), self.shown[-1].text)
        entry = json.loads(self.redis.h["5:88"])
        self.assertEqual((entry["server"], entry["server_started"], entry["admin"]), (2, 1000.0, 1))

    def test_not_started_says_so(self):
        with mock.patch.object(updates, "start", lambda ctx, n: (False, 0.0)), mock.patch("hiddifypanel.panel.commercial.telegrambot.miniapp.needs_unlock", lambda *a: False):
            updates.show_update(self.ctx, ["2", "go"])
        self.assertIn(t(T.up_not_started, "en"), self.shown[-1].text)
        self.assertFalse([k for k in self.redis.h if not k.startswith("@")])  # nothing watched


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
        with mock.patch.object(updates, "redis_client", redis), mock.patch.object(updates, "bot", fake_bot), mock.patch.object(updates, "_state_of", lambda *a: state), mock.patch(
            "hiddifypanel.models.hconfig", lambda key: "x"
        ), mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False):
            updates.watch_updates()
        self.assertIn(t(T.up_done, "en", name="Berlin"), edited[-1])
        self.assertEqual(redis.h, {})


if __name__ == "__main__":
    unittest.main()
