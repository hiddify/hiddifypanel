"""The setup guide (telegrambot/guide.py) and the copy button (ui.copy_btn)."""

import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import doctor, guide, ui
from hiddifypanel.panel.commercial.telegrambot.texts import T, t

SUB = "https://panel.example.com/path/0000/sub/?asn=unknown#Ann"


def buttons(screen):
    return [b.to_dict() for row in screen.markup.keyboard for b in row]


class GuideTests(unittest.TestCase):
    def setUp(self):
        self.sub = SUB
        for p in (
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
            mock.patch.object(guide.accounts, "links", lambda user: SimpleNamespace(sub=self.sub, home="https://panel.example.com/path/0000/")),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.ctx = ui.Ctx(1, "fa", user=SimpleNamespace(name="Ann"))

    def test_every_device_is_offered(self):
        data = [b["callback_data"] for b in buttons(guide.devices_screen(self.ctx))]
        self.assertEqual(data, [f"gd:{d.value}" for d in guide.Device] + ["bb"])

    def test_each_device_has_its_store_a_copy_button_and_four_steps(self):
        for device in guide.Device:
            screen = guide.device_screen(self.ctx, device)
            got = buttons(screen)
            self.assertTrue(got[0]["url"].startswith("https://"), device)
            self.assertEqual(got[0]["style"], "success")
            copy = [b for b in got if "copy_text" in b]
            self.assertEqual(copy[0]["copy_text"], {"text": SUB})
            self.assertIn("4. ", screen.text)
            self.assertNotIn(SUB, screen.text)
        self.assertIn(t(T.guide_add_desktop, "fa"), guide.device_screen(self.ctx, guide.Device.windows).text)
        self.assertIn(t(T.guide_add_phone, "fa"), guide.device_screen(self.ctx, guide.Device.ios).text)

    def test_a_link_too_long_to_copy_is_shown_to_hold(self):
        self.sub = SUB + "x" * 300
        screen = guide.device_screen(self.ctx, guide.Device.android)
        self.assertFalse([b for b in buttons(screen) if "copy_text" in b])
        self.assertIn(t(T.guide_copy_long, "fa"), screen.text)
        self.assertIn("<code>", screen.text)

    def test_unknown_device_shows_the_list(self):
        c = ui.Ctx(1, "en", user=SimpleNamespace(name="Ann"))
        with mock.patch.object(ui.Ctx, "show") as show, mock.patch.object(ui.Ctx, "toast"):
            guide.show_guide(c, ["zz"])
        self.assertIn(t(T.guide_which, "en"), show.call_args.args[0].text)


class DoctorGuideTests(unittest.TestCase):
    def test_the_guide_is_offered_when_nothing_is_wrong(self):
        ok = doctor.Finding(doctor.Level.ok, "")
        with mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False):
            fine = buttons(doctor.doctor_screen(ui.Ctx(1, "en"), doctor.Diagnosis(ok, ok, ok, ok, cause="")))
            broken = buttons(doctor.doctor_screen(ui.Ctx(1, "en"), doctor.Diagnosis(ok, ok, ok, ok, cause="server")))
        self.assertIn("gd", [b["callback_data"] for b in fine])
        self.assertNotIn("gd", [b["callback_data"] for b in broken])


if __name__ == "__main__":
    unittest.main()
