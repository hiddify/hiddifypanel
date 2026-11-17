# from flask_simplelogin import login_required
import datetime

from apiflask import abort
from flask import request
from flask_restful import Resource
from loguru import logger

from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.models import *

from .tgbot import bot


#: Up to this many people, the message is sent before answering (with each one's error, if any).
SEND_NOW_MAX = 20


def _send_all(targets: list[tuple[str, str, int]], text: str) -> dict[str, dict[str, str]]:
    """``text`` and the account card to each (uuid, name, telegram id); the errors by uuid."""
    from hiddifypanel.panel.commercial.telegrambot import Usage
    from hiddifypanel.panel.commercial.telegrambot.ui import with_retry

    errors: dict[str, dict[str, str]] = {}
    for uuid, name, telegram_id in targets:
        try:
            txt = text + "\n\n" + Usage.get_usage_msg(uuid)
            keyboard = Usage.user_keyboard(uuid)
            with_retry(lambda: bot.send_message(telegram_id, txt, reply_markup=keyboard))
        except Exception as e:
            logger.info(f"tgbot: message to {uuid} not sent: {e}")
            errors[uuid] = {"name": name, "error": f"{e}"}
    if len(targets) > SEND_NOW_MAX:
        logger.info(f"tgbot: message sent to {len(targets) - len(errors)} of {len(targets)} users")
    return errors


class SendMsgResource(Resource):
    @login_required({Role.super_admin, Role.admin, Role.agent})
    def post(self, admin_uuid=None):

        if not hconfig(ConfigEnum.telegram_bot_token) or not bot:
            abort(400, "invalid request")

        msg = request.json
        if not msg or not msg.get("id") or not msg.get("text"):
            abort(400, "invalid request")

        users = self.get_users_by_identifier(msg["id"])
        targets = [(user.uuid, user.name, user.telegram_id) for user in users if user]
        text = str(msg["text"])

        # A few are sent now and their errors answered; a big group goes out after the answer (Telegram takes about
        # 30 messages a second, a long request would time out), waiting out the flood limits.
        if len(targets) > SEND_NOW_MAX:
            from hiddifypanel.panel.commercial.telegrambot.ui import background

            background(lambda: _send_all(targets, text))
            return {"msg": "queued", "count": len(targets)}

        res = _send_all(targets, text)
        if len(res) == 0:
            return {"msg": "success"}
        else:
            return {"msg": "error", "res": res}

    def get_users_by_identifier(self, identifier: str | list) -> list[User]:
        """Returns all users that match the identifier for sending a message to them"""
        # when we are here we must have g.account but ...
        if not hasattr(g, "account"):
            return []

        # Not deleted users, with a telegram id (``telegram_id is not None`` in Python was always true)
        query = User.query.filter(
            User.added_by.in_(g.account.recursive_sub_admins_ids()),
            User.deleted.isnot(True),
            User.telegram_id.isnot(None),
            User.telegram_id != 0,
        )

        # user selected many ids as users identifier
        if isinstance(identifier, list):
            return query.filter(User.id.in_(identifier)).all()

        if hutils.convert.is_int(identifier):
            return [query.filter(User.id == int(identifier)).first() or abort(404, "The user not found")]
        if identifier == "all":
            return query.all()
        if identifier == "expired":
            return [u for u in query.all() if not u.is_active]
        if identifier == "active":
            return [u for u in query.all() if u.is_active]
        if identifier == "offline 1h":
            h1 = datetime.datetime.now() - datetime.timedelta(hours=1)
            return [u for u in query.all() if u.is_active and u.last_online < h1]
        if identifier == "offline 1d":
            d1 = datetime.datetime.now() - datetime.timedelta(hours=24)
            return [u for u in query.all() if u.is_active and u.last_online < d1]
        if identifier == "offline 1w":
            d7 = datetime.datetime.now() - datetime.timedelta(days=7)
            return [u for u in query.all() if u.is_active and u.last_online < d7]
        return []
