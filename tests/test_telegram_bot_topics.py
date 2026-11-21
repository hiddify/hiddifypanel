"""Topics in the private chat (telegrambot/topics.py)."""

import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import topics
from hiddifypanel.panel.commercial.telegrambot.texts import T, t


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None, nx=False):
        self.data[key] = str(value).encode()
        return True


class TopicsTests(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.prefs = {}
        self.bot = mock.MagicMock()
        self.bot.get_me.return_value = SimpleNamespace(has_topics_enabled=True)
        self.next_thread = iter([101, 102, 103])
        self.bot.create_forum_topic.side_effect = lambda chat, name, icon_color=None: SimpleNamespace(message_thread_id=next(self.next_thread))
        fake_pref = SimpleNamespace(get=lambda chat, key, default="": self.prefs.get((chat, key), default), put=lambda chat, key, value: self.prefs.__setitem__((chat, key), value))
        for p in (
            mock.patch.object(topics, "redis_client", self.redis),
            mock.patch.object(topics, "bot", self.bot),
            mock.patch.object(topics, "BotPref", fake_pref),
            mock.patch.object(topics, "db"),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_without_topic_mode_nothing_changes(self):
        self.bot.get_me.return_value = SimpleNamespace(has_topics_enabled=False)
        got = []
        topics.deliver(5, "alerts", "en", lambda extra: got.append(extra))
        self.assertEqual(got, [{}])
        self.bot.create_forum_topic.assert_not_called()
        topics.enabled()
        self.assertEqual(self.bot.get_me.call_count, 1)  # kept for an hour

    def test_a_topic_is_made_once_with_its_name(self):
        got = []
        topics.deliver(5, "alerts", "fa", lambda extra: got.append(extra))
        topics.deliver(5, "alerts", "fa", lambda extra: got.append(extra))
        self.assertEqual(got, [{"message_thread_id": 101}, {"message_thread_id": 101}])
        self.bot.create_forum_topic.assert_called_once_with(5, t(T.topic_alerts, "fa"), icon_color=16766590)
        topics.deliver(5, "support", "fa", lambda extra: got.append(extra))
        self.assertEqual(got[-1], {"message_thread_id": 102})

    def test_a_deleted_topic_is_made_again(self):
        topics.deliver(5, "alerts", "en", lambda extra: None)
        tries = []

        def send(extra):
            tries.append(extra)
            if extra.get("message_thread_id") == 101:
                raise RuntimeError("Bad Request: message thread not found")
            return "ok"

        self.assertEqual(topics.deliver(5, "alerts", "en", send), "ok")
        self.assertEqual(tries, [{"message_thread_id": 101}, {"message_thread_id": 102}])

    def test_other_errors_still_raise(self):
        with self.assertRaises(RuntimeError):
            topics.deliver(5, "alerts", "en", lambda extra: (_ for _ in ()).throw(RuntimeError("Forbidden: bot was blocked")))

    def test_a_failed_topic_falls_back_to_the_main_chat(self):
        self.bot.create_forum_topic.side_effect = RuntimeError("Bad Request: not allowed")
        got = []
        topics.deliver(5, "alerts", "en", lambda extra: got.append(extra))
        self.assertEqual(got, [{}])


if __name__ == "__main__":
    unittest.main()
