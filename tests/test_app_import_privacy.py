"""Subscription import actions must not send bearer links to external websites."""

import base64
import inspect
import unittest
from unittest.mock import patch
from urllib.parse import quote, urlsplit

from apiflask import APIFlask
from flask_babel import Babel


class AppImportPrivacyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = APIFlask(__name__)
        Babel(cls.app)
        with cls.app.app_context():
            from hiddifypanel.panel.commercial.restapi.v2.user import apps_api

            cls.api_module = apps_api

    def app_list(self, platform):
        # DTO generation needs no database: use a fictional user's subscription
        # and stub release discovery so these checks never make network requests.
        api = self.api_module.AppAPI.__new__(self.api_module.AppAPI)
        api.hiddify_github_repo = "https://github.com/hiddify"
        api.user_panel_url = "https://panel.example.invalid/client/00000000-0000-4000-8000-000000000000/"
        api.user_panel_encoded_url = quote(api.user_panel_url)
        api.subscription_link_url = api.user_panel_url + "all.txt?name=Example&asn=&mode=new"
        api.subscription_link_encoded_url = base64.b64encode(api.subscription_link_url.encode()).decode()
        api.profile_title = "Example"
        get_apps = inspect.unwrap(self.api_module.AppAPI.get)
        with (
            self.app.test_request_context("/client/api/v2/user/apps/"),
            patch.object(self.api_module, "_", side_effect=lambda text: text),
            patch.object(self.api_module, "get_latest_release_url", return_value=("https://github.com/example/app/releases/tag/v1.0.0", "v1.0.0")),
        ):
            return get_apps(api, self.api_module.AppInSchema(platform=platform))

    def test_foxray_keeps_install_option_and_uses_copy_link_fallback(self):
        for platform in (self.api_module.Platform.ios, self.api_module.Platform.all):
            with self.subTest(platform=platform):
                apps = self.app_list(platform)
                foxray = next(app for app in apps if app.title == "app.foxray.title")
                payload = foxray.model_dump(mode="json")
                self.assertEqual(payload["deeplink"], "")
                self.assertTrue(payload["icon_url"].endswith("apps-icon/foxray.ico"))
                self.assertEqual(payload["install"][0]["type"], "app_store")
                self.assertEqual(payload["install"][0]["url"], "https://apps.apple.com/us/app/foxray/id6448898396")

    def test_import_actions_do_not_navigate_to_external_websites(self):
        for platform in (self.api_module.Platform.ios, self.api_module.Platform.all):
            with self.subTest(platform=platform):
                apps = self.app_list(platform)
                for app in apps:
                    self.assertNotIn(urlsplit(app.deeplink).scheme.lower(), {"http", "https"}, app.title)
                hiddify = next(app for app in apps if app.title == "app.hiddify.next.title")
                self.assertTrue(hiddify.deeplink.startswith("hiddify://import/"))


if __name__ == "__main__":
    unittest.main()
