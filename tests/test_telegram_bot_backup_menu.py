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

    def files(self, *days_ago):
        import datetime

        now = datetime.datetime.now().replace(microsecond=0)
        return [{"name": (now - datetime.timedelta(days=d)).strftime("%Y_%m_%d__%H_%M_%S.json"), "size": 564_300, "created": ""} for d in days_ago]

    def test_history_last_month_newest_first_in_a_box(self):
        files = self.files(1, 3, 45)  # the 45-day-old one is left out
        with mock.patch("hiddifypanel.panel.commercial.restapi.v2.admin.backup_api.list_files", lambda: files), mock.patch.object(admin, "bot", SimpleNamespace(username="hiddify_bot")):
            admin.send_backup(self.ctx, ["hist"])
        text = self.shown[-1].text
        self.assertIn(t(T.bk_history_month, "en", n=2), text)
        box = text[text.index("<blockquote expandable>") :]
        first = box.split("\n\n")[0]
        self.assertEqual(first.count("\n"), 1)  # the newest takes the two lines a closed box shows
        self.assertIn("🆕", first)
        stem = files[0]["name"].removesuffix(".json")
        self.assertIn(f"https://t.me/hiddify_bot?start=bk_{stem}", first)  # a tap opens that backup
        self.assertNotIn(files[2]["name"].removesuffix(".json"), box)

    def test_the_rest_of_the_month_on_further_pages(self):
        files = self.files(*[d / 10 for d in range(1, 90)])  # 89 backups, all of this month
        with mock.patch("hiddifypanel.panel.commercial.restapi.v2.admin.backup_api.list_files", lambda: files), mock.patch.object(admin, "bot", SimpleNamespace(username="b")):
            admin.send_backup(self.ctx, ["hist"])
            first = self.shown[-1]
            admin.send_backup(self.ctx, ["hist", "2"])
            last = self.shown[-1]
        self.assertIn("bk:hist:1", self.data(first))
        self.assertEqual(last.text.count("?start=bk_"), 89 - 2 * admin.MAX_BACKUPS_LISTED)
        self.assertIn(files[-1]["name"].removesuffix(".json"), last.text)

    def test_no_backups_in_the_last_month(self):
        with mock.patch("hiddifypanel.panel.commercial.restapi.v2.admin.backup_api.list_files", lambda: self.files(40)):
            admin.send_backup(self.ctx, ["hist"])
        self.assertIn(t(T.bk_history_none_month, "en"), self.shown[-1].text)

    def test_a_backup_offers_a_key_per_domain_with_a_one_file_link(self):
        files = self.files(1)
        stem = files[0]["name"].removesuffix(".json")
        saved = {}
        links = [("secure", "panel.example.com", ""), ("insecure", "old.example.com", "")]
        with mock.patch("hiddifypanel.panel.commercial.restapi.v2.admin.backup_api.list_files", lambda: files), mock.patch(
            "hiddifypanel.cache.redis_client", SimpleNamespace(set=lambda k, v, ex=0: saved.update({k: v}), get=lambda k: None)
        ), mock.patch("hiddifypanel.panel.commercial.telegrambot.backup_msg.links", lambda owner: links), mock.patch(
            "hiddifypanel.models.hconfig", lambda key: "adminpath"
        ), mock.patch("hiddifypanel.panel.commercial.telegrambot.advanced.is_on", lambda: False):
            admin.send_backup(self.ctx, ["f", stem])
        screen = self.shown[-1]
        urls = [b.url for row in screen.markup.keyboard for b in row if b.url]
        key = next(iter(saved)).rsplit(":", 1)[1]
        self.assertEqual(list(saved.values()), [files[0]["name"]])  # the key gives that one file
        self.assertEqual(urls, [f"https://panel.example.com/adminpath/api/v1/tgbot/backup/{key}/", f"https://old.example.com/adminpath/api/v1/tgbot/backup/{key}/"])
        styles = [b.to_dict().get("style") for row in screen.markup.keyboard for b in row if b.url]
        self.assertEqual(styles, ["success", "danger"])

    def test_an_unknown_or_old_backup_is_gone(self):
        with mock.patch("hiddifypanel.panel.commercial.restapi.v2.admin.backup_api.list_files", lambda: self.files(45)), mock.patch(
            "hiddifypanel.panel.commercial.telegrambot.advanced.is_on", lambda: False
        ):
            self.assertIsNone(admin.backup_file_screen(self.ctx, "2020_01_01__00_00_00"))
            self.assertIsNone(admin.backup_file_screen(self.ctx, "../../etc/passwd"))

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
