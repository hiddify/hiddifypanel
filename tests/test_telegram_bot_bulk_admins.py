"""Advanced mode: bulk actions on users and the admins' screens."""

import json
import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import admins, bulk, ui
from hiddifypanel.panel.commercial.telegrambot.accounts import Filter
from hiddifypanel.panel.commercial.telegrambot.texts import T, t

ADV = "hiddifypanel.panel.commercial.telegrambot.advanced.is_on"


class FakeUser(SimpleNamespace):
    def reset_usage(self):
        self.current_usage = 0

    def remove(self, commit=True):
        self.deleted = True


def user(i, enable=True):
    return FakeUser(id=i, name=f"u{i}", enable=enable, is_active=enable, package_days=30, usage_limit_GB=10, current_usage=5, start_date=None, deleted=False)


class FakeState(dict):
    def update(self, **values):
        for k, v in values.items():
            if v is None:
                self.pop(k, None)
            else:
                self[k] = v


class FakeRedis(dict):
    def get(self, key):
        return dict.get(self, key)

    def set(self, key, value, **_kw):
        self[key] = value

    def delete(self, *keys):
        for k in keys:
            self.pop(k, None)


class Base(unittest.TestCase):
    def setUp(self):
        self.state = FakeState()
        self.redis = FakeRedis()
        for p in (
            mock.patch("hiddifypanel.cache.redis_client", self.redis),
            mock.patch.object(ui.Ctx, "state", property(lambda _s: self.state)),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
            mock.patch(ADV, lambda: True),
            mock.patch.object(bulk.accounts, "is_read_only", lambda: False),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.admin = SimpleNamespace(id=1, name="Ann", mode="admin", telegram_id=5, room_to_activate=lambda n: min(n, 1))
        self.ctx = ui.Ctx(5, "en", admin=self.admin)
        self.toasts = []
        self.shown = []
        for p in (
            mock.patch.object(ui.Ctx, "toast", lambda s, text=None, alert=False: self.toasts.append(text)),
            mock.patch.object(ui.Ctx, "show", lambda s, screen: self.shown.append(screen)),
        ):
            p.start()
            self.addCleanup(p.stop)

    def data(self, screen):
        return [b.callback_data for row in screen.markup.keyboard for b in row if b.callback_data]


class BulkTests(Base):
    def setUp(self):
        super().setUp()
        self.users = [user(1), user(2, enable=False), user(3, enable=False)]
        self.admin.recursive_users_query = lambda: mock.MagicMock(**{"filter.return_value.order_by.return_value.all.return_value": list(self.users)})
        for p in (
            mock.patch.object(bulk, "targets", lambda ctx, f: list(self.users)),
            mock.patch.object(bulk.db, "session", mock.MagicMock()),
            mock.patch.object(bulk.accounts, "apply", lambda users: None),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_steps_pick_confirm_do(self):
        self.admin.room_to_activate = lambda n: n  # room for everyone here
        bulk.show_bulk(self.ctx, ["a"])
        self.assertIn("bu:a:days:30", self.data(self.shown[-1]))
        bulk.show_bulk(self.ctx, ["a", "days", "30"])
        self.assertIn("bu:a:days:30:1", self.data(self.shown[-1]))
        self.assertIn("u1, u2, u3", self.shown[-1].text)
        self.assertEqual(self.users[0].package_days, 30)  # nothing before the confirm
        bulk.show_bulk(self.ctx, ["a", "days", "30", "1"])
        self.assertEqual([u.package_days for u in self.users], [60, 60, 60])
        self.assertIn(t(T.bu_done, "en", what="+30 " + t(T.unit_d, "en"), n=3), self.shown[-1].text)

    def test_only_the_offered_values(self):
        bulk.show_bulk(self.ctx, ["a", "days", "999", "1"])
        self.assertEqual(self.users[0].package_days, 30)

    def test_turning_on_stops_at_the_limit(self):
        done, skipped = bulk.run(self.ctx, Filter.all, "on", 0)
        self.assertEqual((done, skipped), (1, 1))
        self.assertEqual([u.enable for u in self.users], [True, True, False])

    def test_the_panel_keeps_one_user(self):
        with mock.patch.object(bulk.User, "query", mock.MagicMock(**{"filter.return_value.count.return_value": 3})), mock.patch("hiddifypanel.hutils.apply_users.quick_apply_users"), mock.patch(
            "hiddifypanel.hutils.node.parent.notify_childs_users_changed"
        ):
            done, skipped = bulk.run(self.ctx, Filter.all, "del", 0)
        self.assertEqual((done, skipped), (2, 1))
        self.assertEqual([u.deleted for u in self.users], [True, True, False])

    def test_more_days_for_ended_packages_keep_the_active_limit(self):
        for u in self.users:
            u.is_active = u.enable  # the switched-off ones are the inactive ones here
        done, skipped = bulk.run(self.ctx, Filter.all, "days", 30)  # room for 1 of the 2 inactive
        self.assertEqual((done, skipped), (2, 1))
        self.assertEqual([u.package_days for u in self.users], [60, 60, 30])

    def test_renew_keeps_the_active_limit(self):
        for u in self.users:
            u.is_active = u.enable
        done, skipped = bulk.run(self.ctx, Filter.all, "renew", 0)  # room for 1 of the 2 disabled
        self.assertEqual((done, skipped), (2, 1))
        self.assertEqual([u.enable for u in self.users], [True, True, False])

    def test_the_confirmed_users_are_the_ones_changed(self):
        bulk.confirm_screen(self.ctx, Filter.all, "days", 30)
        self.assertEqual(json.loads(self.redis["tgbot:bulk:5"])["ids"], [1, 2, 3])
        shown = [self.users[0]]  # the list changed after the confirm: only the shown ones still there
        query = mock.MagicMock(**{"filter.return_value.order_by.return_value.all.return_value": shown})
        self.admin.recursive_users_query = lambda: query
        done, _ = bulk.run(self.ctx, Filter.all, "days", 30)
        self.assertEqual(done, 1)
        self.assertNotIn("tgbot:bulk:5", self.redis)  # read once

    def test_off_while_advanced_is_off(self):
        with mock.patch(ADV, lambda: False):
            bulk.show_bulk(self.ctx, [])
            self.assertEqual(bulk.list_row(self.ctx), [])
        self.assertEqual(self.shown, [])


class AdminsTests(Base):
    def test_a_super_admin_is_only_a_super_admins(self):
        owner = SimpleNamespace(id=1, mode="super_admin")
        people = [SimpleNamespace(id=2, mode="super_admin"), SimpleNamespace(id=3, mode="agent")]
        model = mock.MagicMock()
        model.get_super_admin.return_value = owner
        model.query.filter.return_value.order_by.return_value.all.return_value = people
        actor = SimpleNamespace(id=5, mode="admin", recursive_sub_admins_ids=lambda: [5, 2, 3])
        with mock.patch.object(admins, "AdminUser", model):
            self.assertEqual([a.id for a in admins.under(ui.Ctx(5, "en", admin=actor))], [3])
            actor.mode = "super_admin"
            self.assertEqual([a.id for a in admins.under(ui.Ctx(5, "en", admin=actor))], [2, 3])

    def test_a_new_agent_gets_nothing_its_creator_lacks(self):
        from hiddifypanel import admin_capabilities as caps

        made = {}
        model = mock.MagicMock(side_effect=lambda **kw: made.update(kw) or SimpleNamespace(**kw))
        with mock.patch.object(admins, "AdminUser", model), mock.patch.object(admins.db, "session", mock.MagicMock()), mock.patch(
            "hiddifypanel.hutils.node.parent.notify_childs_users_changed"
        ), mock.patch.object(caps, "of", lambda a: {k: False for k in caps.ALL}):
            admins.create_agent(self.ctx, "Shop")
        self.assertFalse(any(made["capabilities"].values()))

    def test_agents_do_not_get_it(self):
        agent = ui.Ctx(6, "en", admin=SimpleNamespace(id=2, name="Bo", mode="agent", telegram_id=6))
        self.assertFalse(admins.allowed(agent))
        self.assertTrue(admins.allowed(self.ctx))

    def test_card_outside_the_tree_is_gone(self):
        with mock.patch.object(admins, "under", lambda ctx: []):
            admins.show_admin_card(self.ctx, ["9", "off", "0"])
        self.assertEqual(self.shown, [])
        self.assertEqual(self.toasts[-1], t(T.gone, "en"))

    def test_limit_steps_only(self):
        a = SimpleNamespace(id=9, name="Shop", mode="agent", enable=True, max_users=100, max_active_users=100)
        with mock.patch.object(admins, "visible", lambda ctx, i: a), mock.patch.object(admins.db, "session", mock.MagicMock()), mock.patch.object(admins, "card_screen", lambda ctx, a, note=None: note), mock.patch(
            "hiddifypanel.hutils.node.parent.notify_childs_users_changed"
        ), mock.patch.object(admins.accounts, "is_read_only", lambda: False):
            admins.show_admin_card(self.ctx, ["9", "users", "50"])
            admins.show_admin_card(self.ctx, ["9", "users", "5000"])
            admins.show_admin_card(self.ctx, ["9", "off", "0"])
        self.assertEqual(a.max_users, 150)
        self.assertFalse(a.enable)


if __name__ == "__main__":
    unittest.main()
