import unittest
from types import SimpleNamespace
from unittest import mock

from hiddifypanel.panel.commercial.telegrambot import admin as bot_admin


class FakeUser(SimpleNamespace):
    def reset_usage(self):
        self.current_usage = 0


class UserActionActiveLimitTests(unittest.TestCase):
    """The user card buttons that turn a user on keep to the admin's max_active_users."""

    def run_action(self, action, *, enable, room):
        user = FakeUser(id=5, name="u", enable=enable, start_date="2026-01-01", current_usage=10)
        ctx = mock.MagicMock()
        ctx.tr.side_effect = lambda key, **kw: key
        ctx.admin.can_activate_more_users.return_value = room
        with (
            mock.patch.object(bot_admin, "_visible_user", return_value=user),
            mock.patch.object(bot_admin.accounts, "is_read_only", return_value=False),
            mock.patch.object(bot_admin.accounts, "apply"),
            mock.patch.object(bot_admin, "card_screen"),
            mock.patch.object(bot_admin, "db") as db,
        ):
            bot_admin.user_action(ctx, [str(user.id), action])
        return user, ctx, db.session.commit

    def test_renew_does_not_turn_on_a_user_past_the_limit(self):
        user, ctx, commit = self.run_action("renew", enable=False, room=False)
        self.assertFalse(user.enable)
        self.assertEqual(user.current_usage, 10)
        commit.assert_not_called()
        ctx.toast.assert_called_with(bot_admin.T.limit_reached, alert=True)

    def test_renew_turns_on_a_user_when_there_is_room(self):
        user, _, commit = self.run_action("renew", enable=False, room=True)
        self.assertTrue(user.enable)
        self.assertEqual(user.current_usage, 0)
        commit.assert_called_once()

    def test_renew_of_an_enabled_user_is_allowed_at_the_limit(self):
        # Not one more active user: the limit does not block it
        user, ctx, commit = self.run_action("renew", enable=True, room=False)
        self.assertTrue(user.enable)
        self.assertIsNone(user.start_date)
        commit.assert_called_once()
        ctx.admin.can_activate_more_users.assert_not_called()

    def test_on_does_not_turn_on_a_user_past_the_limit(self):
        user, _, commit = self.run_action("on", enable=False, room=False)
        self.assertFalse(user.enable)
        commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
