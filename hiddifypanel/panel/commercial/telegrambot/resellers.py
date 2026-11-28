"""Advanced mode, its own switch: a bot of their own for each agent (reseller), made with Telegram's managed bots
(Bot API 9.6).

An agent presses "My own bot" in the bot's Settings; Telegram asks them to create a bot (the name and username they
choose) and hands it to this bot to manage. The panel then takes its token (getManagedBotToken), points its webhook
here (api/v1/tgbot/m/<bot id>/) and from then on the same bot code answers in it: the agent's own brand, for the
agent and their own users only. Nobody else is known there; the agent's users still use the panel's bot too if they
like.

It needs "Bot Management Mode" turned on for the panel's bot in @BotFather's Mini App, and the owner's switch.

How it works: each update of an agent's bot runs with that bot's token and username chosen for the request (a
context variable read by the panel's bot object), so every send of the shared code goes out from the agent's bot.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass

from loguru import logger
from telebot import types

from . import advanced
from .texts import T, t
from .ui import RULE, Cb, Ctx, Screen, btn, keyboard, route

_PANEL = 0
_PREF = "mbot:{}"  # bot id → {"token", "agent", "username"} (bot_pref of chat 0)
_INDEX = "mbots"  # the managed bots' ids, comma separated
REQUEST_ID = 9601


@dataclass(frozen=True)
class Managed:
    bot_id: int
    token: str
    agent_id: int
    username: str


#: The agent's bot this request runs for (None: the panel's own bot); kept by the panel's bot object
from hiddifypanel.panel.commercial.restapi.v1.tgbot import managed_bot as current  # noqa: E402


def allowed() -> bool:
    return advanced.feature(advanced.RESELLER_BOTS)


# --------------------------------------------------------------------------- storage


def _pref():
    from hiddifypanel.models import BotPref

    return BotPref


def all_bots() -> list[Managed]:
    ids = [i for i in (_pref().get(_PANEL, _INDEX) or "").split(",") if i.isdigit()]
    return [m for i in ids if (m := find(int(i)))]


def find(bot_id: int) -> Managed | None:
    raw = _pref().get(_PANEL, _PREF.format(bot_id))
    try:
        data = json.loads(raw) if raw else None
    except ValueError:
        return None
    if not data or not data.get("token"):
        return None
    return Managed(bot_id, str(data["token"]), int(data.get("agent") or 0), str(data.get("username") or ""))


def of_agent(agent_id: int) -> Managed | None:
    return next((m for m in all_bots() if m.agent_id == agent_id), None)


def save(m: Managed) -> None:
    from hiddifypanel.database import db

    pref = _pref()
    pref.put(_PANEL, _PREF.format(m.bot_id), json.dumps({"token": m.token, "agent": m.agent_id, "username": m.username}))
    ids = [i for i in (pref.get(_PANEL, _INDEX) or "").split(",") if i.isdigit() and int(i) != m.bot_id]
    pref.put(_PANEL, _INDEX, ",".join([*ids, str(m.bot_id)]))
    db.session.commit()


def forget(m: Managed) -> None:
    """An agent's bot that is gone (deleted in BotFather, its token revoked): out of the panel, so the agent can make
    a new one and nobody keeps calling Telegram for it."""
    from hiddifypanel.database import db

    pref = _pref()
    pref.put(_PANEL, _PREF.format(m.bot_id), "")
    ids = [i for i in (pref.get(_PANEL, _INDEX) or "").split(",") if i.isdigit() and int(i) != m.bot_id]
    pref.put(_PANEL, _INDEX, ",".join(ids))
    db.session.commit()
    logger.info(f"tgbot: agent {m.agent_id}'s bot {m.bot_id} is gone, forgotten")


def is_gone(e: Exception) -> bool:
    """Telegram says the bot's token is no longer valid (the bot deleted or its token revoked)."""
    return getattr(e, "error_code", None) in (401, 404)


def webhook_secret(token: str) -> str:
    return hmac.new(b"hiddify-managed-bot", token.encode(), hashlib.sha256).hexdigest()[:48]


# --------------------------------------------------------------------------- who an agent's bot knows


def scope_ids() -> set[int] | None:
    """The admins whose accounts an agent's bot knows (the agent and those under them); None in the panel's bot."""
    m = current.get()
    if m is None:
        return None
    from hiddifypanel.models import AdminUser

    agent = AdminUser.by_id(m.agent_id)
    return set(agent.recursive_sub_admins_ids()) if agent and not agent.deleted else set()


def admin_in_scope(admin) -> bool:
    ids = scope_ids()
    return ids is None or (admin is not None and admin.id in ids)


def user_in_scope(user) -> bool:
    ids = scope_ids()
    return ids is None or (user is not None and user.added_by in ids)


def state_prefix() -> str:
    """Chat state is kept apart per bot (the same person may use the panel's bot and an agent's bot)."""
    m = current.get()
    return f"m{m.bot_id}:" if m else ""


# --------------------------------------------------------------------------- making one


def settings_lines(ctx: Ctx) -> list[str]:
    if not allowed() or ctx.admin is None or current.get() is not None:
        return []
    m = of_agent(ctx.admin.id)
    state = f"@{m.username}" if m else ctx.tr(T.off)
    return [f"🤖 {ctx.tr(T.rb_title)}: <b>{state}</b>", f"<i>{ctx.tr(T.rb_hint)}</i>"]


def settings_rows(ctx: Ctx) -> list[list]:
    if not allowed() or ctx.admin is None or current.get() is not None:
        return []
    return [[btn(f"🤖 {ctx.tr(T.rb_title)}", Cb.reseller_bot)]]


@route(Cb.reseller_bot, admin=True)
def show_reseller_bot(ctx: Ctx, _args: list[str]) -> None:
    """The agent's own bot: its name when there is one, else the key (by the message box) that makes it."""
    from . import bot

    if not allowed() or ctx.admin is None or current.get() is not None:
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    ctx.toast()
    m = of_agent(ctx.admin.id)
    if m:
        import telebot

        try:
            telebot.TeleBot(m.token, threaded=False).get_me()
        except Exception as e:
            if is_gone(e):  # deleted in BotFather: the key to make a new one, below
                forget(m)
                m = None
    if m:
        lines = [f"🤖 <b>{ctx.tr(T.rb_title)}</b>", RULE, ctx.tr(T.rb_ready, name=f"@{m.username}")]
        return ctx.show(Screen("\n".join(lines), keyboard([types.InlineKeyboardButton(f"@{m.username}", url=f"https://t.me/{m.username}")], [btn(ctx.tr(T.back), Cb.admin_settings)])))
    base = "".join(c for c in (ctx.admin.name or "shop").lower() if c.isalnum())[:20] or "shop"
    key = types.KeyboardButton(
        ctx.tr(T.rb_create_key),
        request_managed_bot=types.KeyboardButtonRequestManagedBot(REQUEST_ID, suggested_name=(ctx.admin.name or "VPN")[:60], suggested_username=f"{base}_vpn_bot"),
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(key)
    try:
        sent = bot.send_message(ctx.chat_id, f"🤖 <b>{ctx.tr(T.rb_title)}</b>\n{RULE}\n{ctx.tr(T.rb_how)}", reply_markup=markup)
        # The key takes the menu keyboard's place: as a Cancel keyboard, any other button brings the menu back
        from . import menukey

        ctx.state.update(**{menukey.CANCEL_FLAG: 1, menukey.CANCEL_MSG: sent.message_id})
    except Exception as e:  # Bot Management Mode is off in BotFather: Telegram refuses the key
        logger.warning(f"tgbot: managed bot key refused: {e}")
        ctx.show(Screen(f"🤖 <b>{ctx.tr(T.rb_title)}</b>\n{RULE}\n⚠️ {ctx.tr(T.rb_not_enabled)}", keyboard([btn(ctx.tr(T.back), Cb.admin_settings)])))


def adopt(owner_tg_id: int, new_bot: types.User) -> Managed | None:
    """Telegram made a bot for this agent (Update.managed_bot): take its token, point it here, remember it."""
    from hiddifypanel.models import AdminUser

    from . import bot

    if not allowed():
        return None
    agent = AdminUser.query.filter(AdminUser.telegram_id == owner_tg_id, AdminUser.deleted.is_(False)).first()
    if agent is None:
        logger.warning(f"tgbot: a managed bot for an unknown Telegram account {owner_tg_id}")
        return None
    token = bot.get_managed_bot_token(new_bot.id)
    m = Managed(new_bot.id, token, agent.id, new_bot.username or "")
    save(m)
    connect(m)
    return m


def connect(m: Managed) -> None:
    """The agent's bot's webhook points here; its commands and menu like the panel's bot."""
    import telebot

    from hiddifypanel.panel.commercial.restapi.v1.tgbot import panel_domain_name
    from hiddifypanel.models import ConfigEnum, hconfig

    from .accounts import user_host

    domain = panel_domain_name() or user_host()
    url = f"https://{domain}/{hconfig(ConfigEnum.proxy_path_admin)}/api/v1/tgbot/m/{m.bot_id}/"
    other = telebot.TeleBot(m.token, parse_mode="HTML", threaded=False)
    other.set_webhook(url=url, secret_token=webhook_secret(m.token), allowed_updates=["message", "callback_query", "message_reaction"])
    logger.info(f"tgbot: agent {m.agent_id}'s bot @{m.username} connected")


def on_managed_bot(update: types.ManagedBotUpdated) -> None:
    """The panel's bot hears that an agent made (or changed) their bot."""
    from . import bot
    from .ui import lang_of

    m = adopt(update.user.id, update.bot)
    if m is None:
        return
    from hiddifypanel.models import AdminUser

    agent = AdminUser.by_id(m.agent_id)
    lang = lang_of(agent, admin=True)
    from . import menukey

    # The menu keyboard comes back in place of the key that made the bot (say never raises)
    menukey.say(update.user.id, lang, f"🤖 {t(T.rb_ready, lang, name='@' + m.username)}", admin_mode=menukey.admin_mode(agent))
