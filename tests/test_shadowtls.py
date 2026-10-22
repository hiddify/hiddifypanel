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

    # ShadowTLS is an SNI proxy: no separate fake domain (no shadowtls_fakedomain in ctx: StrictUndefined fails if used)
    def test_handshake_goes_to_the_proxys_own_domain(self):
        fragment = self.render("hiddify-core/server/protocols/shadowtls")
        inbound = json5.loads(fix_duplicate_json_commas("{" + fragment + "}"))
        self.assertEqual(inbound["handshake"], {"server": "own-server.example", "server_port": 443})
        self.assertEqual(inbound["handshake_for_server_name"], {"own-server.example": inbound["handshake"]})
        self.assertEqual(inbound["detour"], "shadowsocks_for_proxies")
        self.assertEqual(inbound["users"][0]["password"], self.ctx.hconfig.shared_secret)

    def test_client_names_the_proxys_domain(self):
        self.ctx.hconfig.utls = "chrome"
        fragment = self.render("hiddify-core/client/protocols/shadowtls", proxy=SimpleNamespace(server="1.2.3.4", port=443), domain=SimpleNamespace(sni="own-server.example"))
        outbound = json5.loads(fix_duplicate_json_commas("{" + fragment + "}"))
        self.assertEqual(outbound["tls"]["server_name"], "own-server.example")

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

    def test_gateway_routes_shadowtls_by_its_domain_like_any_sni_proxy(self):
        self.ctx.proxies = [self.proxy(20035, 20036), self.proxy(20040, categories=("anytls",))]
        protocols = tomllib.loads(self.render("rust-rpxy-l4/server/base"))["protocols"]
        self.assertNotIn("shadowtls", protocols)
        self.assertEqual(protocols["sp_95_server-0-example_tls"]["target"], ["127.0.0.1:20035"])
        self.assertEqual(protocols["sp_95_server-1-example_tls"]["target"], ["127.0.0.1:20036"])
        self.assertEqual(protocols["sp_96_server-0-example_tls"]["target"], ["127.0.0.1:20040"])

    def test_ss_faketls_domains_go_to_its_service_port(self):
        # SS FakeTLS is an SNI proxy too: its domains are routed by their own names, to the obfs-server service
        from hiddifypanel.proxy_v3.context_vars.proxy import SS_FAKETLS_PORT

        self.ctx.proxies = [self.proxy(SS_FAKETLS_PORT, categories=("ss", "faketls"))]
        protocols = tomllib.loads(self.render("rust-rpxy-l4/server/base"))["protocols"]
        self.assertNotIn("ssfaketls", protocols)
        self.assertEqual(protocols["sp_95_server-0-example_tls"]["target"], [f"127.0.0.1:{SS_FAKETLS_PORT}"])

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
