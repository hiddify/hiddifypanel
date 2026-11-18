"""The bot's user lists come a page at a time from the database, and keep the same users the old in-memory filters
kept (telegrambot/accounts.py: users_page, search_page, summary)."""

import datetime
import unittest
from types import SimpleNamespace

from apiflask import APIFlask

from hiddifypanel.database import db
from hiddifypanel.models import User
from hiddifypanel.panel.commercial.telegrambot import accounts
from hiddifypanel.panel.commercial.telegrambot.accounts import Filter

NOW = datetime.datetime.now()
GB = 1024**3


class PagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = APIFlask(__name__)
        cls.app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False)
        db.init_app(cls.app)
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        User.__table__.create(db.engine)

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        cls.ctx.pop()

    def setUp(self):
        User.query.delete()
        db.session.commit()
        db.session.expunge_all()
        self.users = []
        for i in range(30):
            kind = i % 5
            user = User(
                name=f"user {i}" if i != 7 else "50% off_x",
                comment="vip" if i == 3 else "",
                telegram_id=1000 + i,
                added_by=2 if i == 29 else 1,  # the last one belongs to another admin
                deleted=i == 28,
                enable=kind != 1,
                package_days=30,
                start_date=(NOW - datetime.timedelta(days=40 if kind == 2 else 27 if kind == 3 else 1)).date(),
                usage_limit=10 * GB,
                current_usage=11 * GB if kind == 4 else 1 * GB,
                last_online=NOW - datetime.timedelta(minutes=1 if i % 3 == 0 else 60),
            )
            db.session.add(user)
            self.users.append(user)
        db.session.commit()
        self.admin = SimpleNamespace(recursive_users_query=lambda: User.query.filter(User.added_by.in_([1]), User.deleted.is_(False)))

    def visible(self):
        return sorted((u for u in self.users if u.added_by == 1 and not u.deleted), key=lambda u: -u.id)

    def test_each_filter_keeps_what_the_old_in_memory_filter_kept_in_the_same_order(self):
        for f in Filter:
            expected = [u.id for u in self.visible() if accounts.matches(u, f)]
            got, page = [], 0
            while True:
                found = accounts.users_page(self.admin, f, page, 8)
                self.assertEqual(found.total, len(expected), f)
                got += [u.id for u in found.users]
                if page >= found.pages - 1:
                    break
                page += 1
            self.assertEqual(got, expected, f)
            self.assertTrue(expected or f is Filter.expiring, f)

    def test_a_page_past_the_end_shows_the_last_one(self):
        found = accounts.users_page(self.admin, Filter.all, 99, 8)
        self.assertEqual((found.page, found.pages, found.total), (3, 4, 28))
        self.assertEqual(len(found.users), 4)
        self.assertEqual(accounts.users_page(self.admin, Filter.all, -3, 8).page, 0)

    def test_search_by_name_comment_uuid_or_telegram_id_any_case(self):
        names = lambda found: [u.name for u in found.users]
        self.assertEqual(names(accounts.search_page(self.admin, "USER 1", 0, 50)), ["user 19", "user 18", "user 17", "user 16", "user 15", "user 14", "user 13", "user 12", "user 11", "user 10", "user 1"])
        self.assertEqual(names(accounts.search_page(self.admin, "vip", 0, 50)), ["user 3"])
        self.assertEqual(names(accounts.search_page(self.admin, "1005", 0, 50)), ["user 5"])
        self.assertEqual(names(accounts.search_page(self.admin, self.users[4].uuid[:13].upper(), 0, 50)), ["user 4"])

    def test_search_wildcards_are_plain_characters(self):
        self.assertEqual([u.name for u in accounts.search_page(self.admin, "50%", 0, 50).users], ["50% off_x"])
        self.assertEqual(accounts.search_page(self.admin, "%", 0, 50).total, 1)
        self.assertEqual(accounts.search_page(self.admin, "f_x", 0, 50).total, 1)
        self.assertEqual(accounts.search_page(self.admin, "_", 0, 50).total, 1)

    def test_search_never_reaches_other_admins_or_deleted_users(self):
        self.assertEqual(accounts.search_page(self.admin, "user 29", 0, 50).total, 0)
        self.assertEqual(accounts.search_page(self.admin, "user 28", 0, 50).total, 0)
        self.assertEqual(accounts.search_page(self.admin, "  ", 0, 50).total, 0)

    def test_the_home_summary_counts_like_before(self):
        users = self.visible()
        counts = accounts.summary(self.admin)
        self.assertEqual(counts.total, len(users))
        self.assertEqual(counts.active, sum(accounts.status(u) is accounts.Status.active for u in users))
        self.assertEqual(counts.online, sum(accounts.is_online(u) for u in users))
        self.assertEqual(counts.expiring, sum(accounts.is_expiring(u) for u in users))


class PagerTests(unittest.TestCase):
    def test_no_blank_arrows(self):
        from unittest import mock

        from hiddifypanel.panel.commercial.telegrambot import admin, ui

        with mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False):
            labels = lambda page, pages: [b.text for b in admin._pager(ui.Cb.users, ["a"], page, pages)]
            self.assertEqual(labels(0, 1), [])
            self.assertEqual(labels(0, 3), ["1 / 3", "›"])
            self.assertEqual(labels(1, 3), ["‹", "2 / 3", "›"])
            self.assertEqual(labels(2, 3), ["‹", "3 / 3"])
            self.assertEqual(labels(0, 6), ["1 / 6", "›", "»"])  # a long list: a jump to the far end
            self.assertEqual(labels(3, 6), ["«", "‹", "4 / 6", "›", "»"])
            self.assertEqual(labels(5, 6), ["«", "‹", "6 / 6"])
            sorted_ = [b.callback_data for b in admin._pager(ui.Cb.users, ["a"], 1, 3, ["u"])]
            self.assertEqual(sorted_, ["ul:a:0:u", None, "ul:a:2:u"])  # the order stays when paging; the page shown does nothing
            self.assertIn("disabled", admin._pager(ui.Cb.users, ["a"], 1, 3, ["u"])[1].to_dict())


class ListTests(unittest.TestCase):
    """The users list: two lines per user, two names per row of buttons, tabs with counts, the sort button."""

    def setUp(self):
        import datetime
        from types import SimpleNamespace
        from unittest import mock

        from hiddifypanel.panel.commercial.telegrambot import accounts, admin, ui

        self.admin, self.ui, self.accounts = admin, ui, accounts
        now = datetime.datetime.now()
        GB = 1024**3

        def user(i, name, used, days, start=True, enable=True, seen=None):
            return SimpleNamespace(
                id=i, name=name, enable=enable, current_usage=used * GB, usage_limit=10 * GB, current_usage_GB=used, usage_limit_GB=10,
                start_date=now.date() if start else None, remaining_days=days, package_days=30, last_online=seen,
            )

        self.users = [
            user(3, "کاربر نمونه", 9, 20, seen=now),
            user(2, "bob", 1, 2, seen=now - datetime.timedelta(days=2)),
            user(1, "ann", 0, 30, start=False),
        ]
        self.page = accounts.Page(self.users, 3, 0, 1)
        self.counts = {f: n for f, n in zip(accounts.Filter, (3, 3, 2, 0, 1))}
        for p in (
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
            mock.patch.object(accounts, "list_page", lambda *a: self.page),
            mock.patch.object(accounts, "counts", lambda a: self.counts),
            mock.patch.object(ui.Ctx, "state", property(lambda _s: SimpleNamespace(update=lambda **k: None, get=lambda *a: None))),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.ctx = ui.Ctx(1, "en", admin=SimpleNamespace(id=1))

    def test_the_screen(self):
        from hiddifypanel.panel.commercial.telegrambot.texts import T, t

        screen = self.admin.users_screen(self.ctx, self.accounts.Filter.all, 0, self.accounts.Sort.usage)
        rows = [[b.text for b in row] for row in screen.markup.keyboard]
        self.assertEqual(rows[0], ["✓ 👥 3", "🟢 3", "⏳ 2", "🔴 0", "⚡️ 1"])
        self.assertEqual(len(rows[1]), 2)  # two names to a row
        self.assertIn("\u2068کاربر نمونه\u2069", rows[1][0])  # a Persian name keeps its own direction
        self.assertTrue(all(b.startswith("\u200e\u2068") for b in rows[1] + rows[2]))  # every row the same way round
        buttons = [b.to_dict() for row in screen.markup.keyboard[1:3] for b in row]
        self.assertEqual([b.get("style") for b in buttons], ["success", "success", "success"])  # the colour is the state
        self.assertFalse(any(dot in b["text"] for b in buttons for dot in ("🟢", "🔴", "⚪️", "🟠")))  # no dots
        self.assertTrue(rows[1][0].endswith("⚡️"))  # online
        self.assertTrue(all(line.startswith("\u200e") for line in screen.text.split("<blockquote>")[1].split("</blockquote>")[0].split("\n")))
        self.assertEqual(rows[-2][1], t(T.sort_by, "en", by=t(T.sort_days, "en")))  # the next order
        self.assertEqual(screen.markup.keyboard[-1][0].callback_data, "bb")  # Back, one step
        self.assertIn("<blockquote>", screen.text)
        self.assertIn(t(T.lst_left, "en", n=2), screen.text)
        self.assertIn(t(T.lst_not_started, "en"), screen.text)
        self.assertIn("⚡️", screen.text.split("\n")[3])  # the online one is marked

    def test_the_orders(self):
        key = lambda sort: [u.name for u in sorted(self.users, key=self.accounts._sort_key(sort))]
        S = self.accounts.Sort
        self.assertEqual(key(S.new), ["کاربر نمونه", "bob", "ann"])
        self.assertEqual(key(S.usage), ["کاربر نمونه", "bob", "ann"])
        self.assertEqual(key(S.days), ["bob", "کاربر نمونه", "ann"])
        self.assertEqual(key(S.seen), ["کاربر نمونه", "bob", "ann"])
        self.assertEqual(key(S.name), ["ann", "bob", "کاربر نمونه"])


if __name__ == "__main__":
    unittest.main()
