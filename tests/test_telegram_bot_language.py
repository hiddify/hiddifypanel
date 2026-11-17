"""The Telegram bot's language: the account's choice, else the person's Telegram language, else the panel default;
the language screen and the command list (telegrambot/texts.py, ui.py, settings.py)."""

import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.models import Lang
from hiddifypanel.panel.commercial.telegrambot import settings, texts, ui


class SupportedTests(unittest.TestCase):
    def test_telegram_codes_become_the_bot_languages(self):
        self.assertEqual(texts.supported("fa"), "fa")
        self.assertEqual(texts.supported("pt-br"), "pt")
        self.assertEqual(texts.supported("zh_hans"), "zh")
        self.assertEqual(texts.supported("EN-us"), "en")
        self.assertIsNone(texts.supported("xx"))
        self.assertIsNone(texts.supported(None))

    def test_every_panel_language_has_a_name(self):
        self.assertEqual(set(texts.LANGUAGES), {lang.name for lang in Lang})


class LangOfTests(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(ui, "hconfig", lambda key: "en")
        p.start()
        self.addCleanup(p.stop)

    def test_the_account_choice_comes_first(self):
        self.assertEqual(ui.lang_of(SimpleNamespace(lang=Lang.ru), admin=False, telegram="fa"), "ru")

    def test_then_the_telegram_language(self):
        self.assertEqual(ui.lang_of(SimpleNamespace(lang=None), admin=False, telegram="fa-IR"), "fa")
        self.assertEqual(ui.lang_of(None, admin=False, telegram="de"), "de")

    def test_then_the_panel_default(self):
        self.assertEqual(ui.lang_of(SimpleNamespace(lang=None), admin=True, telegram="xx"), "en")
        self.assertEqual(ui.lang_of(None, admin=True), "en")


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None):
        self.data[key] = value


class FakeCtx(ui.Ctx):
    """A Ctx whose show / toast are recorded (Ctx itself has slots)."""


def ctx(lang="en", *, admin=None, user=None, message_id=None):
    c = FakeCtx(42, lang, admin=admin, user=user, message_id=message_id)
    c.show = mock.MagicMock()
    c.toast = mock.MagicMock()
    return c


class LanguageScreenTests(unittest.TestCase):
    def setUp(self):
        p = mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False)
        p.start()
        self.addCleanup(p.stop)

    def buttons(self, screen):
        return [b.to_dict() for row in screen.markup.keyboard for b in row]

    def test_the_language_spoken_now_is_blue_and_every_language_is_there(self):
        screen = settings.language_screen(ctx("fa", user=SimpleNamespace()))
        buttons = self.buttons(screen)
        self.assertFalse([b for b in buttons if b.get("style")])  # no blue: unreadable in some themes
        marked = [b["callback_data"] for b in buttons if b["text"].startswith(ui.SELECTED)]
        self.assertEqual(marked, ["lg:fa"])
        self.assertEqual({b["callback_data"] for b in buttons if b["callback_data"].startswith("lg:")}, {f"lg:{c}" for c in texts.LANGUAGES})
        self.assertEqual(buttons[-1]["callback_data"], "bb")  # one step back (to settings)

    def test_back_is_one_step_for_an_admin_and_nowhere_for_a_stranger(self):
        self.assertEqual(self.buttons(settings.language_screen(ctx(admin=SimpleNamespace())))[-1]["callback_data"], "bb")
        self.assertTrue(self.buttons(settings.language_screen(ctx()))[-1]["callback_data"].startswith("lg:"))


class ChooseLanguageTests(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        patches = [
            mock.patch.object(settings, "redis_client", self.redis),
            mock.patch.object(settings, "db"),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.handlers.open_home"),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.handlers._delete"),
        ]
        self.mocks = [p.start() for p in patches]
        for p in patches:
            self.addCleanup(p.stop)

    def test_an_account_keeps_its_language(self):
        user = SimpleNamespace(lang=None)
        c = ctx(user=user, message_id=7)
        settings.choose_language(c, ["ru"])
        self.assertEqual(user.lang, Lang.ru)
        self.assertEqual(c.lang, "ru")
        self.mocks[1].session.commit.assert_called_once()
        self.mocks[3].assert_called_once_with(42, 7)
        self.mocks[2].assert_called_once_with(c)

    def test_a_stranger_keeps_it_by_chat(self):
        c = ctx()
        settings.choose_language(c, ["de"])
        self.assertEqual(settings.chat_lang(42), "de")
        self.assertEqual(c.lang, "de")

    def test_an_unknown_code_shows_the_languages(self):
        c = ctx(user=SimpleNamespace(lang=None))
        with mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False):
            settings.choose_language(c, ["xx"])
        c.show.assert_called_once()
        self.mocks[2].assert_not_called()


class CommandsTests(unittest.TestCase):
    def test_commands_are_set_in_every_language_and_for_everyone_else(self):
        fake_bot = mock.MagicMock()
        with mock.patch.object(settings, "bot", fake_bot):
            settings.set_commands()
        private = [c for c in fake_bot.set_my_commands.call_args_list if "scope" not in c.kwargs]
        groups = [c for c in fake_bot.set_my_commands.call_args_list if "scope" in c.kwargs]
        self.assertEqual([c.kwargs["language_code"] for c in private], [None, *texts.LANGUAGES])
        self.assertEqual([c.command for c in private[0].args[0]], ["start", "menu", "language"])
        self.assertEqual(len(groups), len(texts.LANGUAGES) + 1)
        self.assertEqual([(c.command, c.is_ephemeral) for c in groups[0].args[0]], [("me", True)])

    def test_a_failure_in_one_language_does_not_stop_the_others(self):
        fake_bot = mock.MagicMock()
        fake_bot.set_my_commands.side_effect = [RuntimeError("x")] + [None] * (2 * len(texts.LANGUAGES) + 1)
        with mock.patch.object(settings, "bot", fake_bot):
            settings.set_commands()
        self.assertEqual(fake_bot.set_my_commands.call_count, 2 * (len(texts.LANGUAGES) + 1))


if __name__ == "__main__":
    unittest.main()
