import contextvars
import hashlib
import hmac
import time

from apiflask import abort
from flask import request
from flask_restful import Resource
from loguru import logger

from hiddifypanel.cache import cache, redis_client
from hiddifypanel.models import *


#: The agent's own bot an update runs for (telegrambot/resellers.py); None: the panel's bot
managed_bot: contextvars.ContextVar = contextvars.ContextVar("tgbot_managed", default=None)


class _LazyBot:
    """Defers importing telebot (and creating its TeleBot/requests.Session) until
    the bot is actually touched, so installs that never configure a Telegram bot
    don't pay for it on every process startup."""

    __slots__ = ("_real",)

    def __init__(self):
        object.__setattr__(self, "_real", None)

    def _ensure(self):
        real = object.__getattribute__(self, "_real")
        if real is None:
            import telebot

            class ExceptionHandler(telebot.ExceptionHandler):
                def handle(self, exception):
                    """Improved error handling for Telegram bot exceptions"""
                    error_msg = str(exception)
                    logger.error(f"Telegram bot error: {error_msg}")

                    try:
                        # Attempt recovery based on error type
                        if "webhook" in error_msg.lower():
                            if hasattr(bot, "remove_webhook"):
                                bot.remove_webhook()
                                logger.info("Removed webhook due to error")
                        elif "connection" in error_msg.lower():
                            # Wait and retry for connection issues
                            time.sleep(5)
                            return True  # Indicates retry
                    except Exception as e:
                        logger.error(f"Error during recovery attempt: {str(e)}")

                    return False  # Don't retry for unknown errors

            class PanelBot(telebot.TeleBot):
                """The panel's bot; during an update of an agent's own bot (telegrambot/resellers.py) its token and
                username are that bot's, so the shared code answers from it."""

                @property
                def token(self):
                    managed = managed_bot.get()
                    return managed.token if managed else self.__dict__.get("_panel_token", "")

                @token.setter
                def token(self, value):
                    self.__dict__["_panel_token"] = value

                @property
                def username(self):
                    managed = managed_bot.get()
                    return managed.username if managed else self.__dict__.get("_panel_username", "")

                @username.setter
                def username(self, value):
                    self.__dict__["_panel_username"] = value

            real = PanelBot("1:2", parse_mode="HTML", threaded=False, exception_handler=ExceptionHandler())
            real.username = ""
            # Animated button icons that Telegram refuses are sent again as plain emoji (telegrambot/icons.py)
            from hiddifypanel.panel.commercial.telegrambot.icons import install_refusal_guard

            install_refusal_guard()
            # The bot's messages reach a chat that asked for it without a sound (telegrambot/silence.py)
            from hiddifypanel.panel.commercial.telegrambot import silence

            silence.install()
            # Buttons inside the message (soft pills), Telegram's rich messages (telegrambot/rich.py); outermost
            from hiddifypanel.panel.commercial.telegrambot import rich

            rich.install()
            object.__setattr__(self, "_real", real)
        return real

    def __getattr__(self, name):
        return getattr(self._ensure(), name)

    def __setattr__(self, name, value):
        setattr(self._ensure(), name, value)


bot = _LazyBot()


def webhook_secret() -> str:
    """Value Telegram echoes back in X-Telegram-Bot-Api-Secret-Token.

    Derived from the bot token, so it needs no extra setting and changes with the token.
    """
    token = hconfig(ConfigEnum.telegram_bot_token) or ""
    return hmac.new(token.encode(), b"hiddify-tgbot-webhook", hashlib.sha256).hexdigest()


def panel_domain_name() -> str | None:
    """The panel domain Telegram can reach: the first valid one that is a real name (Telegram refuses webhooks and
    Mini Apps on an IP); an IP only when there is nothing else."""
    import ipaddress

    from hiddifypanel.models.domain import DomainType, FakeMode

    def is_name(host: str) -> bool:
        try:
            ipaddress.ip_address(host.strip("[]"))
            return False
        except ValueError:
            return "." in host and "*" not in host

    modes = [DomainType.direct, DomainType.cdn, DomainType.worker, DomainType.relay, DomainType.sub_link_only]
    rows = Domain.query.filter(Domain.mode.in_(modes), Domain.fake_mode == FakeMode.valid, Domain.child_id == Child.current().id).order_by(*Domain.ordering()).all()
    names = [d.domain for d in rows if d.domain]
    return next((n for n in names if is_name(n)), names[0] if names else None)


@cache.cache(1000)
def register_bot_cached(set_hook=False, remove_hook=False):
    return register_bot(set_hook, remove_hook)


def register_bot(set_hook=False, remove_hook=False) -> dict:
    """Points the bot at this panel. Returns ``{"ok", "username", "error"}`` so callers can report it."""
    try:
        token = hconfig(ConfigEnum.telegram_bot_token)
        if not token:
            return {"ok": False, "username": "", "error": ""}
        bot.token = token
        try:
            bot.username = bot.get_me().username
        except Exception as e:
            logger.error(f"Telegram bot token rejected: {e}")
            return {"ok": False, "username": "", "error": f"Invalid token: {e}"}
        if remove_hook:
            bot.remove_webhook()
        domain = panel_domain_name()
        if not domain:
            raise Exception("Cannot get valid domain for setting telegram bot webhook")

        admin_proxy_path = hconfig(ConfigEnum.proxy_path_admin)

        if set_hook:
            # No admin uuid in the URL: uuid-path auth rejects admins with a password.
            bot.set_webhook(url=f"https://{domain}/{admin_proxy_path}/api/v1/tgbot/", secret_token=webhook_secret())
            # The "/" menu (menu, language) in every language the bot speaks
            from hiddifypanel.panel.commercial.telegrambot.settings import set_commands

            set_commands()
        return {"ok": True, "username": bot.username, "error": ""}
    except Exception as e:
        logger.error(e)
        return {"ok": False, "username": "", "error": str(e)}


def init_app(app):
    with app.app_context():
        token = hconfig(ConfigEnum.telegram_bot_token)
        if token:
            bot.token = token
            try:
                bot.username = bot.get_me().username
            except BaseException:
                pass


class TGBotResource(Resource):
    def post(self):
        if not hconfig(ConfigEnum.telegram_bot_token):
            return {"error": "not_found"}, 404
        if not hmac.compare_digest(request.headers.get("X-Telegram-Bot-Api-Secret-Token", ""), webhook_secret()):
            return {"error": "forbidden"}, 403
        if request.headers.get("content-type") != "application/json":
            return {"error": "unsupported_media_type"}, 415
        try:
            import telebot

            # Registers the message handlers. Workers that started before the token
            # was set never imported it, so updates reached a bot with no handlers.
            import hiddifypanel.panel.commercial.telegrambot  # noqa: F401

            # The token may have been changed from another worker.
            token = hconfig(ConfigEnum.telegram_bot_token)
            if bot.token != token:
                bot.token = token
                try:
                    bot.username = bot.get_me().username
                except BaseException:
                    pass

            json_string = request.get_data().decode("utf-8")
            update = telebot.types.Update.de_json(json_string)
            # Telegram resends an update it did not see answered in time: handle each one once.
            if not redis_client.set(f"tgbot:update:{update.update_id}", 1, nx=True, ex=3600):
                return ""
            bot.process_new_updates([update])
        except Exception:
            # Still 200: an error answer makes Telegram resend the same update again and again.
            logger.exception("Telegram update failed")
        return ""


class TGAppResource(Resource):
    """The Mini App page: signs in with Telegram's signed initData, then opens the panel."""

    def get(self):
        if not hconfig(ConfigEnum.telegram_bot_token):
            return {"error": "not_found"}, 404
        from flask import make_response

        from hiddifypanel.panel.commercial.telegrambot.webapp import page

        res = make_response(page())
        res.headers["Content-Type"] = "text/html; charset=utf-8"
        res.headers["Cache-Control"] = "no-store"
        return res


class TGManagedBotResource(Resource):
    """Updates of an agent's own bot (telegrambot/resellers.py): the same handlers, that bot's token."""

    def post(self, bot_id: int):
        if not hconfig(ConfigEnum.telegram_bot_token):
            return {"error": "not_found"}, 404
        from hiddifypanel.panel.commercial.telegrambot import resellers

        # Answered as they are (apiflask's abort inside a flask-restful resource comes out as a 500)
        managed = resellers.find(bot_id)
        if managed is None or not resellers.allowed():
            return {"error": "not_found"}, 404
        if not hmac.compare_digest(request.headers.get("X-Telegram-Bot-Api-Secret-Token", ""), resellers.webhook_secret(managed.token)):
            return {"error": "forbidden"}, 403
        try:
            import telebot

            import hiddifypanel.panel.commercial.telegrambot  # noqa: F401  (registers the handlers)

            update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
            if not redis_client.set(f"tgbot:update:m{bot_id}:{update.update_id}", 1, nx=True, ex=3600):
                return ""
            if not bot.token:  # the panel's own token, for the shared object (the agent's comes from the context)
                bot.token = hconfig(ConfigEnum.telegram_bot_token)
            mark = resellers.current.set(managed)
            try:
                bot.process_new_updates([update])
            finally:
                resellers.current.reset(mark)
        except Exception:
            logger.exception("Telegram update of an agent's bot failed")
        return ""


class TGBackupResource(Resource):
    """A backup from the bot's Backup History: a random key (an hour) for that one file, made for the owner's chat."""

    def get(self, key: str):
        if not hconfig(ConfigEnum.telegram_bot_token) or not key or len(key) > 64:
            return {"error": "not_found"}, 404
        name = redis_client.get(f"tgbot:bkdl:{key}")
        name = name.decode() if isinstance(name, bytes) else name
        if not name:
            return {"error": "expired"}, 404
        from hiddifypanel.panel.commercial.restapi.v2.admin.backup_api import FILE_RE, _json_attachment, backup_dir

        path = backup_dir() / name
        if not FILE_RE.match(name) or not path.is_file():
            return {"error": "not_found"}, 404
        return _json_attachment(path.read_text(encoding="utf-8"), f"hiddify-{name}")


class TGAppActResource(Resource):
    """The bot's small Mini App page: biometric confirm, QR scan, emoji status (telegrambot/miniapp.py)."""

    def get(self):
        if not hconfig(ConfigEnum.telegram_bot_token):
            return {"error": "not_found"}, 404
        from flask import make_response

        from hiddifypanel.panel.commercial.telegrambot.miniapp import page

        res = make_response(page())
        res.headers["Content-Type"] = "text/html; charset=utf-8"
        res.headers["Cache-Control"] = "no-store"
        return res

    def post(self):
        token = hconfig(ConfigEnum.telegram_bot_token)
        if not token:
            return {"error": "not_found"}, 404
        from hiddifypanel.panel.commercial.telegrambot.miniapp import answer

        body = request.get_json(silent=True) or {}
        return answer(str(body.get("init_data") or ""), body, token)


class TGAppLoginResource(Resource):
    def post(self):
        token = hconfig(ConfigEnum.telegram_bot_token)
        if not token:
            return {"error": "not_found"}, 404
        from hiddifypanel.auth import login_user, logout_user
        from hiddifypanel.panel.commercial.telegrambot.webapp import destination, telegram_user_id

        body = request.get_json(silent=True) or {}
        init_data = str(body.get("init_data") or "")
        tg_id = telegram_user_id(init_data, token)
        managed = None
        if tg_id is None:  # opened from an agent's own bot: signed with that bot's token
            from hiddifypanel.panel.commercial.telegrambot import resellers

            if resellers.allowed():
                for candidate in resellers.all_bots():
                    if (tg_id := telegram_user_id(init_data, candidate.token)) is not None:
                        managed = candidate
                        break
        if tg_id is None:
            return {"error": "invalid_sign_in"}, 403
        mark = managed_bot.set(managed)  # an agent's bot signs in its own people only
        try:
            kind, account, answer = destination(tg_id, request.host, str(body.get("to") or "")[:40])
        finally:
            managed_bot.reset(mark)
        # Whoever opened it before on this device is signed out first: an admin's session never stays for someone else
        logout_user()
        if kind == "admin":
            login_user(account, force=True)
            return answer
        if kind == "user":
            return answer  # their own page (its address is their own key): no panel session at all
        return answer, 403
