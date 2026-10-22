import base64
import json
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace

import json5
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from slugify import slugify

from hiddifypanel.proxy_v3.config_tester import _core_items
from hiddifypanel.proxy_v3.context_vars.builder.utils import fix_duplicate_json_commas


class TemplateLoader(FileSystemLoader):
    def get_source(self, environment, template):
        return super().get_source(environment, template if template.endswith(".j2") else template + ".j2")


class ShadowTLSTests(unittest.TestCase):
    def setUp(self):
        self.proxy_id = 94
        root = Path(__file__).resolve().parents[1] / "hiddifypanel/proxy_v3/proxy_templates"
        self.env = Environment(loader=TemplateLoader(root), undefined=StrictUndefined)
        self.env.filters["b64encode"] = lambda value: base64.b64encode(value.encode()).decode()
        self.env.filters["slugify"] = slugify
        self.ctx = SimpleNamespace(
            hconfig=SimpleNamespace(
                shadowtls_enable=True,
                shadowtls_fakedomain="handshake.example",
                shared_secret="01234567-89ab-cdef-0123-456789abcdef",
                shadowsocks2022_method="2022-blake3-aes-256-gcm",
                ipv6_enabled=False,
                ssh_server_enable=False,
                wireguard_enable=False,
                ssfaketls_enable=False,
                telegram_enable=False,
            ),
            domain=SimpleNamespace(sni="own-server.example"),
            proxy=SimpleNamespace(public_access=False, proto="shadowsocks", tcp_port=20035, udp_port=None),
            user=SimpleNamespace(uuid="abcdef01-2345-6789-abcd-ef0123456789", uuid_hex="abcdef0123456789abcdef0123456789"),
            outbounds=SimpleNamespace(singbox_bridged=[]),
            proxies=[],
        )
        self.ctx.users = [self.ctx.user]

    def render(self, name, **kwargs):
        return self.env.get_template(name).render(ctx=self.ctx, **kwargs)

    def proxy(self, *ports, categories=("shadowtls",), mode="domains_sni_gateway", tcp_udp="tcp"):
        self.proxy_id += 1
        domains = [SimpleNamespace(tcp_port=p, udp_port=None, tcp_udp=tcp_udp, domain=SimpleNamespace(sni="own-server.example", name=f"server-{n}.example")) for n, p in enumerate(ports)]
        return SimpleNamespace(id=self.proxy_id, mode=mode, categories=categories, iter_proxies_with_domain=lambda: iter(domains))

    def test_handshake_and_detour_match_client_transport(self):
        fragment = self.render("hiddify-core/server/protocols/shadowtls")
        inbound = json5.loads(fix_duplicate_json_commas("{" + fragment + "}"))
        self.assertEqual(inbound["handshake"], {"server": "handshake.example", "server_port": 443})
        self.assertEqual(inbound["handshake_for_server_name"], {"handshake.example": inbound["handshake"]})
        self.assertEqual(inbound["detour"], "shadowsocks_for_proxies")
        self.assertEqual(inbound["users"][0]["password"], self.ctx.hconfig.shared_secret)
        self.assertNotIn("own-server.example", fragment)

    def test_internal_ss2022_key_matches_client(self):
        for secret in ("01234567-89ab-cdef-0123-456789abcdef", "0123456789abcdef0123456789abcdef"):
            with self.subTest(secret_format="uuid" if "-" in secret else "hex"):
                self.ctx.hconfig.shared_secret = secret
                inbounds = json5.loads("[" + self.render("hiddify-core/server/base/builtin_inbounds") + "]")
                internal = next(o for o in inbounds if o["tag"] == "shadowsocks_for_proxies")
                client = json5.loads("{" + self.render("hiddify-core/client/protocols/ss", detour="transport", plugin="") + "}")
                self.assertEqual(client["password"].split(":", 1)[0], internal["password"])
                self.assertEqual(len(base64.b64decode(internal["password"])), 32)
                self.assertEqual(client["password"].split(":", 1)[1], internal["users"][0]["password"])

    def test_gateway_uses_allocated_shadowtls_ports_and_keeps_other_routes(self):
        self.ctx.proxies = [self.proxy(20035, 20035, 20036), self.proxy(20040, categories=("anytls",))]
        config = tomllib.loads(self.render("rust-rpxy-l4/server/base"))
        route = config["protocols"]["shadowtls"]
        self.assertEqual(route["server_names"], ["handshake.example"])
        self.assertEqual(route["target"], ["127.0.0.1:20035", "127.0.0.1:20036"])
        self.assertEqual(route["send_proxy_protocol"], "v2")
        self.assertEqual(config["protocols"]["sp_96_server-0-example_tls"]["target"], ["127.0.0.1:20040"])

    def test_no_fake_sni_route_without_shadowtls_backends(self):
        for proxies in ([], [self.proxy(20040, categories=("anytls",))], [self.proxy(20035, mode="domains_l7_gateway")], [self.proxy(None)], [self.proxy(20035, tcp_udp="udp")]):
            with self.subTest(proxies=proxies):
                self.ctx.proxies = proxies
                config = tomllib.loads(self.render("rust-rpxy-l4/server/base"))
                self.assertNotIn("shadowtls", config["protocols"])

    def test_disabled_shadowtls_has_no_fake_sni_route(self):
        self.ctx.proxies = [self.proxy(20035)]
        self.ctx.hconfig.shadowtls_enable = False
        self.assertNotIn("shadowtls", tomllib.loads(self.render("rust-rpxy-l4/server/base"))["protocols"])

    def test_tester_hides_helper_but_retains_detour_dependency(self):
        helper = {"type": "shadowtls", "tag": "transport_out §hide§", "server": "own-server.example", "server_port": 443}
        main = {"type": "shadowsocks", "tag": "ShadowTLS", "detour": helper["tag"]}
        config = {"outbounds": [{"type": "selector", "tag": "Select"}, main, helper, {"type": "direct", "tag": "direct"}]}
        before = json.dumps(config)
        items = _core_items(config)
        self.assertEqual([i.tag for i in items], ["ShadowTLS"])
        self.assertEqual(items[0].config["outbounds"], [main, helper])
        self.assertEqual(json.dumps(config), before)

    def test_tester_keeps_visible_proxies_and_sequential_indexes(self):
        config = {
            "outbounds": [{"type": "shadowtls", "tag": "hidden §hide§"}, {"type": "anytls", "tag": "AnyTLS"}],
            "endpoints": [{"type": "wireguard", "tag": "WireGuard"}],
        }
        items = _core_items(config)
        self.assertEqual([(i.index, i.tag) for i in items], [(0, "AnyTLS"), (1, "WireGuard")])


if __name__ == "__main__":
    unittest.main()
