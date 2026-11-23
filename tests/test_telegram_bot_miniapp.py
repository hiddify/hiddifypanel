"""Advanced mode: the Mini App page (biometric lock, QR scan, emoji status) and the config file."""

import json
import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import cfgfile, miniapp, ui
from hiddifypanel.panel.commercial.telegrambot.texts import T, t

ADV = "hiddifypanel.panel.commercial.telegrambot.advanced.is_on"


class FakeRedis:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, **_kw):
        self.values[key] = value
        return True

    def expire(self, key, _seconds):
        return key in self.values

    def delete(self, *keys):
        for k in keys:
            self.values.pop(k, None)

    def pipeline(self):
        redis, ops = self, []

        class Pipe:
            def get(self, key):
                ops.append(("get", key))

            def delete(self, key):
                ops.append(("del", key))

            def execute(self):
                out = []
                for op, key in ops:
                    out.append(redis.get(key) if op == "get" else redis.delete(key))
                return out

        return Pipe()


class Base(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.shown, self.sent, self.prefs = [], [], {}
        for p in (
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
            mock.patch(ADV, lambda: True),
            mock.patch.object(miniapp, "redis_client", self.redis),
            mock.patch.object(miniapp, "page_url", lambda kind, token, **e: f"https://panel.example.com/app/act/?do={kind}&t={token}" + "".join(f"&{k}={v}" for k, v in e.items())),
            mock.patch.object(miniapp.BotPref, "get", lambda chat, key, default="": self.prefs.get((chat, key), default)),
            mock.patch.object(miniapp.BotPref, "put", lambda chat, key, value: self.prefs.__setitem__((chat, key), value)),
            mock.patch.object(ui.Ctx, "toast", lambda s, text=None, alert=False: None),
            mock.patch.object(ui.Ctx, "show", lambda s, screen: self.shown.append(screen)),
            mock.patch.object(miniapp, "with_retry", lambda call, attempts=3: call()),
            mock.patch.object(miniapp, "bot", SimpleNamespace(send_message=lambda chat, text, reply_markup=None, **k: self.sent.append((chat, text, reply_markup)))),
            mock.patch("hiddifypanel.database.db.session", mock.MagicMock()),
            mock.patch.object(miniapp, "telegram_user_id", None, create=True),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.ctx = ui.Ctx(5, "en", admin=SimpleNamespace(id=1, name="Ann", mode="super_admin", telegram_id=5))

    def signed(self, tg_id):
        return mock.patch("hiddifypanel.panel.commercial.telegrambot.webapp.telegram_user_id", lambda data, token: tg_id)


class LockTests(Base):
    def test_unlocked_action_passes(self):
        self.assertFalse(miniapp.needs_unlock(self.ctx, "del", "ua:3:del:1"))

    def answer_lock(self, body):
        url = self.shown[-1].markup.keyboard[0][0].web_app.url
        token = url.split("t=")[1].split("&")[0]
        with self.signed(5):
            return miniapp.answer("data", {"t": token, "ok": True, **body}, "tok")[1], url

    def test_the_first_confirm_puts_a_key_in_the_phone_then_it_is_asked_back(self):
        miniapp.set_locked(5, {"del"})
        self.assertTrue(miniapp.needs_unlock(self.ctx, "del", "ua:3:del:1"))
        code, url = self.answer_lock({"secret": "a" * 64})  # the first time: the key goes into the phone
        self.assertEqual(code, 200)
        self.assertIn("m=set", url)
        self.assertEqual(self.sent[-1][2].keyboard[0][0].callback_data, "ua:3:del:1")
        self.assertFalse(miniapp.needs_unlock(self.ctx, "del", "ua:3:del:1"))  # the press after the biometrics, once
        self.assertTrue(miniapp.needs_unlock(self.ctx, "del", "ua:3:del:1"))
        code, url = self.answer_lock({"token": "b" * 64})  # a page that only says "ok", with no key from the phone
        self.assertEqual(code, 403)
        self.assertIn("m=use", url)
        self.assertTrue(miniapp.needs_unlock(self.ctx, "del", "ua:3:del:1"))
        self.assertEqual(self.answer_lock({"token": "a" * 64})[0], 200)  # the phone's key: through

    def test_token_is_for_its_own_chat_and_once(self):
        token = miniapp.new_token(5, "lock", data="ap:go", action="apply", lang="en", set=True)
        with self.signed(6):
            self.assertEqual(miniapp.answer("data", {"t": token, "ok": True, "secret": "c" * 64}, "tok")[1], 403)
        self.assertEqual(self.sent, [])
        with self.signed(5):  # a foreign try does not burn it: its own chat still can, once
            self.assertEqual(miniapp.answer("data", {"t": token, "ok": True, "secret": "c" * 64}, "tok")[1], 200)
            self.assertEqual(miniapp.answer("data", {"t": token, "ok": True, "secret": "c" * 64}, "tok")[1], 403)
        self.assertEqual(len(self.sent), 1)

    def test_an_agents_token_after_the_switch_is_off(self):
        from hiddifypanel.panel.commercial.telegrambot import resellers

        token = miniapp.new_token(5, "lock", data="ap:go", action="apply", lang="en")
        self.redis.values[miniapp._PENDING_KEY.format(token)] = json.dumps({"chat": 5, "kind": "lock", "bot": 77, "data": "ap:go"})
        with mock.patch.object(resellers, "find", lambda i: resellers.Managed(77, "agent", 4, "b")), mock.patch.object(resellers, "allowed", lambda: False), self.signed(5):
            self.assertEqual(miniapp.answer("data", {"t": token, "ok": True}, "tok")[1], 403)

    def test_bad_signature(self):
        token = miniapp.new_token(5, "lock", data="ap:go")
        with self.signed(None):
            self.assertEqual(miniapp.answer("forged", {"t": token, "ok": True}, "tok")[1], 403)

    def test_changing_a_lock_asks_the_biometrics_too(self):
        miniapp.show_lock(self.ctx, ["apply", "1"])
        self.assertEqual(miniapp.locked(5), set())  # not yet: the confirmation first
        self.assertEqual(self.answer_lock({"secret": "d" * 64})[0], 200)
        miniapp.show_lock(self.ctx, ["apply", "1"])  # the press after the biometrics
        self.assertEqual(miniapp.locked(5), {"apply"})
        miniapp.show_lock(self.ctx, ["apply", "0"])  # taking it off asks too
        self.assertEqual(miniapp.locked(5), {"apply"})
        self.assertEqual(self.answer_lock({"token": "d" * 64})[0], 200)
        miniapp.show_lock(self.ctx, ["apply", "0"])
        self.assertEqual(miniapp.locked(5), set())
        miniapp.show_lock(self.ctx, ["root", "1"])
        self.assertEqual(miniapp.locked(5), set())

    def test_the_panel_link_again_starts_the_locks_over(self):
        miniapp.set_locked(5, {"del"})
        self.prefs[(5, miniapp.LOCK_KEY_PREF)] = "x"
        miniapp.reset_locks(5)
        self.assertEqual(miniapp.locked(5), set())
        self.assertEqual(miniapp._lock_key(5), "")


class ManagedBotTests(Base):
    def test_an_agents_bot_page_is_checked_with_that_bots_token(self):
        from hiddifypanel.panel.commercial.telegrambot import resellers as _r

        allowed = mock.patch.object(_r, "allowed", lambda: True)
        allowed.start()
        self.addCleanup(allowed.stop)
        from hiddifypanel.panel.commercial.restapi.v1.tgbot import managed_bot
        from hiddifypanel.panel.commercial.telegrambot import resellers

        m = resellers.Managed(77, "agent", 4, "shop_bot")
        mark = managed_bot.set(m)
        try:
            token = miniapp.new_token(5, "lock", data="ap:go", action="apply", lang="en", set=True)
        finally:
            managed_bot.reset(mark)
        seen = []
        with mock.patch.object(resellers, "find", lambda i: m if i == 77 else None), mock.patch(
            "hiddifypanel.panel.commercial.telegrambot.webapp.telegram_user_id", lambda data, key: seen.append(key) or 5
        ):
            self.assertEqual(miniapp.answer("data", {"t": token, "ok": True, "secret": "e" * 64}, "panel")[1], 200)
        self.assertEqual(seen, ["agent"])

    def test_a_redrawn_screen_reuses_its_token(self):
        a = miniapp.lasting_token(5, "scan", lang="en")
        self.assertEqual(miniapp.lasting_token(5, "scan", lang="en"), a)
        miniapp.take_token(a)
        self.assertNotEqual(miniapp.lasting_token(5, "scan", lang="en"), a)


class ScanTests(Base):
    def test_only_their_own_users(self):
        uid = "6f1c2b8e-1111-4a2b-9c3d-0123456789ab"
        admin = SimpleNamespace(id=1, mode="super_admin")
        user = SimpleNamespace(id=9, uuid=uid)
        admin_model = mock.MagicMock(**{"query.filter.return_value.first.return_value": admin})
        user_model = mock.MagicMock(**{"query.filter.return_value.first.return_value": user})
        with mock.patch("hiddifypanel.models.AdminUser", admin_model), mock.patch("hiddifypanel.models.User", user_model), mock.patch(
            "hiddifypanel.panel.commercial.telegrambot.accounts.get_visible", lambda a, i: None
        ):
            miniapp._scanned({"chat": 5, "lang": "en"}, f"https://x/p/{uid}/#u")
        self.assertIn(t(T.qs_not_found, "en"), self.sent[-1][1])


class ConfigFileTests(unittest.TestCase):
    def test_formats_and_ip_check(self):
        self.assertEqual(set(cfgfile.FORMATS), {"singbox", "clash", "links"})
        self.assertFalse(cfgfile._is_ip("panel.example.com"))

    def test_hidden_while_advanced_is_off(self):
        with mock.patch(ADV, lambda: False):
            ctx = ui.Ctx(5, "en", user=SimpleNamespace(id=1))
            self.assertEqual(cfgfile.home_rows(ctx), [])


if __name__ == "__main__":
    unittest.main()
