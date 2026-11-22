"""Send Message: to the users or to the admins (all of them, or one found by name, Telegram ID or @username)."""

import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import broadcast, ui
from hiddifypanel.panel.commercial.telegrambot.texts import T, t


class FakeState(dict):
    def update(self, **values):
        for k, v in values.items():
            if v is None:
                self.pop(k, None)
            else:
                self[k] = v


class Base(unittest.TestCase):
    def setUp(self):
        self.state = FakeState()
        self.shown = []
        self.people = [
            SimpleNamespace(id=2, name="Shop North", telegram_id=702),
            SimpleNamespace(id=3, name="Shop South", telegram_id=None),
            SimpleNamespace(id=4, name="Reseller", telegram_id=704),
        ]
        for p in (
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
            mock.patch.object(ui.Ctx, "state", property(lambda _s: self.state)),
            mock.patch.object(ui.Ctx, "toast", lambda s, text=None, alert=False: None),
            mock.patch.object(ui.Ctx, "show", lambda s, screen: self.shown.append(screen)),
            mock.patch.object(broadcast.menukey, "prompt", lambda *a, **k: None),
            mock.patch.object(broadcast, "_admins_under", lambda admin: list(self.people)),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.usernames.chats_of", lambda q: [704] if q.lstrip("@") == "reseller" else []),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.ctx = ui.Ctx(5, "en", admin=SimpleNamespace(id=1, name="Ann", mode="super_admin"))

    def data(self, screen):
        return [b.callback_data for row in screen.markup.keyboard for b in row if b.callback_data]


class AudienceTests(Base):
    def test_users_or_admins_first(self):
        broadcast.show_broadcast(self.ctx, [])
        self.assertEqual(self.data(self.shown[-1]), ["bc:u", "bc:a", "bb"])
        broadcast.show_broadcast(self.ctx, ["u"])
        self.assertEqual(self.data(self.shown[-1]), ["bc:all", "bc:one", "bb"])  # the users' two keys, as before
        broadcast.show_broadcast(self.ctx, ["a"])
        self.assertEqual(self.data(self.shown[-1]), ["bc:aall", "bc:aone", "bb"])


class AllAdminsTests(Base):
    def test_all_admins_with_the_bot(self):
        broadcast.show_broadcast(self.ctx, ["aall"])
        self.assertIn(t(T.bc_admins_count, "en", n=2), self.shown[-1].text)
        self.assertEqual(broadcast._chats(self.ctx), [702, 704])
        self.assertEqual(self.state.get("awaiting"), broadcast.AWAITING)


class OneAdminTests(Base):
    def test_by_name_id_or_username(self):
        broadcast._find_admin(self.ctx, "north")
        self.assertEqual(self.state.get("bc_admin"), 2)
        self.assertEqual(broadcast._chats(self.ctx), [702])
        broadcast._find_admin(self.ctx, "704")
        self.assertEqual(self.state.get("bc_admin"), 4)
        broadcast._find_admin(self.ctx, "@reseller")
        self.assertEqual(self.state.get("bc_admin"), 4)

    def test_several_are_offered(self):
        broadcast._find_admin(self.ctx, "shop")
        self.assertEqual(self.data(self.shown[-1])[:2], ["bc:ato:2", "bc:ato:3"])

    def test_without_the_bot_or_unknown(self):
        broadcast._find_admin(self.ctx, "south")
        self.assertIn(t(T.bc_one_no_bot, "en", name="Shop South"), self.shown[-1].text)
        broadcast._find_admin(self.ctx, "nobody")
        self.assertIn(t(T.bc_one_admin_none, "en", q="nobody"), self.shown[-1].text)
        broadcast._pick_admin(self.ctx, 99)  # not under this admin
        self.assertIsNone(self.state.get("bc_admin"))


class NavTests(unittest.TestCase):
    def test_each_choice_is_a_back_step(self):
        from hiddifypanel.panel.commercial.telegrambot import nav
        from hiddifypanel.panel.commercial.telegrambot.ui import Cb

        state = FakeState()
        with mock.patch.object(ui.Ctx, "state", property(lambda _s: state)):
            ctx = ui.Ctx(5, "en", admin=SimpleNamespace(id=1, mode="super_admin"))
            nav.reset(ctx, Cb.broadcast, [])
            nav.push(ctx, Cb.broadcast, ["a"])
            nav.push(ctx, Cb.broadcast, ["aall"])
            self.assertEqual(state["nav"], [["bc", []], ["bc", ["a"]], ["bc", ["aall"]]])
            nav.reset(ctx, Cb.backup, ["hist"])
            nav.push(ctx, Cb.backup, ["hist", "1"])  # another page of the history: the same step
            nav.push(ctx, Cb.backup, ["f", "2026_11_22__22_41_10"])  # one backup: a step further
            self.assertEqual(state["nav"], [["bk", ["hist", "1"]], ["bk", ["f", "2026_11_22__22_41_10"]]])


if __name__ == "__main__":
    unittest.main()
