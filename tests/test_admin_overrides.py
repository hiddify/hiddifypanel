import unittest
from types import SimpleNamespace as N
from unittest import mock

from hiddifypanel import admin_overrides
from hiddifypanel.models import ConfigEnum


def admin(id, overrides=None, parent=None):
    a = N(id=id, override_settings=overrides, parent_admin=None)
    a.parent_admin = parent if parent is not None else a  # the owner is its own parent
    return a


class AdminOverridesTests(unittest.TestCase):
    def test_clean_keeps_known_non_empty_valid_values(self):
        values, problems = admin_overrides.clean({
            "branding_title": " My VPN ", "branding_site": "https://t.me/me", "lang": "fa",
            "branding_freetext": "", "proxy_path": "x", "user_page_url": "not a url",
        })
        self.assertEqual(values, {"branding_title": "My VPN", "branding_site": "https://t.me/me", "lang": "fa"})
        self.assertEqual(problems, ["user_page_url"])
        self.assertEqual(admin_overrides.clean({"lang": "xx"})[1], ["lang"])
        self.assertEqual(admin_overrides.clean(None), ({}, []))

    def test_nearest_admin_wins_then_the_panel(self):
        owner = admin(1, {"branding_title": "Owner"})
        reseller = admin(2, {"branding_site": "https://t.me/reseller"}, owner)
        agent = admin(3, {"branding_title": "Agent"}, reseller)
        user = N(admin=agent)
        with mock.patch.object(admin_overrides, "hconfig", lambda k: f"panel:{k}"):
            self.assertEqual(admin_overrides.user_hconfig(ConfigEnum.branding_title, user), "Agent")
            self.assertEqual(admin_overrides.user_hconfig(ConfigEnum.branding_site, user), "https://t.me/reseller")
            self.assertEqual(admin_overrides.user_hconfig(ConfigEnum.lang, user), "panel:lang")
            self.assertEqual(admin_overrides.user_hconfig(ConfigEnum.branding_title, N(admin=reseller)), "Owner")
            # only the user page's settings can be overridden
            self.assertEqual(admin_overrides.user_hconfig(ConfigEnum.proxy_path, user), "panel:proxy_path")


if __name__ == "__main__":
    unittest.main()
