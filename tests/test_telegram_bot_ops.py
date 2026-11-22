"""Advanced mode: Apply, the config test and the scanner's Mini App page."""

import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import ops, ui, webapp
from hiddifypanel.panel.commercial.telegrambot.texts import T, t

ADV = "hiddifypanel.panel.commercial.telegrambot.advanced.is_on"


class Base(unittest.TestCase):
    def setUp(self):
        self.shown, self.toasts = [], []
        for p in (
            mock.patch("hiddifypanel.panel.commercial.telegrambot.icons.enabled", lambda: False),
            mock.patch(ADV, lambda: True),
            mock.patch.object(ui.Ctx, "toast", lambda s, text=None, alert=False: self.toasts.append(text)),
            mock.patch.object(ui.Ctx, "show", lambda s, screen: self.shown.append(screen)),
            mock.patch.object(ops, "app_url", lambda page: None),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.owner = ui.Ctx(5, "en", admin=SimpleNamespace(id=1, name="Ann", mode="super_admin", telegram_id=5))
        self.admin = ui.Ctx(6, "en", admin=SimpleNamespace(id=2, name="Bo", mode="admin", telegram_id=6))

    def data(self, screen):
        return [b.callback_data for row in screen.markup.keyboard for b in row if b.callback_data]


class GateTests(Base):
    def test_super_admins_only(self):
        self.assertTrue(ops.allowed(self.owner))
        self.assertFalse(ops.allowed(self.admin))
        ops.show_apply(self.admin, ["go"])
        self.assertEqual(self.shown, [])
        with mock.patch(ADV, lambda: False):
            self.assertFalse(ops.allowed(self.owner))
            self.assertEqual(ops.status_rows(self.owner), [])


class ApplyTests(Base):
    def test_confirm_then_start_and_watch(self):
        api = SimpleNamespace(running_actions=lambda: [], _last_runs=lambda: {}, start_action=mock.MagicMock())
        with mock.patch.object(ops, "_apply_api", lambda: api), mock.patch.object(ops, "background") as bg:
            ops.show_apply(self.owner, ["ask"])
            self.assertIn("ap:go", self.data(self.shown[-1]))
            api.start_action.assert_not_called()
            ops.show_apply(self.owner, ["go"])
        api.start_action.assert_called_once_with("apply")
        bg.assert_called_once()

    def test_busy_panel_says_so(self):
        def refuse(_a):
            raise RuntimeError("Another action is still running")

        api = SimpleNamespace(running_actions=lambda: ["install"], _last_runs=lambda: {}, start_action=refuse)
        with mock.patch.object(ops, "_apply_api", lambda: api):
            ops.show_apply(self.owner, ["go"])
            self.assertEqual(self.toasts[-1], t(T.op_not_started, "en"))
            ops.show_apply(self.owner, [])
        self.assertNotIn("ap:ask", self.data(self.shown[-1]))  # no Apply key while something runs


class TestResultTests(Base):
    def test_summary_lines(self):
        result = {"at": 1700000000, "apps": {"xray": {"total": 3, "ok": 2, "failed": [{"name": "vless-ws"}]}, "hiddify": {"error": "timeout", "total": 0, "ok": 0}}}
        text = "\n".join(ops.result_lines("en", result))
        self.assertIn(t(T.op_test_ok, "en", ok=2, total=3), text)
        self.assertIn("vless-ws", text)
        self.assertIn(t(T.op_test_error, "en"), text)
        self.assertEqual(ops.result_lines("en", None), [t(T.op_no_test, "en")])


if __name__ == "__main__":
    unittest.main()
