"""Advanced mode: the nodes and domains screens, node alerts and the morning report."""

import datetime
import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import servers, ui
from hiddifypanel.panel.commercial.telegrambot.texts import T, t

ADV = "hiddifypanel.panel.commercial.telegrambot.advanced.is_on"


class FakeRedis:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, **_kw):
        self.values[key] = value
        return True


def node(id, name, ok=True, cpu=10.0, error_code=None):
    return SimpleNamespace(
        id=id,
        name=name,
        ok=ok,
        country="DE",
        error=None,
        error_code=error_code,
        cpu=SimpleNamespace(percent=cpu),
        memory=SimpleNamespace(percent=20.0),
        disk=SimpleNamespace(percent=30.0),
        host=SimpleNamespace(panel_version="14.5.0"),
    )


class Base(unittest.TestCase):
    def setUp(self):
        for p in (mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),):
            p.start()
            self.addCleanup(p.stop)
        self.ctx = ui.Ctx(5, "en", admin=SimpleNamespace(id=1, name="Ann", mode="admin", telegram_id=5))

    def data(self, markup):
        return [b.callback_data for row in markup.keyboard for b in row]


class GateTests(Base):
    def test_hidden_while_advanced_is_off(self):
        with mock.patch(ADV, lambda: False):
            self.assertEqual(servers.status_rows(self.ctx), [])
            self.assertEqual(servers.settings_lines(self.ctx), [])

    @mock.patch(ADV, lambda: True)
    def test_operators_get_the_keys_agents_do_not(self):
        self.assertEqual([b.callback_data for b in servers.status_rows(self.ctx)[0]], ["nd", "dm"])
        agent = ui.Ctx(6, "en", admin=SimpleNamespace(id=2, name="Bo", mode="agent", telegram_id=6))
        self.assertEqual(servers.status_rows(agent), [])

    @mock.patch(ADV, lambda: True)
    def test_morning_switch_follows_the_preference(self):
        with mock.patch.object(servers.BotPref, "get", lambda *_a, **_k: "0"):
            self.assertEqual(servers.settings_rows(self.ctx)[0][0].callback_data, "mr:1")
        with mock.patch.object(servers.BotPref, "get", lambda *_a, **_k: ""):
            self.assertEqual(servers.settings_rows(self.ctx)[0][0].callback_data, "mr:0")


class NodesScreenTests(Base):
    @mock.patch(ADV, lambda: True)
    def test_up_and_down_nodes(self):
        nodes = [node(0, "this-server"), node(2, "Berlin", cpu=95.0), node(3, "Paris", ok=False, error_code="timeout")]
        with mock.patch.object(servers, "_nodes", lambda: nodes):
            screen = servers.nodes_screen(self.ctx)
        self.assertIn(t(T.nd_summary, "en", up=2, n=3), screen.text)
        self.assertIn(t(T.nd_this, "en"), screen.text)
        self.assertIn("🔴 <b>Paris</b>", screen.text)
        self.assertIn("timeout", screen.text)
        self.assertIn("CPU 95%", screen.text)
        self.assertEqual(self.data(screen.markup), ["nd", "dm", "bb"])


class DomainsScreenTests(Base):
    def test_marks_and_certificates(self):
        soon = datetime.datetime.utcnow() + datetime.timedelta(days=5, hours=1)
        rows = [
            {"name": "a.example.com", "mode": "direct", "dns": True, "expires": soon, "error": False},
            {"name": "b.example.com", "mode": "direct", "dns": False, "expires": None, "error": True},
        ]
        with mock.patch.object(servers, "domain_rows", lambda: rows):
            screen = servers.domains_screen(self.ctx)
        self.assertIn(t(T.dm_summary, "en", ok=1, n=2), screen.text)
        self.assertIn("🟢 <code>a.example.com</code>", screen.text)
        self.assertIn("⚠️ " + t(T.dm_cert_days, "en", days=5), screen.text)
        self.assertIn("🔴 <code>b.example.com</code>", screen.text)
        self.assertIn(t(T.dm_renew_failed, "en"), screen.text)


class NodeAlertTests(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.told = []
        self.nodes = [node(0, "here"), node(2, "Berlin")]
        admin = SimpleNamespace(id=1, telegram_id=5, mode="admin", lang=None)
        for p in (
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
            mock.patch.object(servers, "redis_client", self.redis),
            mock.patch.object(servers, "hconfig", lambda _k: "set"),
            mock.patch(ADV, lambda: True),
            mock.patch("hiddifypanel.hutils.node.is_parent", lambda: True),
            mock.patch.object(servers, "_nodes", lambda: self.nodes),
            mock.patch.object(servers, "_operators", lambda: [admin]),
            mock.patch.object(servers, "lang_of", lambda *_a, **_k: "en"),
            mock.patch.object(servers, "_tell", lambda chat, text, _m: self.told.append((chat, text))),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_down_after_two_failed_checks_then_back(self):
        self.nodes[1] = node(2, "Berlin", ok=False, error_code="timeout")
        servers.watch_nodes()
        self.assertEqual(self.told, [])  # one slow answer is not an outage
        servers.watch_nodes()
        self.assertEqual(len(self.told), 1)
        self.assertIn("Berlin", self.told[0][1])
        servers.watch_nodes()
        self.assertEqual(len(self.told), 1)  # told once
        self.nodes[1] = node(2, "Berlin")
        servers.watch_nodes()
        self.assertEqual(len(self.told), 2)
        self.assertTrue(self.told[1][1].startswith("✅"))
        servers.watch_nodes()
        self.assertEqual(len(self.told), 2)

    def test_quiet_when_advanced_is_off(self):
        self.nodes[1] = node(2, "Berlin", ok=False)
        with mock.patch(ADV, lambda: False):
            servers.watch_nodes()
            servers.watch_nodes()
        self.assertEqual(self.told, [])


if __name__ == "__main__":
    unittest.main()
