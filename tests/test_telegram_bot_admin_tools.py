"""The admin's tools on their keyboard: many users at once with numbered names, silent notifications, the bandwidth
chart, the message to all users, and the chats."""

import datetime
import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import admin, bandwidth, broadcast, silence, ui
from hiddifypanel.panel.commercial.telegrambot.texts import T, t



def plain(text):
    """The text as an older app shows it: a smart date's own text."""
    import re

    return re.sub(r"<tg-time [^>]*>(.*?)</tg-time>", r"\1", text)

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
        for p in (
            mock.patch.object(ui.Ctx, "state", property(lambda _s: self.state)),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.ctx = ui.Ctx(5, "en", admin=SimpleNamespace(id=1, name="Ann", mode="admin"))

    def data(self, screen):
        return [b.callback_data for row in screen.markup.keyboard for b in row]


class NewUsersTests(Base):
    def test_first_one_or_how_many(self):
        self.assertEqual(self.data(admin.new_screen(self.ctx, 0, 0, 0)), ["nw:0:0:1", "nc", "bb"])

    def test_many_ask_their_name_after_the_days(self):
        screen = admin.new_screen(self.ctx, 10, 30, 12)
        self.assertEqual(self.state.get("awaiting"), "new_name")
        self.assertIn("Hiddify-01, Hiddify-02 … Hiddify-12", screen.text)
        self.state.update(new_name="Shop")
        self.assertIn("ng:10:30:12", self.data(admin.new_screen(self.ctx, 10, 30, 12)))

    def test_typed_counts(self):
        self.assertEqual(admin.parse_count("10"), 10)
        self.assertEqual(admin.parse_count(" ۱۵ "), 15)
        self.assertIsNone(admin.parse_count("0"))
        self.assertIsNone(admin.parse_count(str(admin.MAX_BATCH + 1)))
        self.assertIsNone(admin.parse_count("ten"))

    def test_names_get_two_digit_numbers(self):
        self.assertEqual(admin.names_preview("Hiddify", 1), "Hiddify")
        self.assertEqual(admin.names_preview("Hiddify", 100), "Hiddify-001, Hiddify-002 … Hiddify-100")
        from hiddifypanel.panel.commercial.telegrambot import accounts

        made = []
        with mock.patch.object(accounts, "User", lambda **kw: SimpleNamespace(**kw)), mock.patch.object(accounts, "db"), mock.patch.object(accounts, "apply", lambda users: made.extend(users)):
            accounts.create(SimpleNamespace(id=1), gb=1, days=1, count=3, name="Hiddify")
        self.assertEqual([u.name for u in made], ["Hiddify-01", "Hiddify-02", "Hiddify-03"])


class SilenceTests(unittest.TestCase):
    def test_sends_to_a_silent_chat_go_without_a_sound(self):
        from telebot import apihelper

        got = []
        with mock.patch.object(apihelper, "_make_request", lambda token, method_name, method="get", params=None, files=None: got.append((method_name, params))):
            silence.install()
            with mock.patch.object(silence, "is_silent", lambda chat: chat == 7):
                apihelper._make_request("t", "sendMessage", "post", {"chat_id": 7, "text": "a"})
                apihelper._make_request("t", "sendPhoto", "post", {"chat_id": 8})
                apihelper._make_request("t", "sendChatAction", "post", {"chat_id": 7})
                apihelper._make_request("t", "editMessageText", "post", {"chat_id": 7})
        self.assertEqual([p.get("disable_notification") for _m, p in got], [True, None, None, None])


class BandwidthTests(unittest.TestCase):
    def series(self, period, values, nodes=None):
        start = datetime.datetime(2026, 11, 1)
        unit = datetime.timedelta(hours=1) if period == "h24" else datetime.timedelta(days=1)
        slots = [bandwidth.Slot(start + unit * i, v) for i, v in enumerate(values)]
        return bandwidth.Series(period, slots, previous=100 * 1024**3, nodes=nodes or {0: ""})

    def test_a_sharp_picture_for_each_period(self):
        for period, (n, _unit) in bandwidth.PERIODS.items():
            values = [{0: (i % 5) * 1024**3, 3: i * 1024**2} for i in range(n)]
            png = bandwidth.render(self.series(period, values, {0: "main", 3: "نود"}))
            self.assertTrue(png[1:4] == b"PNG")
            from PIL import Image
            import io

            self.assertEqual(Image.open(io.BytesIO(png)).size, (bandwidth.W, bandwidth.H))

    def test_empty_and_the_numbers_in_the_caption(self):
        ctx = ui.Ctx(1, "en")
        empty = bandwidth.caption(ctx, self.series("h24", [{0: 0}] * 24))
        self.assertIn(t(T.bw_empty, "en"), empty)
        self.assertIn(t(T.bw_hours_note, "en"), empty)
        full = bandwidth.caption(ctx, self.series("d7", [{0: 30 * 1024**3}] * 7))
        self.assertIn("+110%", full)  # 210 GB against 100 GB before
        self.assertEqual(bandwidth.short(1536 * 1024**2), "1.5 GB")

    def test_the_period_tabs(self):
        ctx = ui.Ctx(1, "en")
        with mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False):
            pick = [b.callback_data for row in bandwidth.pick_screen(ctx).markup.keyboard for b in row]
            tabs = [b.text for row in bandwidth._markup(ctx, "d15").keyboard for b in row]
        self.assertEqual(pick, ["bw:h24", "bw:d7", "bw:d15", "bw:d30", "bb"])
        self.assertIn("✓ " + t(T.bw_d15, "en"), tabs)


class BroadcastTests(Base):
    def test_written_then_confirmed_then_cancelled(self):
        self.state.update(awaiting=broadcast.AWAITING)
        message = SimpleNamespace(text="Hello all", message_id=44)
        shown = []
        with mock.patch.object(broadcast, "targets", lambda a: [10, 11]), mock.patch("hiddifypanel.panel.commercial.telegrambot.menukey.tell"), mock.patch.object(ui.Ctx, "show", lambda _s, screen: shown.append(screen)):
            self.assertTrue(broadcast.take(self.ctx, message))
            self.assertFalse(broadcast.take(self.ctx, message))  # no longer writing one
        self.assertEqual(self.state.get("bc_message"), 44)
        self.assertIn("bc:go", self.data(shown[0]))
        self.assertIn("2", shown[0].text)

    def test_to_all_asks_for_the_message(self):
        from hiddifypanel.panel.commercial.telegrambot import menukey

        shown = []
        fake_bot = mock.MagicMock()
        fake_bot.send_message.return_value = SimpleNamespace(message_id=70)
        with (
            mock.patch.object(broadcast, "targets", lambda a: [10, 11]),
            mock.patch.object(menukey, "bot", fake_bot),
            mock.patch.object(ui.Ctx, "show", lambda _s, screen: shown.append(screen)),
            mock.patch.object(ui.Ctx, "toast"),
        ):
            broadcast.show_broadcast(self.ctx, ["all"])
        self.assertEqual(self.state.get("awaiting"), broadcast.AWAITING)
        self.assertEqual(self.state.get("cancel_msg"), 70)
        self.assertIn("bb", self.data(shown[-1]))

    def test_first_all_or_one(self):
        self.assertEqual(self.data(broadcast.choose_screen(self.ctx)), ["bc:all", "bc:one", "bb"])

    def test_one_user_by_name_then_the_message_goes_only_to_them(self):
        from hiddifypanel.panel.commercial.telegrambot import accounts

        ann = SimpleNamespace(id=7, name="Ann", telegram_id=555)
        bob = SimpleNamespace(id=8, name="Annabel", telegram_id=None)
        shown = []
        with (
            mock.patch.object(accounts, "search_page", lambda admin, q, page, size: accounts.Page([ann, bob], 2, 0, 1)),
            mock.patch.object(accounts, "get_visible", lambda admin, uid: {7: ann, 8: bob}.get(uid)),
            mock.patch.object(broadcast, "bot"),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.menukey.bot"),
            mock.patch("hiddifypanel.panel.commercial.telegrambot.menukey.tell"),
            mock.patch.object(ui.Ctx, "show", lambda _s, screen: shown.append(screen)),
            mock.patch.object(ui.Ctx, "toast"),
        ):
            self.state.update(awaiting=broadcast.AWAITING_USER)
            self.assertTrue(broadcast.take(self.ctx, SimpleNamespace(text="ann", message_id=1)))  # the exact name wins
            self.assertEqual((self.state.get("awaiting"), self.state.get("bc_target")), (broadcast.AWAITING, 7))
            self.assertTrue(broadcast.take(self.ctx, SimpleNamespace(text="Hello Ann", message_id=2)))
            self.assertEqual(broadcast._chats(self.ctx), [555])
            self.assertIn("bc:go", self.data(shown[-1]))
            self.assertIn("Ann", shown[-1].text)
            broadcast._pick_user(self.ctx, 8)  # no bot: asked again
            self.assertEqual(self.state.get("awaiting"), broadcast.AWAITING_USER)
            self.assertIn(t(T.bc_one_no_bot, "en", name="Annabel"), shown[-1].text)

    def test_back_while_writing_brings_the_menu_back_and_goes_one_step(self):
        from hiddifypanel.panel.commercial.telegrambot import menukey, nav
        from hiddifypanel.panel.commercial.telegrambot.ui import Cb

        nav.reset(self.ctx, Cb.broadcast, [])  # the Send Message key
        nav.push(self.ctx, Cb.broadcast, ["all"])
        self.assertEqual(self.state.get("nav"), [["bc", []], ["bc", ["all"]]])
        fake_bot = mock.MagicMock()
        fake_bot.send_message.side_effect = [SimpleNamespace(message_id=90), SimpleNamespace(message_id=91)]
        with mock.patch.object(menukey, "bot", fake_bot):
            menukey.prompt(self.ctx, "write the name", "hint")
            menukey.prompt(self.ctx, "write the message", "hint")  # the next line takes the place of the first
        fake_bot.delete_message.assert_called_once_with(5, 90)
        self.assertEqual(self.state.get("cancel_msg"), 91)
        self.state.update(awaiting=broadcast.AWAITING)
        with mock.patch.object(menukey, "ensure") as ensure:
            self.assertTrue(menukey.restore(self.ctx))
            self.assertFalse(menukey.restore(self.ctx))  # once
        ensure.assert_called_once()
        self.assertTrue(ensure.call_args.kwargs["force"])
        self.assertIsNone(self.state.get("awaiting"))
        shown = []
        with mock.patch.object(ui.Ctx, "show", lambda _s, screen: shown.append(screen)), mock.patch.object(ui.Ctx, "toast"):
            nav.go_back(self.ctx, [])
        self.assertIn("bc:all", self.data(shown[0]))  # the choice again, not the start

    def test_found_by_telegram_username_or_id(self):
        from hiddifypanel.panel.commercial.telegrambot import accounts, usernames

        tried = []
        with (
            mock.patch.object(usernames, "chats_of", lambda name: [777] if usernames.normal(name) == "ann_tg" else []),
            mock.patch.object(broadcast, "_chat_target", lambda ctx, chats: tried.append(chats) or bool(chats)),
            mock.patch.object(broadcast, "_ask_user") as ask,
            mock.patch.object(accounts, "search_page", lambda *a: accounts.Page([], 0, 0, 1)),
        ):
            broadcast._find_user(self.ctx, "@Ann_TG")
            broadcast._find_user(self.ctx, "123456789")
            broadcast._find_user(self.ctx, "@nobody")
            broadcast._find_user(self.ctx, "ann_tg")  # a username typed without @, after the panel names
        self.assertEqual(tried, [[777], [123456789], [], [777]])
        ask.assert_called_once()  # only @nobody is asked again
        self.assertIn("@nobody", ask.call_args.args[1])

    def test_someone_who_only_wrote_to_the_admin_gets_it_too(self):
        from hiddifypanel.panel.commercial.telegrambot import menukey

        query = mock.MagicMock()
        query.filter.return_value.first.return_value = None  # not one of the admin's users
        self.ctx.admin.recursive_users_query = lambda: query
        conv = SimpleNamespace(name="Sara", username="sara")
        shown = []
        fake_conv = mock.MagicMock()
        fake_conv.query.filter.return_value.first.return_value = conv
        with (
            mock.patch("hiddifypanel.models.message.Conversation", fake_conv),
            mock.patch.object(menukey, "bot"),
            mock.patch.object(ui.Ctx, "show", lambda _s, screen: shown.append(screen)),
            mock.patch.object(ui.Ctx, "toast"),
        ):
            self.assertTrue(broadcast._chat_target(self.ctx, [888]))
        self.assertEqual(broadcast._chats(self.ctx), [888])
        self.assertIn("Sara", shown[-1].text)
        self.assertEqual(self.state.get("awaiting"), broadcast.AWAITING)

    def test_cancel_sends_nothing(self):
        self.state.update(awaiting=broadcast.AWAITING)
        with mock.patch("hiddifypanel.panel.commercial.telegrambot.menukey.tell") as tell:
            self.assertTrue(broadcast.take(self.ctx, SimpleNamespace(text=t(T.sp_cancel, "en"), message_id=1)))
        self.assertIsNone(self.state.get("bc_message"))
        tell.assert_called_once()


class ConversationTests(unittest.TestCase):
    @mock.patch("hiddifypanel.panel.commercial.telegrambot.advanced.is_on", lambda: True)
    def test_each_day_is_one_folded_box_starting_with_its_first_message(self):
        from hiddifypanel.panel.commercial.telegrambot import chats

        d1, d2 = datetime.datetime(2026, 11, 16, 9, 0), datetime.datetime(2026, 11, 17, 9, 21)
        msgs = [
            SimpleNamespace(sender="user", kind="text", text="first of day one", created_at=d1),
            SimpleNamespace(sender="admin", kind="text", text="answer", created_at=d1 + datetime.timedelta(minutes=5)),
            SimpleNamespace(sender="user", kind="text", text="first of day two", created_at=d2),
            SimpleNamespace(sender="user", kind="request", text="1|1", created_at=d2 + datetime.timedelta(hours=1)),
        ]
        conv = SimpleNamespace(name="Sara", messages=msgs)
        (page,) = chats.conversation_pages(conv, "en", lambda key, **kw: t(key, "en", **kw))
        self.assertIn('<tg-time unix="', page)  # dates and times each person sees in their own zone
        page = plain(page)
        self.assertEqual(page.count("<blockquote expandable>"), 2)
        day_two = page.split("📅 <b>2026-11-17</b>\n<blockquote expandable>")[1]
        self.assertTrue(day_two.split("\n")[1].startswith("first of day two"))  # the box opens with the day's first message
        self.assertIn(t(T.ch_k_request, "en"), day_two)

    def test_a_long_day_goes_on_over_pages_with_its_date(self):
        from hiddifypanel.panel.commercial.telegrambot import chats

        day = datetime.datetime(2026, 11, 17, 9, 0)
        msgs = [SimpleNamespace(sender="user", kind="text", text="x" * 500, created_at=day) for _ in range(20)]
        pages = chats.conversation_pages(SimpleNamespace(name="A", messages=msgs), "en", lambda key, **kw: t(key, "en", **kw))
        self.assertGreater(len(pages), 1)
        self.assertTrue(all(plain(p).startswith("📅 <b>2026-11-17</b>") and len(p) < 4000 for p in pages))


class MainAppTests(Base):
    def test_the_owner_sees_the_link_for_botfather(self):
        from hiddifypanel.panel.commercial.telegrambot import accounts, admin_settings

        from hiddifypanel.panel.commercial.telegrambot import openbutton

        with mock.patch.object(admin_settings.silence, "is_silent", lambda chat: False), mock.patch.object(accounts, "panel_app_url", lambda: "https://panel.example.com/p/api/v1/tgbot/app/"), mock.patch.object(
            openbutton, "has_open_button", lambda fresh=False: False
        ):
            self.ctx.admin = SimpleNamespace(id=1, mode="super_admin")
            owner = admin_settings.settings_screen(self.ctx)
            self.ctx.admin = SimpleNamespace(id=2, mode="agent")
            agent = admin_settings.settings_screen(self.ctx)
            steps = openbutton.help_screen(ui.Ctx(5, "en", admin=SimpleNamespace(id=1, mode="super_admin"))).text
        self.assertIn(t(T.oa_missing, "en"), owner.text)  # the state, and a key to the steps
        self.assertIn("oh", self.data(owner))
        self.assertNotIn("oh", self.data(agent))
        self.assertIn("<code>https://panel.example.com/p/api/v1/tgbot/app/</code>", steps)


class AdvancedTests(Base):
    def test_off_the_bot_is_as_it_was(self):
        import datetime

        from hiddifypanel.panel.commercial.telegrambot import admin, advanced

        with mock.patch.object(advanced, "is_on", lambda: False):
            self.assertEqual(ui.tg_time(datetime.datetime(2026, 11, 18, 9, 30), "t", "09:30"), "09:30")  # plain text
            middle = admin._pager(ui.Cb.users, ["a"], 1, 3, ["u"])[1].to_dict()
            self.assertEqual(middle.get("callback_data"), "ul:a:1:u")  # the page number refreshes, as before
            self.assertIsNone(ui.off_btn("x"))  # an only-greyed button is left out
            self.assertEqual(len(ui.keyboard([ui.off_btn("x")], [ui.btn("y", ui.Cb.home)]).keyboard), 1)

    def test_only_the_owner_sees_and_turns_the_switches(self):
        from hiddifypanel.panel.commercial.telegrambot import admin_settings, advanced

        saved = {}
        with (
            mock.patch.object(admin_settings.silence, "is_silent", lambda chat: False),
            mock.patch.object(advanced, "_read", lambda key: saved.get(key, False)),
            mock.patch.object(advanced, "set_switch", lambda key, on: saved.__setitem__(key, on)),
            mock.patch.object(admin_settings, "db"),
            mock.patch.object(ui.Ctx, "show"),
            mock.patch.object(ui.Ctx, "toast") as toast,
            mock.patch("hiddifypanel.panel.commercial.telegrambot.accounts.panel_app_url", lambda: None),
        ):
            self.ctx.admin = SimpleNamespace(id=1, mode="super_admin")
            owner = self.data(admin_settings.settings_screen(self.ctx))
            self.assertIn("av:advanced:1", owner)
            self.assertNotIn("av:adv_resellers:1", owner)  # inside Advanced only
            admin_settings.set_advanced(self.ctx, ["advanced", "1"])
            owner_on = self.data(admin_settings.settings_screen(self.ctx))
            self.assertIn("av:adv_resellers:1", owner_on)
            self.assertIn("av:adv_guard:1", owner_on)
            self.assertFalse(advanced.feature(advanced.RESELLER_BOTS))  # off by default
            self.ctx.admin = SimpleNamespace(id=2, mode="agent")
            self.assertFalse([d for d in self.data(admin_settings.settings_screen(self.ctx)) if d.startswith("av:")])
            admin_settings.set_advanced(self.ctx, ["advanced", "0"])
            self.assertTrue(saved["advanced"])  # an agent cannot turn it off
            toast.assert_called_with(t(T.not_allowed, "en"), alert=True)


class BackupMessageTests(unittest.TestCase):
    def test_the_file_is_named_by_its_day_and_time(self):
        from hiddifypanel.panel.commercial.telegrambot import backup_msg

        when = backup_msg.when_of("/opt/hiddify-manager/hiddify-panel/backup/2026_11_17__18_00_01.json")
        self.assertEqual(backup_msg.file_name(when), "2026.11.17_18.00.json")

    def test_the_links_by_colour(self):
        import json

        from hiddifypanel.panel.commercial.telegrambot import backup_msg

        found = [("secure", "panel.example.com", "https://panel.example.com/p/"), ("cdn", "cdn.example.com", "https://cdn.example.com/p/"), ("insecure", "192.0.2.1", "http://192.0.2.1/p/")]
        with mock.patch.object(backup_msg, "links", lambda owner: found), mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False):
            rows = json.loads(backup_msg.markup("en", None).to_json())["inline_keyboard"]
            plain = json.loads(backup_msg.markup("en", None, plain_http=False).to_json())["inline_keyboard"]
        styles = [r[0].get("style") for r in rows]
        self.assertEqual(styles, ["success", "success", "danger"])  # secure and CDN green, not secure red
        self.assertEqual([r[0]["text"] for r in rows], ["🔒 Secure", "🔐 Secure", "⚠️ Not Secure IPv4"])
        self.assertFalse(any("example.com" in r[0]["text"] for r in rows))  # never the address itself
        self.assertEqual(len(plain), 2)  # without the plain http one

    def test_the_labels_by_kind(self):
        from hiddifypanel.panel.commercial.telegrambot import backup_msg

        ip = ".".join(["198", "51", "100", "7"])
        self.assertEqual(backup_msg.button_label("secure", ip), "🔒 Secure IPv4")
        self.assertEqual(backup_msg.button_label("secure", "panel.example.com"), "🔒 Secure")
        self.assertEqual(backup_msg.button_label("cdn", "cdn.example.com"), "🔐 Secure")
        self.assertEqual(backup_msg.button_label("insecure", ip), "⚠️ Not Secure IPv4")
        self.assertEqual(backup_msg.button_label("insecure", "panel.example.com"), "⚠️ Not Secure")


if __name__ == "__main__":
    unittest.main()
