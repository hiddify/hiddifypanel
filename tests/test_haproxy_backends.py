"""HAProxy configs that use a backend they never define (HAProxy refuses them and does not start)."""

from __future__ import annotations

import unittest

from hiddifypanel.proxy_v3.config_builder.haproxy.server import missing_backends

_CONFIG = """
frontend in-httpmode-ssl
  use_backend %[path,map_beg(/opt/hiddify-manager/generated/include/haproxy/server/maps/path_tcp,to_httpmode_from_tls)]
  default_backend to_httpmode_from_tls
  use_backend panel if { path_beg /admin }

backend panel
  server s 127.0.0.1:9000
"""


class MissingBackendsTest(unittest.TestCase):
    def test_reports_backend_used_but_not_defined(self):
        # A routing override from before 14.1.0b2 has no to_httpmode_from_tls
        self.assertEqual(missing_backends(_CONFIG), ["to_httpmode_from_tls"])

    def test_complete_config_has_none(self):
        config = _CONFIG + "\nbackend to_httpmode_from_tls\n    server s abns@http_in_from_tls send-proxy-v2\n"
        self.assertEqual(missing_backends(config), [])

    def test_dynamic_names_and_other_maps_are_not_backends(self):
        config = "frontend f\n  use_backend %[req.hdr(host),lower,map_str(virt@short_links)]\n  http-request set-var(txn.x) str(1)\n"
        self.assertEqual(missing_backends(config), [])


if __name__ == "__main__":
    unittest.main()
