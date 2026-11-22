"""The backup key: Backup Now or Backup History (the newest one shown while the box is closed)."""

import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import admin, nav, ui
from hiddifypanel.panel.commercial.telegrambot.texts import T, t


class Base(unittest.TestCase):
    def setUp(self):
        self.shown = []
        for p in (
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
            mock.patch.object(ui.Ctx, "toast", lambda s, text=None, alert=False: None),
            mock.patch.object(ui.Ctx, "show", lambda s, screen: self.shown.append(screen)),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.ctx = ui.Ctx(5, "en", admin=SimpleNamespace(id=1, name="Ann", mode="super_admin"))

    def data(self, screen):
        return [b.callback_data for row in screen.markup.keyboard for b in row if b.callback_data]


class BackupMenuTests(Base):
    def test_two_choices(self):
        admin.send_backup(self.ctx, [])
        self.assertEqual(self.data(self.shown[-1]), ["bk:now", "bk:hist", "bb"])

    def test_history_newest_first_in_a_box(self):
        files = [
            {"name": "2026_11_22__22_41_10.json", "size": 564_300, "created": "2026-11-22T19:11:10+00:00"},
            {"name": "2026_11_21__18_00_01.json", "size": 550_000, "created": "2026-11-21T14:30:01+00:00"},
        ]
        with mock.patch("hiddifypanel.panel.commercial.restapi.v2.admin.backup_api.list_files", lambda: files):
            admin.send_backup(self.ctx, ["hist"])
        text = self.shown[-1].text
        self.assertIn(t(T.bk_history_count, "en", n=2), text)
        box = text[text.index("<blockquote expandable>") :]
        self.assertLess(box.index("2026.11.22_22.41"), box.index("2026.11.21_18.00"))  # newest first
        first = box.split("\n\n")[0]
        self.assertEqual(first.count("\n"), 1)  # the newest takes the two lines a closed box shows
        self.assertIn("🆕", first)

    def test_no_backups_yet(self):
        with mock.patch("hiddifypanel.panel.commercial.restapi.v2.admin.backup_api.list_files", lambda: []):
            admin.send_backup(self.ctx, ["hist"])
        self.assertIn(t(T.bk_history_none, "en"), self.shown[-1].text)

    def test_owner_only(self):
        agent = ui.Ctx(6, "en", admin=SimpleNamespace(id=2, name="Bo", mode="agent"))
        admin.send_backup(agent, [])
        self.assertEqual(self.shown, [])

    def test_taking_a_backup_is_not_a_back_step(self):
        self.assertTrue(nav.is_admin_screen(ui.Cb.backup, []))
        self.assertTrue(nav.is_admin_screen(ui.Cb.backup, ["hist"]))
        self.assertFalse(nav.is_admin_screen(ui.Cb.backup, ["now"]))


if __name__ == "__main__":
    unittest.main()
