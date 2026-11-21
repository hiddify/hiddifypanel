"""Per-domain TLS fragment via FinalMask (#5647)."""

from __future__ import annotations

import unittest

from hiddifypanel.proxy_v3 import tls_fragment as tf


class TlsFragmentResolveTest(unittest.TestCase):
    def test_direct_never_enables(self):
        r = tf.resolve(domain_mode="direct", extra={"tls_fragment": {"mode": "on"}}, global_enable=True)
        self.assertFalse(r["enable"])
        self.assertIsNone(tf.to_finalmask(r))

    def test_no_fragment_stays_off(self):
        # The fragment is per domain only (tricks.finalmask); panel globals no longer turn it on
        for global_enable in (False, True):
            r = tf.resolve(domain_mode="cdn", extra={}, global_enable=global_enable)
            self.assertFalse(r["enable"])
            self.assertEqual(r["lengths"], tf.DEFAULT_LENGTHS)
            self.assertIsNone(tf.to_finalmask(r))

    def test_mode_off_overrides_global_on(self):
        r = tf.resolve(domain_mode="cdn", extra={"tricks": {"tls_fragment": {"mode": "off"}}}, global_enable=True)
        self.assertFalse(r["enable"])

    def test_mode_on_builds_finalmask(self):
        extra = tf.set_tls_fragment({}, {"mode": "on", "lengths": ["3-5", "6-8"], "delays": ["10-20"], "packets": "tlshello", "maxSplit": "3-6"})
        r = tf.resolve(domain_mode="worker", extra=extra)
        self.assertTrue(r["enable"])
        layer = tf.to_finalmask(r)["tcp"][0]
        self.assertEqual(layer["type"], "fragment")
        self.assertEqual(layer["settings"]["lengths"], ["3-5", "6-8"])
        self.assertEqual(layer["settings"]["delays"], ["10-20"])
        self.assertEqual(layer["settings"]["maxSplit"], "3-6")

    def test_set_tls_fragment_writes_finalmask(self):
        out = tf.set_tls_fragment(
            {"other": 1},
            {"mode": "on", "packets": "tlshello", "lengths": ["3-5", "6-8", "10-20"], "delays": ["10-20"], "maxSplit": "3-6"},
        )
        self.assertEqual(out["other"], 1)
        self.assertEqual(out["tricks"]["template"], tf.TEMPLATE_TLS_FRAGMENT)
        layer = out["tricks"]["finalmask"]["tcp"][0]
        self.assertEqual(layer["type"], "fragment")
        self.assertEqual(layer["settings"]["lengths"], ["3-5", "6-8", "10-20"])

    def test_set_off_clears_fragment_finalmask(self):
        start = tf.set_tls_fragment({}, {"mode": "on", "lengths": ["10-100"], "delays": ["50-200"], "packets": "tlshello"})
        out = tf.set_tls_fragment(start, {"mode": "off"})
        self.assertNotIn("tricks", out)
        self.assertFalse(tf.resolve(domain_mode="cdn", extra=out)["enable"])

if __name__ == "__main__":
    unittest.main()
