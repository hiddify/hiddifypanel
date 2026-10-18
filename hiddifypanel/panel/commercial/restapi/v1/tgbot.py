import hashlib
import hmac
import time

from apiflask import abort
from flask import request
from flask_restful import Resource
from loguru import logger

from hiddifypanel.cache import cache, redis_client
from hiddifypanel.models import *


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

            real = telebot.TeleBot("1:2", parse_mode="HTML", threaded=False, exception_handler=ExceptionHandler())
            real.username = ""
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
            abort(404)
        if not hmac.compare_digest(request.headers.get("X-Telegram-Bot-Api-Secret-Token", ""), webhook_secret()):
            abort(403)
        if request.headers.get("content-type") != "application/json":
            abort(415)
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
            abort(404)
        from flask import make_response

        from hiddifypanel.panel.commercial.telegrambot.webapp import PAGE

        res = make_response(PAGE)
        res.headers["Content-Type"] = "text/html; charset=utf-8"
        res.headers["Cache-Control"] = "no-store"
        return res


class TGAppLoginResource(Resource):
    def post(self):
        token = hconfig(ConfigEnum.telegram_bot_token)
        if not token:
            abort(404)
        from hiddifypanel.auth import login_user
        from hiddifypanel.panel import hiddify
        from hiddifypanel.panel.commercial.telegrambot.webapp import telegram_user_id

        tg_id = telegram_user_id(str((request.get_json(silent=True) or {}).get("init_data") or ""), token)
        if tg_id is None:
            return {"error": "Invalid Telegram sign-in"}, 403
        admin = AdminUser.query.filter(AdminUser.telegram_id == tg_id, AdminUser.deleted.is_(False)).first()
        if admin:
            login_user(admin, force=True)
            return {"redirect": f"/{hconfig(ConfigEnum.proxy_path_admin)}/admin/v2/"}
        user = User.query.filter(User.telegram_id == tg_id, User.deleted.is_(False)).first()
        if user:
            return {"redirect": hiddify.get_account_panel_link(user, request.host)}
        return {"error": "This Telegram account is not linked to the panel. Send /start from the panel link first."}, 403
