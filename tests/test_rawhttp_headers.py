import unittest

from hiddifypanel.proxy_v3.config_builder.jinja_render import _jinja_choose_random
from hiddifypanel.proxy_v3.config_builder.rawhttp import CUT_RANGE, safe_headers

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
PATH = "/Vc6Z6d4VtSuYFW4i3EKzc"


def browser(host):
    return {
        "Host": [host], "User-Agent": [UA], "Accept": ["*/*"], "Accept-Language": ["en-US"],
        "Accept-Encoding": ["gzip, deflate, br, zstd"], "Connection": ["keep-alive"], "Cache-Control": ["no-cache"],
        "Pragma": ["no-cache"], "Referer": [f"https://{host}/"],
        "sec-ch-ua": ['"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"'], "sec-ch-ua-mobile": ["?0"],
        "sec-ch-ua-platform": ["Android", "macOS", "Windows"], "Sec-Fetch-Dest": ["empty"], "Sec-Fetch-Mode": ["cors"],
        "Sec-Fetch-Site": ["same-origin"],
    }


def name_spans(headers, method="GET"):
    """Where the request line and each header name sit in xray's request (headers sorted by name)."""
    pos = len(f"{method} {PATH} HTTP/1.1\r\n")
    spans = [(0, pos)]
    for k in sorted(headers, key=str.encode):
        spans.append((pos, pos + len(k) + 2))
        pos += len(k) + 2 + len(headers[k][0]) + 2
    return spans


class RawHttpHeadersTests(unittest.TestCase):
    def test_xray_keeps_most_headers_and_no_name_at_the_cut(self):
        for host in ("a.io", "37.128.205.109.sslip.io", "very-long-subdomain.some-cdn-domain.example.com"):
            with self.subTest(host=host):
                kept = safe_headers(browser(host), PATH)
                self.assertIn("Host", kept)
                self.assertIn("User-Agent", kept)
                self.assertGreaterEqual(len(kept), 10)
                for start, end in name_spans(kept):
                    self.assertFalse(any(start <= cut < end for cut in CUT_RANGE), (start, end))

    def test_set_that_failed_on_a_server_is_cut_down(self):
        # this layout failed 9 in 10 connections behind HAProxy: "missing colon: User-Agent"
        names = ("Host", "User-Agent", "Accept", "Accept-Language", "Accept-Encoding", "Connection", "Cache-Control", "Pragma")
        headers = {k: v for k, v in browser("37.128.205.109.sslip.io").items() if k in names}
        self.assertLess(len(safe_headers(headers, PATH)), len(headers))

    def test_short_request_keeps_everything(self):
        headers = {"Host": ["a.io"], "User-Agent": ["x"], "Accept": ["*/*"]}
        self.assertEqual(safe_headers(headers, "/p"), headers)

    def test_any_order_client_gets_only_what_is_safe_in_every_order(self):
        headers = {k: v[0] for k, v in browser("37.128.205.109.sslip.io").items()}
        kept = safe_headers(headers, PATH, method="PUT", xray=False)
        self.assertIn("User-Agent", kept)
        self.assertNotIn("Host", kept)  # sent from the transport's "host"
        self.assertIsInstance(kept["User-Agent"], str)

    def test_choose_random_takes_a_list(self):
        self.assertIn(_jinja_choose_random(["Android", "macOS", "Windows"]), {"Android", "macOS", "Windows"})
        self.assertIn(_jinja_choose_random("a, b"), {"a", "b"})


if __name__ == "__main__":
    unittest.main()
