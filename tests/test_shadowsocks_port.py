import unittest
from unittest.mock import patch

from hiddifypanel.models import ConfigEnum
from hiddifypanel.panel.commercial.restapi.v2.admin.domains_page_api import OTHER_SERVICE_PORTS
from hiddifypanel.proxy_v3.template_catalog.custom_proxy_presets import (
    _stable_public_port,
    ip_mode_public_port,
    shadowsocks_ports_from_v12,
)


class ShadowsocksPortUpgradeTest(unittest.TestCase):
    def test_the_preset_keeps_the_v12_port(self):
        with patch("hiddifypanel.proxy_v3.template_catalog.custom_proxy_presets.hconfig", return_value="57661") as hconfig:
            port = ip_mode_public_port(
                "shadowsocks",
                "shadowsocks",
                wireguard_endpoint=False,
                slug="shadowsocks-shadowsocks2022-hc",
                child_id=3,
            )
        self.assertEqual(port, 57661)
        hconfig.assert_called_once_with(ConfigEnum.shadowsocks2022_port, 3)

    def test_a_missing_v12_port_stays_on_the_generated_one(self):
        with patch("hiddifypanel.proxy_v3.template_catalog.custom_proxy_presets.hconfig", return_value=""):
            port = ip_mode_public_port("ss", "shadowsocks", wireguard_endpoint=False, slug="shadowsocks-shadowsocks2022-hc", child_id=0)
        self.assertEqual(port, _stable_public_port("shadowsocks-shadowsocks2022-hc"))

    def test_the_generated_port_is_replaced_and_a_chosen_one_stays(self):
        self.assertEqual(
            shadowsocks_ports_from_v12([42470], [42470], generated=42470, legacy=57661, overridden=False),
            ([57661], [57661]),
        )
        self.assertIsNone(shadowsocks_ports_from_v12([42470], [42470], generated=42470, legacy=57661, overridden=True))
        self.assertIsNone(shadowsocks_ports_from_v12([18000], [18000], generated=42470, legacy=57661, overridden=False))
        self.assertIsNone(shadowsocks_ports_from_v12([57661], [57661], generated=42470, legacy=57661, overridden=False))

    def test_the_old_setting_does_not_reserve_a_domain_port(self):
        self.assertNotIn(ConfigEnum.shadowsocks2022_port, OTHER_SERVICE_PORTS)
