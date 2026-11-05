import unittest
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader
from slugify import slugify


class TemplateLoader(FileSystemLoader):
    def get_source(self, environment, template):
        return super().get_source(environment, template if template.endswith(".j2") else template + ".j2")


def server_line(config: str, backend: str) -> str:
    """The ``server`` line of a backend in the rendered config."""
    lines = config.splitlines()
    start = lines.index(f"backend {backend}")
    for line in lines[start + 1 :]:
        if line.startswith(("backend ", "frontend ", "listen ")):
            break
        if line.strip().startswith("server "):
            return line.strip()
    raise AssertionError(f"no server line in backend {backend}")


class HaproxyDecoyTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / "hiddifypanel/proxy_v3/proxy_templates"
        # Lenient undefined, as the panel renders it (config_builder/jinja_render.py): base.j2 has {{ port }} in a comment
        self.env = Environment(loader=TemplateLoader(root), keep_trailing_newline=True)
        self.env.filters["slugify"] = slugify
        self.env.globals["include_path"] = lambda ctx, slug: f"/tmp/{slug.replace('/', '_')}.map"
        domain = SimpleNamespace(name="www.gateway.example", sni="www.gateway.example")
        gateway = SimpleNamespace(id=7, mode="domains_sni_gateway", iter_proxies_with_domain=lambda: iter([SimpleNamespace(domain=domain, tcp_port=20007, tcp_udp="tcp")]))
        self.ctx = SimpleNamespace(
            hconfig=SimpleNamespace(
                log_level="WARNING",
                ipv6_enabled=False,
                decoy_domain="www.decoy.example",
                telegram_webproxy_enable=False,
                proxy_path_admin="admin-path",
                path_naive="naive",
                path_tcp="tcp",
            ),
            custom_proxies=[],
            proxies=[gateway],
            domains=[],
        )

    def render(self):
        return self.env.get_template("haproxy/server/base").render(ctx=self.ctx, haproxy_cert_dir="/opt/hiddify-manager/data/cert/")

    def test_default_decoy_is_fetched_over_https(self):
        # Visitors reach default_decoy over TLS: on :80 an https-only decoy answers 301 to itself (the real site).
        self.assertEqual(
            server_line(self.render(), "default_decoy"),
            "server s www.decoy.example:443 ssl verify none sni str(www.decoy.example) resolvers dns resolve-prefer ipv4 init-addr last,libc,none",
        )

    def test_sni_gateway_decoy_stays_on_port_80(self):
        # Only cleartext requests with that Host get here: the site's own answer on :80 is the right one.
        self.assertEqual(
            server_line(self.render(), "decoy_sp_7_www-gateway-example"),
            "server s www.gateway.example:80 resolvers dns resolve-prefer ipv4 init-addr last,libc,none",
        )


if __name__ == "__main__":
    unittest.main()
