"""Support inside the bot (telegrambot/support.py, free.py): private both ways, receipts, the person's screen, media."""

import datetime
import json
import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.models.message import Sender
from hiddifypanel.panel.commercial.telegrambot import free, support, ui
from hiddifypanel.panel.commercial.telegrambot.texts import T, t



def plain(text):
    """The text as an older app shows it: a smart date's own text."""
    import re

    return re.sub(r"<tg-time [^>]*>(.*?)</tg-time>", r"\1", text)

class FakeRedis:
    def __init__(self):
        self.data = {}
        self.lists = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None, nx=False):
        self.data[key] = value
        return True

    def incr(self, key):
        self.data[key] = int(self.data.get(key) or 0) + 1
        return self.data[key]

    def expire(self, key, ttl):
        pass

    def rpush(self, key, value):
        self.lists.setdefault(key, []).append(value)

    def ltrim(self, key, start, end):
        self.lists[key] = self.lists.get(key, [])[start:] if end == -1 else self.lists.get(key, [])[start : end + 1]

    def lrange(self, key, start, end):
        return list(self.lists.get(key, []))

    def delete(self, key):
        self.lists.pop(key, None)
        self.data.pop(key, None)


def message(sender, text, minutes=0):
    return SimpleNamespace(sender=sender.value, kind="text", text=text, created_at=datetime.datetime.now() - datetime.timedelta(minutes=minutes))


def conv(**kw):
    base = dict(id=9, admin_id=1, telegram_id=500, name="Ann", username=None, user_uuid=None, unread=1, messages=[])
    return SimpleNamespace(**{**base, **kw})


def tg_message(chat=500, mid=77, content_type="text", caption=None):
    return SimpleNamespace(chat=SimpleNamespace(id=chat), message_id=mid, content_type=content_type, caption=caption, from_user=SimpleNamespace(first_name="Ann", last_name=None, username=None))


class Base(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.bot = mock.MagicMock()
        for p in (
            mock.patch.object(support, "redis_client", self.redis),
            mock.patch.object(support, "bot", self.bot),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.menukey.bot", self.bot),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
        ):
            p.start()
            self.addCleanup(p.stop)

    def reactions(self):
        return [(c.args[1], c.args[2][0].emoji) for c in self.bot.set_message_reaction.call_args_list]


class ReceiptTests(Base):
    def test_sent_seen_answered(self):
        c = conv()
        support.sent(c, tg_message(mid=1))
        support.sent(c, tg_message(mid=2))
        support.seen(c)
        support.answered(c)
        self.assertEqual(self.reactions(), [(1, "🕊"), (2, "🕊"), (1, "👀"), (2, "👀"), (1, "👌"), (2, "👌")])
        self.bot.set_message_reaction.reset_mock()
        support.answered(c)  # nothing waits any more
        self.assertEqual(self.reactions(), [])

    def test_no_reactions_is_reported(self):
        self.bot.set_message_reaction.side_effect = RuntimeError("REACTION_INVALID")
        self.assertFalse(support.sent(conv(), tg_message()))


class ScreenTests(Base):
    def screen(self, c, lang="en"):
        return support.screen(ui.Ctx(500, lang, user=SimpleNamespace()), c)

    def test_only_the_last_day_with_its_date_in_one_folded_box(self):
        def at(sender, text, day, minute):
            return SimpleNamespace(sender=sender.value, kind="text", text=text, created_at=datetime.datetime(2026, 11, day, 10, minute))

        old_day = [at(Sender.user, "yesterday's question", 16, 0)]
        today = [at(Sender.user, f"hello {i} <x>", 17, i) for i in range(5)] + [at(Sender.admin, "Try again", 17, 30)]
        text = plain(self.screen(conv(messages=old_day + today, unread=0)).text)
        self.assertNotIn("yesterday", text)  # the days before are in the history
        self.assertIn("📅 <b>2026-11-17</b>", text)
        self.assertEqual(text.count("<blockquote expandable>"), 1)
        box = text.split("<blockquote expandable>")[1]
        self.assertTrue(box.split("\n")[1].startswith("hello 0"))  # it opens with the day's first message
        self.assertIn("Try again", box)
        self.assertIn("&lt;x&gt;", text)
        self.assertIn(t(T.sp_answered, "en"), text)
        self.assertIn(t(T.sp_private, "en"), text)

    def test_where_it_stands(self):
        self.assertIn(t(T.sp_empty, "fa"), self.screen(conv(), "fa").text)
        waiting = conv(messages=[message(Sender.user, "hi")], unread=1)
        self.assertIn(t(T.sp_waiting, "en"), self.screen(waiting).text)
        waiting.unread = 0
        self.assertIn(t(T.sp_seen, "en"), self.screen(waiting).text)

    def test_buttons(self):
        data = [b.callback_data for row in self.screen(conv()).markup.keyboard for b in row]
        self.assertEqual(data, ["sq", "dr", "bb"])


class MediaTests(Base):
    def setUp(self):
        super().setUp()
        self.c = conv()
        self.added = []
        admin = SimpleNamespace(id=1, telegram_id=42, lang=None)
        self.awaiting = "support"  # they pressed "Write a Message"
        state = SimpleNamespace(get=lambda k, d=None: self.awaiting if k == "awaiting" else d, update=lambda **kw: None)
        for p in (
            mock.patch.object(ui.Ctx, "state", property(lambda self: state)),
            mock.patch.object(support.free_test, "current_conversation", lambda chat, user: self.c),
            mock.patch.object(support.free_test, "add_message", lambda conv, sender, text: self.added.append((sender, text))),
            mock.patch.object(support, "db"),
            mock.patch.object(support.AdminUser, "by_id", lambda i: admin),
            mock.patch.object(support, "lang_of", lambda *a, **k: "en"),
            mock.patch.object(support.User, "by_uuid", lambda u: None),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_a_photo_sent_without_write_a_message_stays_here(self):
        self.awaiting = None
        self.assertFalse(support.relay_media(ui.Ctx(500, "en", user=SimpleNamespace()), tg_message(content_type="photo")))
        self.bot.copy_message.assert_not_called()

    def test_a_photo_is_copied_to_the_admin_and_kept(self):
        ctx = ui.Ctx(500, "en", user=SimpleNamespace())
        self.assertTrue(support.relay_media(ctx, tg_message(content_type="photo", caption="error screen")))
        copy = self.bot.copy_message.call_args
        self.assertEqual(copy.args, (42, 500, 77))
        self.assertIn("rp:9", json.dumps(copy.kwargs["reply_markup"].to_dict()))
        self.assertIn("<blockquote>error screen</blockquote>", copy.kwargs["caption"])  # one message for the admin
        # the person's only line: it arrived (the writing is over, the menu keyboard is back)
        self.assertEqual([c.args[1] for c in self.bot.send_message.call_args_list], [f"✉️ {t(T.sp_delivered, 'en')}"])
        self.assertEqual(self.added, [(Sender.user, "📷 error screen")])
        self.assertEqual(self.reactions(), [(77, "🕊")])
        self.bot.forward_message.assert_not_called()

    def test_nobody_to_talk_to(self):
        self.c = None
        self.assertFalse(support.relay_media(ui.Ctx(500, "en"), tg_message(content_type="photo")))


class AdminAnswerTests(Base):
    def setUp(self):
        super().setUp()
        self.c = conv()
        self.added = []
        self.state = {"awaiting": "reply", "reply_to": 9}
        self.said = []
        state = SimpleNamespace(get=lambda k: self.state.get(k), update=lambda **kw: self.state.update(kw))
        self.sessions = mock.MagicMock()
        self.sessions.session.get.side_effect = lambda model, i: self.c if i == 9 else None
        for p in (
            mock.patch.object(support, "db", self.sessions),
            mock.patch.object(support.free_test, "add_message", lambda conv, sender, text: self.added.append((sender, text))),
            mock.patch.object(ui.Ctx, "state", property(lambda self: state)),
            mock.patch.object(ui.Ctx, "show"),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.menukey.tell", lambda ctx, text: self.said.append(text)),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.free._conv_lang", lambda c: "fa"),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.topics.thread", lambda *a: None),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_the_answer_comes_from_support_never_from_the_admin(self):
        admin = SimpleNamespace(id=1, name="Secret Admin", username="secret_admin")
        ctx = ui.Ctx(42, "en", admin=admin)
        self.assertTrue(support.admin_media(ctx, tg_message(chat=42, mid=5, content_type="photo", caption="Hi <b>")))
        copy = self.bot.copy_message.call_args
        self.assertEqual(copy.args, (500, 42, 5))
        self.assertIn(t(T.msg_from, "fa"), copy.kwargs["caption"])
        self.assertIn("Hi &lt;b&gt;", copy.kwargs["caption"])  # one message: the media, "Support" and its caption
        self.assertNotIn("Secret", copy.kwargs["caption"])
        self.assertIn("sq", json.dumps(copy.kwargs["reply_markup"].to_dict()))
        self.bot.send_message.assert_not_called()
        self.bot.forward_message.assert_not_called()
        self.assertEqual(self.added, [(Sender.admin, "📷 Hi <b>")])
        self.assertEqual(self.state["awaiting"], None)

    def test_the_reply_prompt_goes_away(self):
        self.state["reply_prompt"] = 31
        support.admin_media(ui.Ctx(42, "en", admin=SimpleNamespace(id=1)), tg_message(chat=42, content_type="photo"))
        self.bot.delete_message.assert_called_once_with(42, 31)

    def test_a_sticker_gets_support_in_a_line_before(self):
        support.admin_media(ui.Ctx(42, "en", admin=SimpleNamespace(id=1)), tg_message(chat=42, content_type="sticker"))
        self.assertIn(t(T.msg_from, "fa"), self.bot.send_message.call_args.args[1])
        self.assertNotIn("caption", self.bot.copy_message.call_args.kwargs)

    def test_not_answering_anyone(self):
        self.state = {"awaiting": None}
        self.assertFalse(support.admin_media(ui.Ctx(42, "en", admin=SimpleNamespace(id=1)), tg_message(chat=42)))

    def test_another_admins_conversation_is_not_answered(self):
        support.admin_media(ui.Ctx(42, "en", admin=SimpleNamespace(id=2)), tg_message(chat=42, content_type="photo"))
        self.bot.copy_message.assert_not_called()


class WritingTests(Base):
    def setUp(self):
        super().setUp()
        self.state = {}
        state = SimpleNamespace(get=lambda k: self.state.get(k), update=lambda **kw: self.state.update(kw))
        p = mock.patch.object(ui.Ctx, "state", property(lambda self: state))
        p.start()
        self.addCleanup(p.stop)
        mock.patch.object(ui.Ctx, "toast").start()
        self.addCleanup(mock.patch.stopall)

    def test_write_opens_a_cancel_keyboard_with_the_hint(self):
        support.ask_message(ui.Ctx(500, "fa", user=SimpleNamespace()), [])
        keys = json.loads(self.bot.send_message.call_args.kwargs["reply_markup"].to_json())
        self.assertEqual(keys["keyboard"], [[{"text": t(T.sp_cancel, "fa")}]])
        self.assertEqual(keys["input_field_placeholder"], t(T.sp_placeholder, "fa"))
        self.assertNotIn("force_reply", keys)
        self.assertEqual(self.state["awaiting"], "support")

    def test_cancel_sends_nothing_and_removes_the_keyboard(self):
        ctx = ui.Ctx(500, "en", user=SimpleNamespace())
        self.assertFalse(support.cancelled(ctx, t(T.sp_cancel, "en")))  # not writing: a plain message
        self.state["awaiting"] = "support"
        self.assertTrue(support.cancelled(ctx, t(T.sp_cancel, "en")))
        keys = json.loads(self.bot.send_message.call_args.kwargs["reply_markup"].to_json())
        self.assertTrue(keys["is_persistent"])  # the person's keyboard is back, Menu included
        self.assertIn({"text": t(T.menu_key, "en"), "style": "primary"}, [b for row in keys["keyboard"] for b in row])  # Menu is blue
        self.assertIsNone(self.state["awaiting"])

    def test_after_the_message_the_keyboard_goes_with_a_line(self):
        ctx = ui.Ctx(500, "en", user=SimpleNamespace())
        support.done_writing(ctx)
        self.bot.send_message.assert_not_called()
        self.state["awaiting"] = "support"
        support.done_writing(ctx)
        self.assertIn(t(T.sp_delivered, "en"), self.bot.send_message.call_args.args[1])


class AdminReplyFlowTests(Base):
    """Reply opens a Cancel key (not a forced reply, which hid the Menu key); every outcome brings Menu back."""

    def setUp(self):
        super().setUp()
        self.state = {}
        self.said = []
        state = SimpleNamespace(get=lambda k: self.state.get(k), update=lambda **kw: self.state.update(kw))
        self.c = conv()
        self.free_bot = mock.MagicMock()
        for p in (
            mock.patch.object(ui.Ctx, "state", property(lambda self: state)),
            mock.patch.object(ui.Ctx, "toast"),
            mock.patch.object(free, "bot", self.free_bot),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.menukey.bot", self.free_bot),
            mock.patch.object(free, "db"),
            mock.patch.object(free, "_mine", lambda ctx, args: self.c),
            mock.patch.object(free, "_conv_lang", lambda c: "en"),
            mock.patch.object(support, "seen"),
            mock.patch.object(support, "typing"),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.menukey.tell", lambda ctx, text: self.said.append(text)),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.free_bot.send_message.return_value = SimpleNamespace(message_id=31)

    def admin_ctx(self):
        return ui.Ctx(42, "en", admin=SimpleNamespace(id=1))

    def test_reply_opens_a_cancel_key(self):
        free.ask_reply(self.admin_ctx(), ["9"])
        keys = json.loads(self.free_bot.send_message.call_args.kwargs["reply_markup"].to_json())
        self.assertEqual(keys["keyboard"], [[{"text": t(T.sp_cancel, "en")}]])
        self.assertNotIn("force_reply", keys)
        self.assertEqual((self.state["awaiting"], self.state["reply_prompt"]), ("reply", 31))

    def test_cancel_sends_nothing_and_brings_menu_back(self):
        self.state.update(reply_to=9, reply_prompt=31)
        with mock.patch.object(free, "deliver") as deliver:
            free.admin_reply(self.admin_ctx(), t(T.sp_cancel, "en"))
        deliver.assert_not_called()
        self.assertEqual(self.said, [f"✖️ {t(T.sp_cancelled, 'en')}"])
        self.free_bot.delete_message.assert_called_once_with(42, 31)

    def test_a_reply_says_sent_and_brings_menu_back(self):
        self.state.update(reply_to=9)
        sessions = mock.MagicMock()
        sessions.session.get.return_value = self.c
        with mock.patch.object(free, "deliver") as deliver, mock.patch.object(free, "db", sessions):
            free.admin_reply(self.admin_ctx(), "Restart the app")
        deliver.assert_called_once_with(self.c, "Restart the app")
        self.assertIn("✅", self.said[-1])


class EndChatTests(Base):
    def setUp(self):
        super().setUp()
        self.state = {"awaiting": "support"}
        state = SimpleNamespace(get=lambda k: self.state.get(k), update=lambda **kw: self.state.update(kw))
        for p in (
            mock.patch.object(ui.Ctx, "state", property(lambda self: state)),
            mock.patch.object(ui.Ctx, "toast"),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.home = mock.patch("hiddifypanel.panel.commercial.telegrambot.handlers.open_home").start()
        self.addCleanup(mock.patch.stopall)

    def test_the_chat_is_cleared_and_the_menu_comes_back(self):
        support.remember(500, 11)
        support.remember(500, SimpleNamespace(message_id=12))
        support.remember(500, None)
        support.sent(conv(), tg_message(mid=13))
        ctx = ui.Ctx(500, "en", user=SimpleNamespace(), message_id=14)
        support.end_chat(ctx, [])
        self.bot.delete_messages.assert_called_once_with(500, [11, 12, 13, 14])
        self.home.assert_called_once_with(ctx, keys=True)  # the keyboard went with a cleared message
        self.assertIsNone(self.state["awaiting"])
        self.assertEqual(self.redis.lrange(support._SESSION.format(500), 0, -1), [])

    def test_old_messages_one_by_one(self):
        support.remember(500, 11)
        support.remember(500, 12)
        self.bot.delete_messages.side_effect = RuntimeError("Bad Request: message can't be deleted")
        self.bot.delete_message.side_effect = [RuntimeError("too old"), None]
        support.end_chat(ui.Ctx(500, "en", user=SimpleNamespace()), [])
        self.assertEqual([c.args for c in self.bot.delete_message.call_args_list], [(500, 11), (500, 12)])
        self.home.assert_called_once()

    def test_answers_carry_answer_and_end(self):
        data = [b["callback_data"] for row in support.answer_buttons("en").to_dict()["inline_keyboard"] for b in row]
        self.assertEqual(data, ["sq", "sx"])


class HistoryTests(Base):
    def setUp(self):
        super().setUp()
        self.convs = []
        model = mock.MagicMock()
        model.query.filter.return_value.all.side_effect = lambda: self.convs
        p = mock.patch.object(support, "Conversation", model)
        p.start()
        self.addCleanup(p.stop)

    def at(self, sender, text, day, hour, kind="text"):
        m = message(sender, text)
        m.created_at = datetime.datetime(2026, 11, day, hour, 0)
        m.kind = kind
        m.id = day * 100 + hour
        return m

    def test_by_date_with_a_header_per_day(self):
        self.convs = [
            conv(messages=[self.at(Sender.user, "second <x>", 17, 9), self.at(Sender.admin, "answer", 17, 10)]),
            conv(messages=[self.at(Sender.user, "first", 15, 8), self.at(Sender.user, "", 15, 9), self.at(Sender.user, "req", 15, 9, kind="request")]),
        ]
        (page,) = support.history_pages(500, "en")
        page = plain(page)
        self.assertLess(page.index("first"), page.index("second"))
        self.assertLess(page.index("second"), page.index("answer"))
        self.assertEqual(page.count("📅"), 2)
        self.assertEqual(page.count("<blockquote expandable>"), 2)  # each day one folded box, like the admin's
        self.assertTrue(page.split("📅 <b>2026-11-17</b>\n<blockquote expandable>")[1].split("\n")[1].startswith("second"))
        self.assertIn("&lt;x&gt;", page)
        self.assertNotIn("req", page)

    def test_newest_page_first_with_older_and_newer(self):
        self.convs = [conv(messages=[self.at(Sender.user, f"m{i} " + "x" * 400, 1 + i // 3, 1 + i % 3) for i in range(30)])]
        pages = support.history_pages(500, "en")
        self.assertGreater(len(pages), 2)
        self.assertTrue(all(len(p) < 4000 for p in pages))
        ctx = ui.Ctx(500, "en", user=SimpleNamespace())
        newest = support.history_screen(ctx, 0)
        self.assertIn("m29", newest.text)
        data = [b.callback_data for row in newest.markup.keyboard for b in row]
        self.assertEqual(data, ["hs:1", "sp", "bb"])
        middle = [b.callback_data for row in support.history_screen(ctx, 1).markup.keyboard for b in row]
        self.assertEqual(middle, ["hs:2", "hs:0", "sp", "bb"])
        oldest = support.history_screen(ctx, 99)
        self.assertIn("m0 ", oldest.text)
        self.assertTrue(all(len(p) for p in pages))
        self.assertTrue(pages[1].lstrip().startswith("📅"))  # each page starts with its day

    def test_nothing_yet(self):
        screen = support.history_screen(ui.Ctx(500, "fa", user=SimpleNamespace()), 0)
        self.assertIn(t(T.hist_empty, "fa"), screen.text)


class TextAnswerTests(unittest.TestCase):
    def test_the_text_answer_names_support_only(self):
        fake_bot = mock.MagicMock()
        c = conv()
        with (
            mock.patch.object(free, "bot", fake_bot),
            mock.patch.object(free, "_conv_lang", lambda c: "en"),
            mock.patch.object(free.free_test, "add_message", lambda *a: None),
            mock.patch.object(free, "db"),
            mock.patch.object(support, "answered") as answered,
            mock.patch.object(support, "remember"),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.topics.thread", lambda *a: None),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
        ):
            free.deliver(c, "Restart the app")
        text = fake_bot.send_message.call_args.args[1]
        self.assertIn("sx", json.dumps(fake_bot.send_message.call_args.kwargs["reply_markup"].to_dict()))  # End Chat
        self.assertIn(t(T.msg_from, "en"), text)
        self.assertIn("Restart the app", text)
        answered.assert_called_once_with(c)



class ReadLaterTests(unittest.TestCase):
    def test_the_notice_goes_the_menu_comes_and_it_stays_unread(self):
        from hiddifypanel.panel.commercial.telegrambot import handlers, nav

        conversation = conv(unread=2)
        with mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False):
            markup = support.admin_buttons(conversation, "en")
        data = [b.callback_data for row in markup.keyboard for b in row]
        self.assertIn("rl:9", data)
        ctx = ui.Ctx(42, "en", admin=SimpleNamespace(id=1), message_id=77, call_id="c")
        with (
            mock.patch.object(handlers, "_delete") as delete,
            mock.patch.object(handlers, "open_home") as home,
            mock.patch.object(nav, "reset"),
            mock.patch.object(ui.Ctx, "toast"),
        ):
            support.read_later(ctx, ["9"])
        delete.assert_called_once_with(42, 77)
        home.assert_called_once()
        self.assertEqual(conversation.unread, 2)  # still to be read, in Support History



class HowToWriteTests(unittest.TestCase):
    def test_support_and_back_and_back_clears_both_lines(self):
        import time as _time

        from telebot import apihelper

        from hiddifypanel.panel.commercial.restapi.v1.tgbot import bot as real_bot
        from hiddifypanel.panel.commercial.telegrambot import handlers

        ctx = ui.Ctx(500, "en", user=SimpleNamespace())
        fake = mock.MagicMock()
        with mock.patch.object(handlers, "bot", fake), mock.patch.object(handlers.free_test, "current_conversation", lambda chat, user: object()), mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False):
            handlers._how_to_write(ctx, 61)
        data = [b.callback_data for row in fake.send_message.call_args.kwargs["reply_markup"].keyboard for b in row]
        self.assertEqual(data, ["sp:h:61", "x:61"])
        deleted = []

        def request(token, method_name, method="get", params=None, files=None):
            if method_name == "deleteMessage":
                deleted.append(int(params["message_id"]))
            return True

        update = {"update_id": int(_time.time() * 1000) % 10**9, "callback_query": {"id": "q", "from": {"id": 500, "is_bot": False, "first_name": "A"}, "chat_instance": "c", "data": "x:61", "message": {"message_id": 62, "date": 0, "chat": {"id": 500, "type": "private"}, "text": "how"}}}
        with mock.patch.object(handlers, "context", lambda *a, **k: ui.Ctx(500, "en", user=SimpleNamespace(), message_id=62, call_id="q")), mock.patch("telebot.apihelper._make_request", request), mock.patch("hiddifypanel.panel.commercial.telegrambot.usernames.remember"):
            real_bot.process_new_updates([__import__("telebot").types.Update.de_json(update)])
        self.assertEqual(sorted(deleted), [61, 62])  # the line and what was typed


if __name__ == "__main__":
    unittest.main()
