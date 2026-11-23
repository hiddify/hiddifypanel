"""A person's chat keeps one screen at a time, and Back goes one step back (telegrambot/nav.py, ui.Ctx.show)."""

import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import nav, ui
from hiddifypanel.panel.commercial.telegrambot.ui import Cb


class FakeState:
    def __init__(self, **values):
        self.values = dict(values)

    def get(self, key, default=None):
        return self.values.get(key, default)

    def update(self, **values):
        for k, v in values.items():
            if v is None:
                self.values.pop(k, None)
            else:
                self.values[k] = v


class Base(unittest.TestCase):
    def setUp(self):
        self.state = FakeState()
        p = mock.patch.object(ui.Ctx, "state", property(lambda _self: self.state))
        p.start()
        self.addCleanup(p.stop)
        self.bot = mock.MagicMock()
        for p in (mock.patch.object(ui, "bot", self.bot), mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False)):
            p.start()
            self.addCleanup(p.stop)

    def person(self, message_id=None, on_photo=False):
        c = ui.Ctx(5, "en", user=SimpleNamespace(), message_id=message_id, call_id="c")
        c.on_photo = on_photo
        return c


class PathTests(Base):
    def test_steps_and_the_same_screen_in_place(self):
        c = self.person()
        nav.reset(c, Cb.settings)
        nav.push(c, Cb.lang, [])
        nav.push(c, Cb.lang, [])
        self.assertEqual(self.state.get("nav"), [["se", []], ["lg", []]])
        nav.push(c, Cb.history, ["0"])
        nav.push(c, Cb.history, ["1"])  # another page: the same step
        self.assertEqual(self.state.get("nav")[-1], ["hs", ["1"]])

    def test_a_device_is_a_step_further_and_back_returns_to_the_list(self):
        c = self.person()
        nav.reset(c, Cb.guide)  # the keyboard key
        nav.push(c, Cb.guide, ["i"])  # iPhone
        self.assertEqual(self.state.get("nav"), [["gd", []], ["gd", ["i"]]])
        nav.push(c, Cb.guide, ["a"])  # another device in its place
        self.assertEqual(self.state.get("nav"), [["gd", []], ["gd", ["a"]]])
        nav.push(c, Cb.guide, [])  # "Another Device": the list again, no loop
        self.assertEqual(self.state.get("nav"), [["gd", []]])

    def test_what_is_a_step(self):
        self.assertTrue(nav.is_screen(Cb.lang, []))
        self.assertFalse(nav.is_screen(Cb.lang, ["fa"]))  # choosing a language is an action
        self.assertFalse(nav.is_screen(Cb.chart, ["r"]))  # refreshing the chart too
        self.assertFalse(nav.is_screen(Cb.pref, ["alerts", "0"]))

    def test_doing_something_is_not_an_admin_step(self):
        self.assertTrue(nav.is_admin_screen(Cb.bulk, ["a", "days", "30"]))  # the confirm screen
        self.assertFalse(nav.is_admin_screen(Cb.bulk, ["a", "days", "30", "1"]))  # doing it: Back is not its confirm
        self.assertTrue(nav.is_admin_screen(Cb.admin_card, ["9"]))
        self.assertFalse(nav.is_admin_screen(Cb.admin_card, ["9", "users", "50"]))
        self.assertTrue(nav.is_admin_screen(Cb.apply, []))
        self.assertFalse(nav.is_admin_screen(Cb.apply, ["go"]))
        self.assertFalse(nav.is_admin_screen(Cb.cfgtest, ["go"]))
        self.assertTrue(nav.is_admin_screen(Cb.lock, []))
        self.assertFalse(nav.is_admin_screen(Cb.lock, ["del", "1"]))

    def test_back_shows_the_screen_before(self):
        c = self.person(message_id=9)
        nav.reset(c, Cb.settings)
        nav.push(c, Cb.lang, [])
        shown = []
        with mock.patch.dict(ui.ROUTES, {Cb.settings: ui.Route(lambda ctx, args: shown.append(("se", args)), admin=False)}), mock.patch.object(ui.Ctx, "toast"):
            nav.go_back(c, [])
        self.assertEqual(shown, [("se", [])])
        self.assertEqual(self.state.get("nav"), [["se", []]])

    def test_back_at_the_first_step_goes_to_the_start(self):
        c = self.person(message_id=9)
        nav.reset(c, Cb.guide)
        with mock.patch("hiddifypanel.panel.commercial.telegrambot.handlers.open_home") as home, mock.patch.object(ui.Ctx, "toast"):
            nav.go_back(c, [])
        home.assert_called_once_with(c)
        self.assertEqual(self.state.get("nav"), [])


class OneScreenTests(Base):
    def setUp(self):
        super().setUp()
        self.bot.send_message.side_effect = lambda *a, **k: SimpleNamespace(message_id=100 + self.bot.send_message.call_count, photo=None)
        self.bot.send_photo.side_effect = lambda *a, **k: SimpleNamespace(message_id=200 + self.bot.send_photo.call_count, photo=[1])
        # classic cards here (a rich card refused); RichCardTests below has the rich ones
        for p in (
            mock.patch("hiddifypanel.panel.commercial.telegrambot.qr.render", lambda data: b"png"),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.rich.send_card", lambda *a, **k: None),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.rich.edit_card", lambda *a, **k: False),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_a_new_screen_message_takes_the_place_of_the_old_one(self):
        self.state.update(upanel=50, upanel_photo=True)
        c = self.person(message_id=50, on_photo=True)
        c.show(ui.Screen("text screen"))  # a photo cannot become text: a new message
        self.bot.delete_message.assert_called_once_with(5, 50)
        self.assertEqual(self.state.get("upanel"), 101)

    def test_an_edit_in_place_deletes_nothing(self):
        self.state.update(upanel=60, upanel_photo=False)
        c = self.person(message_id=60)
        c.show(ui.Screen("another text screen"))
        self.bot.edit_message_text.assert_called_once()
        self.bot.delete_message.assert_not_called()
        self.assertEqual(self.state.get("upanel"), 60)

    def test_the_card_comes_back_as_a_photo_from_a_text_screen(self):
        self.state.update(upanel=60, upanel_photo=False)
        c = self.person(message_id=60)
        c.show(ui.Screen("card", None, qr="sub"))
        self.bot.edit_message_text.assert_not_called()
        self.bot.send_photo.assert_called_once()
        self.bot.delete_message.assert_called_once_with(5, 60)
        self.assertEqual((self.state.get("upanel"), self.state.get("upanel_photo")), (201, True))

    def test_an_admin_also_keeps_one_screen(self):
        c = ui.Ctx(5, "en", admin=SimpleNamespace(), message_id=None)
        self.state.update(upanel=70)
        c.show(ui.Screen("admin screen"))
        self.bot.delete_message.assert_called_once_with(5, 70)

    def test_an_admins_steps(self):
        self.assertTrue(nav.is_admin_screen(Cb.card, ["7"]))
        self.assertTrue(nav.is_admin_screen(Cb.bandwidth, ["d7"]))
        self.assertFalse(nav.is_admin_screen(Cb.bandwidth, ["d15", "r"]))  # another period in place
        self.assertFalse(nav.is_admin_screen(Cb.act, ["7", "reset"]))  # an action
        c = ui.Ctx(5, "en", admin=SimpleNamespace())
        nav.reset(c, Cb.users, ["a", "0"])
        nav.push(c, Cb.users, ["c", "1", "u"])  # another filter: the same step
        nav.push(c, Cb.card, ["7"])
        self.assertEqual(self.state.get("nav"), [["ul", ["c", "1", "u"]], ["uc", ["7"]]])



class RichCardTests(Base):
    def test_the_card_comes_back_in_the_same_message(self):
        self.state.update(upanel=60, upanel_photo=False)
        c = self.person(message_id=60)
        edits = []
        with mock.patch("hiddifypanel.panel.commercial.telegrambot.qr.render", lambda data: b"png"), mock.patch("hiddifypanel.panel.commercial.telegrambot.rich.edit_card", lambda *a, **k: edits.append(a) or True):
            c.show(ui.Screen("card", None, qr="sub"))
        self.assertEqual(edits[0][:2], (5, 60))  # this chat, this message: in place
        self.bot.send_photo.assert_not_called()
        self.bot.delete_message.assert_not_called()
        self.assertEqual((self.state.get("upanel"), self.state.get("upanel_photo")), (60, False))


if __name__ == "__main__":
    unittest.main()
