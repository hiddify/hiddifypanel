import unittest

from hiddifypanel.models.usage_data import UsageData
from hiddifypanel.panel import usage_batch


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None):
        self.data[key] = value.encode() if isinstance(value, str) else value

    def delete(self, key):
        self.data.pop(key, None)


class UsageBatchTest(unittest.TestCase):
    def test_inflight_round_trip(self):
        r = FakeRedis()
        self.assertIsNone(usage_batch.load_inflight(r))
        usage_batch.save_inflight(r, "b1", [UsageData(uuid="u1", upload=1, download=2)])
        batch_id, usages = usage_batch.load_inflight(r)
        self.assertEqual(batch_id, "b1")
        self.assertEqual((usages[0].uuid, usages[0].usage), ("u1", 3))
        usage_batch.drop_inflight(r)
        self.assertIsNone(usage_batch.load_inflight(r))

    def test_broken_inflight_is_dropped(self):
        r = FakeRedis()
        r.set(usage_batch.INFLIGHT_KEY, "not json")
        self.assertIsNone(usage_batch.load_inflight(r))
        self.assertNotIn(usage_batch.INFLIGHT_KEY, r.data)

    def test_parent_applies_a_batch_once(self):
        r = FakeRedis()
        total = 0
        for _ in range(5):  # the node resends after lost answers
            if not usage_batch.already_applied(r, 7, "b1"):
                total += 100
                usage_batch.mark_applied(r, 7, "b1")
        self.assertEqual(total, 100)
        self.assertFalse(usage_batch.already_applied(r, 7, "b2"))
        self.assertFalse(usage_batch.already_applied(r, 8, "b1"))


if __name__ == "__main__":
    unittest.main()
