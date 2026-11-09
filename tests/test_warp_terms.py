"""WARP routes only after an admin has accepted Cloudflare's terms."""

import unittest

from hiddifypanel.proxy_v3.outbounds import warp_may_route


class WarpMayRouteTests(unittest.TestCase):
    def test_on_only_when_enabled_and_accepted(self):
        self.assertTrue(warp_may_route("all", True))
        self.assertTrue(warp_may_route("custom", True))

    def test_off_when_disabled_even_if_accepted(self):
        self.assertFalse(warp_may_route("disable", True))
        self.assertFalse(warp_may_route(None, True))
        self.assertFalse(warp_may_route("", True))

    def test_off_until_the_boolean_true(self):
        for accepted in (False, None, "true", "True", 1, "false"):
            self.assertFalse(warp_may_route("all", accepted))
            self.assertFalse(warp_may_route("custom", accepted))


if __name__ == "__main__":
    unittest.main()
