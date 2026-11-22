"""The Menu key that always stays by the message box (telegrambot/menukey.py, handlers.on_text)."""

import json
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from telebot import types

from hiddifypanel.panel.commercial.restapi.v1.tgbot import bot as real_bot
from hiddifypanel.panel.commercial.telegrambot import handlers, menukey
from hiddifypanel.panel.commercial.telegrambot.texts import LANGUAGES, T, t


class EnsureTests(unittest.TestCase):
    def setUp(self):
        self.prefs = {}
        self.bot = mock.MagicMock()
        fake_pref = SimpleNamespace(get=lambda chat, key, default="": self.prefs.get((chat, key), default), put=lambda chat, key, value: self.prefs.__setitem__((chat, key), value))
        for p in (mock.patch.object(menukey, "bot", self.bot), mock.patch.object(menukey, "BotPref", fake_pref), mock.patch.object(menukey, "db")):
            p.start()
            self.addCleanup(p.stop)

    def test_once_per_chat_and_again_in_a_new_language_or_role(self):
        menukey.ensure(5, "fa")
        menukey.ensure(5, "fa")
        self.assertEqual(self.bot.send_message.call_count, 1)
        keys = json.loads(self.bot.send_message.call_args.kwargs["reply_markup"].to_json())
        self.assertEqual(keys["keyboard"], [[{"text": t(T.menu_key, "fa"), "style": "primary"}]])  # an admin: Menu only
        self.assertTrue(keys["is_persistent"] and keys["resize_keyboard"])
        menukey.ensure(5, "en")
        menukey.ensure(5, "en", person=True)
        self.assertEqual(self.bot.send_message.call_count, 3)

    def test_start_sends_it_again_after_a_cleared_chat(self):
        menukey.ensure(5, "fa", person=True)
        menukey.ensure(5, "fa", person=True)
        menukey.ensure(5, "fa", person=True, force=True)
        self.assertEqual(self.bot.send_message.call_count, 2)

    def test_only_one_hint_line_in_the_chat(self):
        self.bot.send_message.side_effect = [SimpleNamespace(message_id=70), SimpleNamespace(message_id=71)]
        menukey.ensure(5, "fa", person=True, force=True)
        menukey.ensure(5, "fa", person=True, force=True)
        self.bot.delete_message.assert_called_once_with(5, 70)

    def test_a_persons_keyboard(self):
        keys = json.loads(menukey.keyboard_for("fa", person=True).to_json())["keyboard"]
        self.assertEqual(
            [[b["text"] for b in row] for row in keys],
            [[t(T.guide, "fa"), t(T.doctor, "fa")], [t(T.chart, "fa"), t(T.support, "fa")], [t(T.hist_key, "fa"), t(T.settings, "fa")], [t(T.menu_key, "fa")]],
        )

    def test_every_key_in_every_language_opens_its_screen(self):
        from hiddifypanel.panel.commercial.telegrambot.ui import Cb

        for code in LANGUAGES:
            self.assertIs(menukey.action(t(T.guide, code)), Cb.guide)
            self.assertIs(menukey.action(t(T.support, code)), Cb.support)
        self.assertIsNone(menukey.action("hello"))

    def test_a_text_both_roles_have_opens_each_ones_own_screen(self):
        from hiddifypanel.panel.commercial.telegrambot.ui import Cb

        for code in LANGUAGES:  # Settings reads the same for both in English and Persian
            self.assertIs(menukey.action(t(T.settings, code)), Cb.settings, code)
            self.assertIs(menukey.action(t(T.btn_settings, code), admin=True), Cb.admin_settings, code)
        self.assertIsNone(menukey.action(t(T.btn_users, "en")))  # an admin's key is nothing for a person

    def test_a_failure_never_breaks_the_menu(self):
        self.bot.send_message.side_effect = RuntimeError("blocked")
        menukey.ensure(5, "en")
        self.assertEqual(self.prefs, {})

    def test_every_language_label_is_the_key(self):
        for code in LANGUAGES:
            self.assertTrue(menukey.is_menu(t(T.menu_key, code)))
        self.assertTrue(menukey.is_menu(f"  {t(T.menu_key, 'fa')} "))
        self.assertFalse(menukey.is_menu("menu please"))


class OpenKeyTests(unittest.TestCase):
    def test_a_person_gets_the_screen_an_admin_the_menu(self):
        from hiddifypanel.panel.commercial.telegrambot.ui import ROUTES, Cb

        called = []
        state = {"upanel": 55, "upanel_photo": True}
        fake_state = SimpleNamespace(get=lambda k, d=None: state.get(k, d), update=lambda **kw: state.update(kw))

        def person_ctx():
            c = SimpleNamespace(admin=None, user=SimpleNamespace(), message_id=7, on_photo=False, state=fake_state)
            c.on_panel = lambda: (setattr(c, "message_id", state.get("upanel")), setattr(c, "on_photo", state.get("upanel_photo")))
            return c

        with mock.patch.dict(ROUTES, {Cb.guide: SimpleNamespace(handler=lambda ctx, args: called.append(ctx))}), mock.patch.object(handlers, "open_home") as home:
            person = person_ctx()
            handlers._open_key(person, Cb.guide)
            self.assertEqual(called, [person])
            self.assertEqual((person.message_id, person.on_photo), (55, True))  # it takes the place of the screen shown now
            self.assertEqual(state["nav"], [["gd", []]])  # a first step: Back goes to the start
            handlers._open_key(person_ctx(), Cb.me)
            handlers._open_key(person_ctx(), Cb.users)  # an admin's key never opens an admin's screen for a person
            self.assertEqual(home.call_count, 2)


class AdminKeyTests(unittest.TestCase):
    def test_the_screen_comes_at_the_bottom_and_the_old_panel_goes(self):
        from hiddifypanel.panel.commercial.telegrambot.ui import ROUTES, Cb

        state = {"panel": 40}
        fake_state = SimpleNamespace(get=lambda k, d=None: state.get(k, d), update=lambda **kw: state.update(kw))
        admin = SimpleNamespace(admin=SimpleNamespace(), user=None, chat_id=5, message_id=40, state=fake_state)
        got = []

        def users(ctx, args):
            got.append((ctx.message_id, args))
            state["panel"] = 41

        with mock.patch.dict(ROUTES, {Cb.users: SimpleNamespace(handler=users)}), mock.patch.object(handlers, "open_home") as home, mock.patch.object(handlers, "_delete") as delete:
            handlers._open_key(admin, Cb.users, menukey.action_args(t(T.btn_users, "fa"), admin=True))
            self.assertEqual(got, [(None, ["a", "0"])])  # a new message, with the list's arguments
            delete.assert_called_once_with(5, 40)
            handlers._open_key(admin, Cb.guide)  # a person's key: the admin's home
            handlers._open_key(admin, Cb.home)
            self.assertEqual(home.call_count, 2)

    def test_each_level_sees_its_keys(self):
        def labels(mode):
            return [b["text"] for row in json.loads(menukey.keyboard_for("en", admin_mode=mode).to_json())["keyboard"] for b in row]

        owner, admin, agent = labels("super_admin"), labels("admin"), labels("agent")
        self.assertIn(t(T.btn_settings, "en"), agent)  # language and backup are in Settings
        self.assertNotIn(t(T.btn_backup, "en"), owner)
        self.assertIn(t(T.btn_status, "en"), agent)
        self.assertNotIn(t(T.btn_check, "en"), owner)  # Server Status holds the services now
        self.assertEqual(owner[-1], t(T.menu_key, "en"))
        self.assertEqual(menukey.admin_mode(SimpleNamespace(mode=SimpleNamespace(value="agent"))), "agent")
        self.assertIsNone(menukey.admin_mode(None))


class PressTests(unittest.TestCase):
    def test_pressing_it_opens_the_menu_and_stops_writing(self):
        state = {"awaiting": "support"}
        ctx = SimpleNamespace(admin=None, user=SimpleNamespace(), lang="fa", state=SimpleNamespace(get=state.get, update=lambda **kw: state.update(kw)))
        sent = []

        def fake(token, method_name, method="get", params=None, files=None):
            sent.append(method_name)
            return True

        update = {"update_id": int(time.time() * 1000) % 10**9, "message": {"message_id": 8, "date": 0, "chat": {"id": 5, "type": "private"}, "from": {"id": 5, "is_bot": False, "first_name": "A"}, "text": t(T.menu_key, "fa")}}
        with (
            mock.patch.object(handlers, "context", lambda *a, **k: ctx),
            mock.patch.object(handlers, "open_home") as home,
            mock.patch("telebot.apihelper._make_request", fake),
        ):
            real_bot.process_new_updates([types.Update.de_json(update)])
        home.assert_called_once_with(ctx)
        self.assertIsNone(state["awaiting"])
        self.assertIn("deleteMessage", sent)


class BrandTests(unittest.TestCase):
    def test_the_page_button_is_hiddify_in_every_language(self):
        from hiddifypanel.panel.commercial.telegrambot import ui, user as user_screens

        for lang in ("fa", "en", "ru", "zh"):
            ctx = ui.Ctx(5, lang, user=SimpleNamespace(name="Ann"))
            with (
                mock.patch.object(handlers, "menukey"),
                mock.patch.object(handlers.user, "set_menu_button") as menu_button,
                mock.patch.object(ui.Ctx, "show"),
                mock.patch.object(user_screens, "account_card", lambda u, lang, note=None: "CARD"),
                mock.patch("hiddifypanel.panel.commercial.telegrambot.widget.available", lambda: True),
                mock.patch.object(handlers.accounts, "links", lambda u: SimpleNamespace(home="https://panel.example.com/u/", sub="s", page="p")),
                mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
            ):
                handlers.open_home(ctx)
                self.assertEqual(menu_button.call_args.args[1], "Hiddify")
            with (
                mock.patch.object(user_screens.accounts, "links", lambda u: SimpleNamespace(home="https://panel.example.com/u/", sub="s", page="p")),
                mock.patch.object(user_screens, "account_card", lambda u, lang, note=None: "CARD"),
                mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
                mock.patch("hiddifypanel.panel.commercial.telegrambot.widget.available", lambda: True),
            ):
                data = [b.to_dict() for row in user_screens.home(ctx).markup.keyboard for b in row]
            # The card keeps Refresh and Links: the page is on the Hiddify button by the message box, the screens on
            # the keyboard
            self.assertEqual([b.get("callback_data") for b in data], ["me", "ml", "wg"], lang)


if __name__ == "__main__":
    unittest.main()


class StatusKeyRenameTests(unittest.TestCase):
    def test_new_and_old_labels_open_the_status(self):
        from hiddifypanel.panel.commercial.telegrambot import menukey
        from hiddifypanel.panel.commercial.telegrambot.ui import Cb

        actions = menukey._actions(True)
        self.assertEqual(actions["📊 Action & Status"][0], Cb.status)
        self.assertEqual(actions["📊 Server Status"][0], Cb.status)  # a chat may still show the old keyboard
        self.assertEqual(actions["📊 عملیات و وضعیت"][0], Cb.status)
