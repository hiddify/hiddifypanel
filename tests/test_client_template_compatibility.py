import unittest
from pathlib import Path
from types import SimpleNamespace

import json5
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, StrictUndefined

from hiddifypanel.proxy_v3.context_vars.builder.utils import fix_duplicate_json_commas
from hiddifypanel.proxy_v3.template_catalog.client_builder import build_clash_client_outbound, supports_clash_preset
from hiddifypanel.proxy_v3.template_catalog.proxy_matrix import ProxyCombination


class TemplateLoader(FileSystemLoader):
    def get_source(self, environment, template):
        return super().get_source(environment, template if template.endswith(".j2") else template + ".j2")


class ClientTemplateCompatibilityTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / "hiddifypanel/proxy_v3/proxy_templates"
        self.env = Environment(loader=TemplateLoader(root), undefined=StrictUndefined)
        self.env.filters["trim_no_line"] = lambda value: " ".join(str(value).split())
        cert = SimpleNamespace(server_name="server.example", is_trusted=True, cert_lines=[], key_lines=[])
        self.domain = SimpleNamespace(sni="server.example", host="server.example", is_reality=lambda: False, is_fake_tls=lambda: False, allow_insecure=False)
        self.domain.cert = cert
        self.proxy = SimpleNamespace(proto="tuic", server_core="hiddify-core", transport="custom", server="server.example", port=443, path="upgrade", domain=self.domain, tls_layer=SimpleNamespace(alpns=lambda: ["h2", "http/1.1"]))
        self.ctx = SimpleNamespace(
            proxy=self.proxy,
            shared_cert=cert,
            domain=SimpleNamespace(cert=cert),
            user=SimpleNamespace(uuid="01234567-89ab-cdef-0123-456789abcdef"),
            platform=SimpleNamespace(app_group="clash", app=SimpleNamespace(version="1.19.32")),
            hconfig=SimpleNamespace(vless_flow="xtls-rprx-vision", vless_encryption="mlkem768x25519plus.native.0rtt.test-key", httpupgrade_enable=True),
        )

    def render(self, name):
        text = self.env.get_template(name).render(ctx=self.ctx, proxy=self.proxy, domain=self.domain)
        return json5.loads(fix_duplicate_json_commas("{" + text + "}"))

    def test_tuic_client_and_server_negotiate_the_same_alpn(self):
        server = self.render("hiddify-core/server/tls/tls")["tls"]
        client = self.render("hiddify-core/client/tls/shared_cert_tls")["tls"]
        self.proxy.udp_port = 443
        mihomo = self.render("clash/client/protocols/tuic")
        self.assertEqual(server["alpn"], ["h3"])
        self.assertEqual(client["alpn"], mihomo["alpn"])
        self.assertEqual(server["alpn"], client["alpn"])

    def test_tuic_alpn_does_not_change_hysteria_or_generic_tls(self):
        self.proxy.proto = "hysteria"
        self.assertNotIn("alpn", self.render("hiddify-core/server/tls/tls")["tls"])
        self.assertNotIn("alpn", self.render("hiddify-core/client/tls/shared_cert_tls")["tls"])
        self.proxy.proto = "vless"
        self.assertEqual(self.render("hiddify-core/server/tls/tls")["tls"]["alpn"], ["h2", "http/1.1"])
        self.assertNotIn("alpn", self.render("hiddify-core/client/tls/shared_cert_tls")["tls"])

    def test_encrypted_xray_vless_exports_vision_on_all_transports(self):
        self.proxy.server_core = "xray"
        for transport in ("tcp", "xhttp", "grpc", "ws", "http", "httpupgrade"):
            with self.subTest(transport=transport):
                self.proxy.transport = transport
                proxy = self.render("clash/client/protocols/vless")
                self.assertEqual(proxy["flow"], "xtls-rprx-vision")
                self.assertEqual(proxy["encryption"], self.ctx.hconfig.vless_encryption)

    def test_reality_tcp_terminator_uses_vision_without_inner_encryption(self):
        self.proxy.server_core = "xray"
        self.proxy.transport = "tcp"
        self.domain.is_reality = lambda: True
        proxy = self.render("clash/client/protocols/vless")
        self.assertEqual(proxy["flow"], "xtls-rprx-vision")
        self.assertNotIn("encryption", proxy)

    def test_plain_non_tcp_and_hiddify_vless_do_not_gain_vision(self):
        self.proxy.transport = "ws"
        self.proxy.server_core = "xray"
        self.ctx.hconfig.vless_encryption = "none"
        self.assertNotIn("flow", self.render("clash/client/protocols/vless"))
        self.proxy.server_core = "hiddify-core"
        self.ctx.hconfig.vless_encryption = "mlkem768x25519plus.native.0rtt.test-key"
        proxy = self.render("clash/client/protocols/vless")
        self.assertNotIn("flow", proxy)
        self.assertNotIn("encryption", proxy)

    def test_anytls_catalog_builds_a_clash_outbound(self):
        combo = ProxyCombination(l3="tls", transport="custom", cdn="direct", proto="anytls", enable=True, name="AnyTLS")
        self.assertTrue(supports_clash_preset(combo))
        template, dependencies = build_clash_client_outbound(combo)
        self.assertIn("clash/client/protocols/anytls", dependencies)
        self.ctx.iter_ctx_domains = lambda: iter([self.ctx])
        self.env.loader = ChoiceLoader([
            DictLoader({"clash/client/tag": "AnyTLS"}), self.env.loader,
        ])
        rendered = self.env.from_string(template).render(ctx=self.ctx)
        proxy = json5.loads("[" + rendered.rstrip().rstrip(",") + "]")[0]
        self.assertEqual(proxy["type"], "anytls")
        self.assertEqual(proxy["sni"], "server.example")
        self.assertEqual(proxy["password"], self.ctx.user.uuid)
        self.assertNotIn("skip-cert-verify", proxy)

    def test_anytls_preserves_insecure_domain_setting(self):
        self.domain.allow_insecure = True
        self.assertTrue(self.render("clash/client/protocols/anytls")["skip-cert-verify"])

    def test_anytls_reality_is_explicitly_skipped(self):
        self.domain.is_reality = lambda: True
        class Skipped(Exception):
            pass
        def skip(reason):
            raise Skipped(reason)
        self.env.globals["skip"] = skip
        with self.assertRaisesRegex(Skipped, "AnyTLS does not support Reality"):
            self.render("clash/client/protocols/anytls")

    def test_httpupgrade_uses_confirmed_handshake_instead_of_fast_open(self):
        options = self.render("clash/client/streams/httpupgrade")["ws-opts"]
        self.assertTrue(options["v2ray-http-upgrade"])
        self.assertFalse(options["v2ray-http-upgrade-fast-open"])


if __name__ == "__main__":
    unittest.main()
