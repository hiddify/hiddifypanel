import unittest
from pathlib import Path
from unittest import mock

from jinja2 import ChainableUndefined, Environment, FileSystemLoader
from slugify import slugify

from hiddifypanel.models.proxy_base_config import BASE_CONFIG_MATRIX, TEXT_SERVER_BASE_CORES
from hiddifypanel.proxy_v3 import custom_proxy_validate
from hiddifypanel.proxy_v3.config_builder.dump import SERVER_CONFIG_DRIVERS
from hiddifypanel.proxy_v3.config_builder.jinja_render import _jinja_tojson
from hiddifypanel.proxy_v3.config_builder.text_server import TextServerDriver
from hiddifypanel.proxy_v3.custom_proxy_validate import validate_base_config_content

TEMPLATES = Path(__file__).resolve().parents[1] / "hiddifypanel/proxy_v3/proxy_templates"


class TemplateLoader(FileSystemLoader):
    def get_source(self, environment, template):
        return super().get_source(environment, template if template.endswith(".j2") else template + ".j2")


class TextServerBaseCoresTests(unittest.TestCase):
    def test_every_text_server_driver_core_is_listed(self):
        text_driver_cores = {core for core, driver in SERVER_CONFIG_DRIVERS.items() if issubclass(driver, TextServerDriver)}
        self.assertLessEqual(text_driver_cores, TEXT_SERVER_BASE_CORES)

    def test_listed_cores_are_editable_server_base_configs(self):
        self.assertLessEqual(TEXT_SERVER_BASE_CORES, set(BASE_CONFIG_MATRIX["server"]))

    def test_json_server_cores_are_not_listed(self):
        self.assertFalse({"xray", "hiddify-core", "dns_proxy"} & TEXT_SERVER_BASE_CORES)


class BaseConfigValidateTests(unittest.TestCase):
    """The template editor validates a base config before saving it; text server configs are not JSON."""

    def setUp(self):
        # Render the real templates without a database, like the panel's env (default Undefined): only ctx, the panel's
        # proxy context, is a lenient stand-in. Other names (public_ports, script variables) must come from the validator.
        env = Environment(loader=TemplateLoader(TEMPLATES))
        env.filters["slugify"] = slugify
        env.filters["tojson"] = _jinja_tojson
        # The real include_path writes a sidecar file and returns its path; only the path matters here.
        env.globals["include_path"] = lambda ctx, slug, output_dir="": f"/opt/hiddify-manager/generated/{slug}"

        def render(template_text, child_id, ctx):
            return env.from_string(template_text).render(**ctx)

        patches = [
            mock.patch.object(custom_proxy_validate, "build_sample_context", side_effect=lambda **kwargs: {"ctx": ChainableUndefined(name="ctx")}),
            mock.patch.object(custom_proxy_validate, "_render_template_text", side_effect=render),
            # What the firewall driver opens (a database read in the panel) and the WireGuard NIC (an `ip route` lookup).
            mock.patch("hiddifypanel.hutils.network.all_public_ports", return_value={"tcp": {443: "https"}, "udp": {443: "quic"}}),
            mock.patch("hiddifypanel.proxy_v3.config_builder.wireguard.server.default_ipv4_interface", return_value="eth0"),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def validate(self, core, content):
        return validate_base_config_content({"core": core, "side": "server", "content": content})

    def builtin(self, core):
        return (TEMPLATES / core / "server/base.j2").read_text()

    def test_builtin_text_server_bases_are_valid(self):
        for core in sorted(TEXT_SERVER_BASE_CORES):
            with self.subTest(core=core):
                result = self.validate(core, self.builtin(core))
                self.assertEqual(result["errors"], [])
                self.assertTrue(result["ok"])

    def test_rust_rpxy_l4_base_with_extra_toml_block_is_valid(self):
        extra = '\n[protocols."my_site"]\nprotocol = "tls"\nserver_names = ["example.com"]\ntarget = ["127.0.0.1:8443"]\n'
        result = self.validate("rust-rpxy-l4", self.builtin("rust-rpxy-l4") + extra)
        self.assertEqual(result["errors"], [])
        self.assertTrue(result["ok"])

    def test_jinja_errors_are_still_reported_for_text_server_cores(self):
        for core in sorted(TEXT_SERVER_BASE_CORES):
            with self.subTest(core=core):
                result = self.validate(core, "listen_port = 443\n{% if ctx.hconfig.ipv6_enabled %}\nlisten_ipv6 = true\n")
                self.assertFalse(result["ok"])
                self.assertEqual([e["code"] for e in result["errors"]], ["jinja_error"])

    def test_json_cores_are_still_parsed(self):
        result = self.validate("xray", "listen_port = 443\n")
        self.assertFalse(result["ok"])
        self.assertEqual([e["code"] for e in result["errors"]], ["json5_parse"])


if __name__ == "__main__":
    unittest.main()
