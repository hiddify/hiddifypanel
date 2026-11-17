"""Each user's traffic per day (models/usage.py UserDailyUsage) and the bot's usage chart (telegrambot/chart.py)."""

import datetime
import io
import unittest
from types import SimpleNamespace
from unittest import mock

from apiflask import APIFlask
from PIL import Image

from hiddifypanel.database import db
from hiddifypanel.models.usage import UserDailyUsage
from hiddifypanel.panel.commercial.telegrambot import chart, ui
from hiddifypanel.panel.commercial.telegrambot.texts import T, t

TODAY = datetime.date(2026, 11, 17)
GB = 1024**3


class DailyTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = APIFlask(__name__)
        cls.app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False)
        db.init_app(cls.app)
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        UserDailyUsage.__table__.create(db.engine)

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        cls.ctx.pop()

    def setUp(self):
        UserDailyUsage.query.delete()
        db.session.commit()

    def test_a_day_adds_up_and_each_user_has_their_own(self):
        UserDailyUsage.add(TODAY, {1: 100, 2: 50, 3: 0})
        db.session.commit()
        UserDailyUsage.add(TODAY, {1: 25})
        db.session.commit()
        rows = {(r.user_id, r.date): r.usage for r in UserDailyUsage.query.all()}
        self.assertEqual(rows, {(1, TODAY): 125, (2, TODAY): 50})

    def test_the_last_days_oldest_first_with_empty_days(self):
        UserDailyUsage.add(TODAY - datetime.timedelta(days=2), {1: 7})
        UserDailyUsage.add(TODAY, {1: 9})
        db.session.commit()
        self.assertEqual(UserDailyUsage.last_days(1, 3, TODAY), [(TODAY - datetime.timedelta(days=2), 7), (TODAY - datetime.timedelta(days=1), 0), (TODAY, 9)])
        self.assertEqual(len(UserDailyUsage.last_days(1, 30, TODAY)), 30)

    def test_old_days_are_pruned(self):
        UserDailyUsage.add(TODAY - datetime.timedelta(days=UserDailyUsage.KEEP_DAYS + 1), {1: 1})
        UserDailyUsage.add(TODAY - datetime.timedelta(days=UserDailyUsage.KEEP_DAYS), {1: 2})
        db.session.commit()
        self.assertEqual(UserDailyUsage.prune(TODAY), 1)
        db.session.commit()
        self.assertEqual([r.usage for r in UserDailyUsage.query.all()], [2])


def days(values):
    first = TODAY - datetime.timedelta(days=len(values) - 1)
    return [(first + datetime.timedelta(days=i), v) for i, v in enumerate(values)]


class RenderTests(unittest.TestCase):
    def test_a_png_of_the_right_size_for_any_data(self):
        for values in ([0] * 30, [GB] * 30, [0] * 29 + [5 * GB], [i * 10**7 for i in range(30)], [3]):
            png = chart.render(days(values))
            image = Image.open(io.BytesIO(png))
            self.assertEqual((image.format, image.size), ("PNG", (chart.W, chart.H)))

    def test_short_numbers(self):
        self.assertEqual(chart._short(1.5 * GB), "1.5 GB")
        self.assertEqual(chart._short(350 * 1024**2), "350 MB")
        self.assertEqual(chart._short(250 * GB), "250 GB")


class CaptionTests(unittest.TestCase):
    def test_totals_and_the_busiest_day(self):
        ctx = ui.Ctx(1, "fa")
        text = chart.caption(ctx, SimpleNamespace(name="<Ann>"), days([GB, 3 * GB, 0, 2 * GB]))
        self.assertIn("&lt;Ann&gt;", text)
        self.assertIn(t(T.chart_peak, "fa"), text)
        self.assertIn((TODAY - datetime.timedelta(days=2)).isoformat(), text)

    def test_nothing_yet(self):
        text = chart.caption(ui.Ctx(1, "en"), SimpleNamespace(name="Ann"), days([0] * 30))
        self.assertIn(t(T.chart_empty, "en"), text)


class TargetTests(unittest.TestCase):
    def test_a_user_sees_only_their_own_and_an_admin_only_theirs(self):
        own = SimpleNamespace(id=1)
        self.assertIs(chart._target(ui.Ctx(1, "en", user=own), ["99"]), own)
        admin = SimpleNamespace(id=5)
        with mock.patch("hiddifypanel.panel.commercial.telegrambot.accounts.get_visible", lambda a, uid: own if uid == 1 else None):
            self.assertIs(chart._target(ui.Ctx(1, "en", admin=admin), ["1"]), own)
            self.assertIsNone(chart._target(ui.Ctx(1, "en", admin=admin), ["2"]))
            self.assertIsNone(chart._target(ui.Ctx(1, "en", admin=admin), []))
        self.assertIsNone(chart._target(ui.Ctx(1, "en"), ["1"]))


if __name__ == "__main__":
    unittest.main()
