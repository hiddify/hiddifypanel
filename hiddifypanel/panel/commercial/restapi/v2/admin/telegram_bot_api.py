"""The Telegram bot page (owner only): is the bot alive and reachable by Telegram, a test message to oneself, setting
the webhook again, and the animated button icons."""

from __future__ import annotations

import datetime
import re

from apiflask import abort
from flask import request
from flask.views import MethodView
from loguru import logger

from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.cache import redis_client
from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, ConfigEnum, Role, User, hconfig, set_hconfig

ROLES = {Role.super_admin}
#: Telegram may be blocked from the server: the page answers within this, whatever Telegram does.
TELEGRAM_TIMEOUT = 8
MAX_SETS_LENGTH = 1000
_SET_NAME = re.compile(r"^[A-Za-z0-9_]{1,64}$")


def _call(method: str, **params) -> dict:
    """One Bot API call with a short timeout (through the same path as the bot, so the icon guard applies)."""
    from telebot import apihelper

    token = str(hconfig(ConfigEnum.telegram_bot_token) or "")
    return apihelper._make_request(token, method, params={**params, "timeout": TELEGRAM_TIMEOUT})


def _error_kind(e: Exception) -> str:
    """What went wrong, as a key the page translates: the token is wrong, or Telegram is out of reach."""
    code = getattr(e, "error_code", None)
    return "token_rejected" if code in (401, 404) else "unreachable"


def _expected_webhook() -> tuple[str | None, str]:
    from hiddifypanel.panel.commercial.restapi.v1.tgbot import panel_domain_name

    domain = panel_domain_name()
    return domain, f"https://{domain}/{hconfig(ConfigEnum.proxy_path_admin)}/api/v1/tgbot/" if domain else ""


def _when(unix: object) -> str | None:
    return datetime.datetime.fromtimestamp(unix).isoformat() if isinstance(unix, int) and unix > 0 else None


def _icons(load: bool) -> dict:
    from hiddifypanel.panel.commercial.telegrambot import icons, texts

    state = {
        "enabled": bool(hconfig(ConfigEnum.telegram_bot_animated_icons)),
        "refused": bool(redis_client.get(icons._REFUSED_KEY)),
        "sets": str(hconfig(ConfigEnum.telegram_bot_icon_sets) or ""),
        "default_sets": list(icons.DEFAULT_SETS),
        "found": None,
        "needed": None,
        "missing": [],
    }
    if load and state["enabled"]:
        # How many of the emoji the bot's buttons start with have an animated icon in the sets, and which do not
        needed = sorted({icons._norm(m.group(1)) for text in texts._table("en").values() if (m := icons._LEADING_EMOJI.match(text))})
        missing = [emoji for emoji in needed if not icons.icon_for(emoji)]
        state["needed"] = len(needed)
        state["found"] = len(needed) - len(missing)
        state["missing"] = missing
    return state


def _state(load_icons: bool = True) -> dict:
    configured = bool(hconfig(ConfigEnum.telegram_bot_token))
    account = g.account
    state: dict = {
        "configured": configured,
        "bot": None,
        "error": None,
        "webhook": None,
        "me_connected": bool(getattr(account, "telegram_id", None)),
        "admins_connected": AdminUser.query.filter(AdminUser.telegram_id.isnot(None), AdminUser.telegram_id != 0, AdminUser.deleted.is_(False)).count(),
        "users_connected": User.query.filter(User.telegram_id.isnot(None), User.telegram_id != 0, User.deleted.is_(False)).count(),
        "icons": _icons(load=False),
    }
    if not configured:
        return state
    try:
        me = _call("getMe")
    except Exception as e:
        logger.info(f"tgbot page: getMe failed: {e}")
        state["error"] = _error_kind(e)
        return state
    state["bot"] = {
        "id": me.get("id"),
        "name": me.get("first_name") or "",
        "username": me.get("username") or "",
        "groups": bool(me.get("can_join_groups")),
        "main_app": bool(me.get("has_main_web_app")),
    }
    domain, expected = _expected_webhook()
    try:
        info = _call("getWebhookInfo")
        state["webhook"] = {
            "set": bool(info.get("url")),
            "matches": bool(expected) and info.get("url") == expected,
            "domain": domain or "",
            "pending": int(info.get("pending_update_count") or 0),
            "last_error": info.get("last_error_message") or None,
            "last_error_at": _when(info.get("last_error_date")),
        }
    except Exception as e:
        logger.info(f"tgbot page: getWebhookInfo failed: {e}")
        state["error"] = _error_kind(e)
    try:
        state["icons"] = _icons(load=load_icons)
    except Exception as e:
        logger.info(f"tgbot page: icons not checked: {e}")
    return state


def _forget(*keys: ConfigEnum) -> None:
    from hiddifypanel.models.child import Child

    child_id = Child.current().id
    for key in keys:
        hconfig.invalidate(key)
        hconfig.invalidate(key, child_id)
        hconfig.invalidate(key=key, child_id=child_id)


class TelegramBotApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self):
        return _state()


class TelegramBotTestApi(MethodView):
    """A message to this admin's own chat: the whole path (token, network, the chat link) works."""

    decorators = [login_required(ROLES)]

    def post(self):
        if not hconfig(ConfigEnum.telegram_bot_token):
            abort(400, "The Telegram bot is not set up")
        chat_id = getattr(g.account, "telegram_id", None)
        if not chat_id:
            return {"ok": False, "error": "not_connected"}
        from hiddifypanel.panel.commercial.restapi.v1.tgbot import bot
        from hiddifypanel.panel.commercial.telegrambot.texts import T, t
        from hiddifypanel.panel.commercial.telegrambot.ui import Cb, btn, celebrate, keyboard, lang_of

        lang = lang_of(g.account, admin=True)
        try:
            celebrate(bot.send_message, chat_id, f"✅ <b>{t(T.test_title, lang)}</b>\n{t(T.test_body, lang)}", reply_markup=keyboard([btn(t(T.menu, lang), Cb.home)]))
        except Exception as e:
            logger.info(f"tgbot page: test message failed: {e}")
            code = getattr(e, "error_code", None)
            return {"ok": False, "error": "blocked" if code in (400, 403) else _error_kind(e)}
        return {"ok": True, "error": None}


class TelegramBotWebhookApi(MethodView):
    """Point Telegram at this panel again (the domain or the admin path changed, or the webhook was lost)."""

    decorators = [login_required(ROLES)]

    def post(self):
        if not hconfig(ConfigEnum.telegram_bot_token):
            abort(400, "The Telegram bot is not set up")
        from hiddifypanel.panel.commercial.restapi.v1.tgbot import register_bot

        result = register_bot(set_hook=True, agents=True)
        if not result.get("ok"):
            logger.info(f"tgbot page: webhook not set: {result.get('error')}")
        return {"ok": bool(result.get("ok")), "state": _state(load_icons=False)}


class TelegramBotIconsApi(MethodView):
    """The animated icons option and their sets; saving also lifts a refusal, so the icons are tried again."""

    decorators = [login_required(ROLES)]

    def put(self):
        from hiddifypanel.panel.commercial.telegrambot import icons

        body = request.get_json(silent=True) or {}
        enabled = body.get("enabled")
        sets = body.get("sets")
        if enabled is not None:
            if not isinstance(enabled, bool):
                abort(400, "enabled must be true or false")
            set_hconfig(ConfigEnum.telegram_bot_animated_icons, enabled, commit=False)
        if sets is not None:
            if not isinstance(sets, str) or len(sets) > MAX_SETS_LENGTH:
                abort(400, "Invalid icon sets")
            names = [n.strip() for n in sets.replace("\n", ",").split(",") if n.strip()]
            if any(not _SET_NAME.match(n) for n in names):
                abort(400, "An icon set name has only letters, digits and _")
            set_hconfig(ConfigEnum.telegram_bot_icon_sets, ",".join(names), commit=False)
        db.session.commit()
        # set_hconfig clears the cache before the commit: a request in between (the bot answering someone) would keep
        # the old value for the cache's whole life, so it is cleared again now that the new one is in the database.
        _forget(ConfigEnum.telegram_bot_animated_icons, ConfigEnum.telegram_bot_icon_sets)
        redis_client.delete(icons._REFUSED_KEY)
        return _icons(load=True) if hconfig(ConfigEnum.telegram_bot_token) else _icons(load=False)
