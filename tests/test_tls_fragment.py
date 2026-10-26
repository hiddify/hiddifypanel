"""Per-domain TLS fragment via FinalMask (#5647)."""

from __future__ import annotations

import unittest

from hiddifypanel.proxy_v3 import tls_fragment as tf


class TlsFragmentResolveTest(unittest.TestCase):
    def test_direct_never_enables(self):
        r = tf.resolve(domain_mode="direct", extra={"tls_fragment": {"mode": "on"}}, global_enable=True)
        self.assertFalse(r["enable"])
        self.assertIsNone(tf.to_finalmask(r))

    def test_inherit_follows_global(self):
        off = tf.resolve(domain_mode="cdn", extra={}, global_enable=False)
        on = tf.resolve(domain_mode="cdn", extra={}, global_enable=True)
        self.assertFalse(off["enable"])
        self.assertTrue(on["enable"])
        fm = tf.to_finalmask(on)
        self.assertEqual(fm["type"], "fragment")
        self.assertEqual(fm["settings"]["packets"], "tlshello")
        self.assertEqual(fm["settings"]["lengths"], ["10-100"])

    def test_mode_off_overrides_global_on(self):
        r = tf.resolve(domain_mode="cdn", extra={"tricks": {"tls_fragment": {"mode": "off"}}}, global_enable=True)
        self.assertFalse(r["enable"])

    def test_mode_on_builds_finalmask(self):
        r = tf.resolve(
            domain_mode="worker",
            extra={"tricks": {"tls_fragment": {"mode": "on", "lengths": ["3-5", "6-8"], "delays": ["10-20"], "packets": "tlshello", "maxSplit": "3-6"}}},
            global_enable=False,
        )
        self.assertTrue(r["enable"])
        fm = tf.to_finalmask(r)
        self.assertEqual(fm["settings"]["lengths"], ["3-5", "6-8"])
        self.assertEqual(fm["settings"]["delays"], ["10-20"])
        self.assertEqual(fm["settings"]["maxSplit"], "3-6")

    def test_set_tls_fragment_writes_finalmask(self):
        out = tf.set_tls_fragment(
            {"other": 1},
            {"mode": "on", "packets": "tlshello", "lengths": ["3-5", "6-8", "10-20"], "delays": ["10-20"], "maxSplit": "3-6"},
        )
        self.assertEqual(out["tricks"]["tls_fragment"]["mode"], "on")
        self.assertEqual(out["tricks"]["finalmask"]["type"], "fragment")
        self.assertEqual(out["tricks"]["finalmask"]["settings"]["lengths"], ["3-5", "6-8", "10-20"])

    def test_set_off_clears_fragment_finalmask(self):
        start = tf.set_tls_fragment({}, {"mode": "on", "lengths": ["10-100"], "delays": ["50-200"], "packets": "tlshello"})
        out = tf.set_tls_fragment(start, {"mode": "off"})
        self.assertEqual(out["tricks"]["tls_fragment"]["mode"], "off")
        self.assertNotIn("finalmask", out["tricks"])


if __name__ == "__main__":
    unittest.main()
