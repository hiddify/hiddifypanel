import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.proxy_v3 import config_tester_proxies as ctp


def proxy(id, name, enable=True):
    return SimpleNamespace(id=id, name=name, enable=enable)


PROXIES = [proxy(1, "vless ws"), proxy(2, "vless ws TLS"), proxy(3, "Hysteria2 QUIC"), proxy(4, "trojan")]


class OwnerTest(unittest.TestCase):
    def test_longest_name_wins(self):
        self.assertEqual(ctp.owner("vless ws TLS example.com IPv4 h2", PROXIES).id, 2)
        self.assertEqual(ctp.owner("vless ws example.com", PROXIES).id, 1)

    def test_whole_words_only(self):
        self.assertIsNone(ctp.owner("vless wss example.com", PROXIES))
        self.assertIsNone(ctp.owner("trojanX example.com", PROXIES))

    def test_exact_and_spaces(self):
        self.assertEqual(ctp.owner("trojan", PROXIES).id, 4)
        self.assertEqual(ctp.owner("  Hysteria2   QUIC  example.com", PROXIES).id, 3)

    def test_not_ours(self):
        self.assertIsNone(ctp.owner("someone else's config", PROXIES))


class HealthTest(unittest.TestCase):
    def test_down_partial_up(self):
        results = [
            {"name": "vless ws a.example.com", "ok": False},
            {"name": "vless ws b.example.com", "ok": False},
            {"name": "vless ws TLS a.example.com", "ok": True},
            {"name": "vless ws TLS b.example.com", "ok": False},
            {"name": "trojan a.example.com", "ok": True},
            {"name": "unknown config", "ok": False},
        ]
        with mock.patch.object(ctp, "_proxies", return_value=PROXIES):
            got = {h["id"]: (h["status"], h["tested"], h["failed"]) for h in ctp.health(results, child_id=0)}
        self.assertEqual(got, {1: ("down", 2, 2), 2: ("partial", 2, 1), 4: ("up", 1, 0)})

    def test_down_first(self):
        results = [{"name": "trojan x", "ok": True}, {"name": "vless ws x", "ok": False}]
        with mock.patch.object(ctp, "_proxies", return_value=PROXIES):
            self.assertEqual([h["status"] for h in ctp.health(results, child_id=0)], ["down", "up"])


if __name__ == "__main__":
    unittest.main()
