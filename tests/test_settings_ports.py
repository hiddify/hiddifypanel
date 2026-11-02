import unittest

from hiddifypanel.models import ConfigEnum
from hiddifypanel.panel.settings_form import _port_conflict


class PortConflictTest(unittest.TestCase):
    def test_empty_support_text_is_not_a_port(self):
        # "support" contains "port"; both fields default to "" and used to block every save.
        sections = {"branding": {"branding_title": "Hiddify", "branding_support_title": "", "branding_support_more": ""}}
        self.assertIsNone(_port_conflict(ConfigEnum.branding_support_title, "", sections))
        self.assertIsNone(_port_conflict(ConfigEnum.branding_support_more, "hello, world", sections))

    def test_shared_word_in_support_text_is_not_a_port(self):
        sections = {"branding": {"branding_support_title": "world", "branding_support_more": "hello, world"}}
        self.assertIsNone(_port_conflict(ConfigEnum.branding_support_more, "hello, world", sections))

    def test_the_same_port_in_two_settings_is_rejected(self):
        sections = {"proxy": {"hysteria_port": "2096", "tuic_port": "2096, 2097"}}
        self.assertEqual(_port_conflict(ConfigEnum.hysteria_port, "2096", sections), ("tuic_port", "2096"))

    def test_a_blank_piece_is_not_a_port(self):
        sections = {"proxy": {"hysteria_port": "", "tuic_port": "2096,"}}
        self.assertIsNone(_port_conflict(ConfigEnum.hysteria_port, "", sections))
        self.assertIsNone(_port_conflict(ConfigEnum.tuic_port, "2096,", sections))

    def test_80_and_443_stay_on_their_own_lists(self):
        self.assertEqual(_port_conflict(ConfigEnum.hysteria_port, "443", {"proxy": {"hysteria_port": "443"}}), ("", "443"))
        self.assertIsNone(_port_conflict(ConfigEnum.tls_ports, "443", {"proxy": {"tls_ports": "443"}}))
        self.assertIsNone(_port_conflict(ConfigEnum.http_ports, "80,8080", {"proxy": {"http_ports": "80,8080"}}))
        self.assertEqual(_port_conflict(ConfigEnum.wireguard_port, "80", {"proxy": {"wireguard_port": "80"}}), ("", "80"))
