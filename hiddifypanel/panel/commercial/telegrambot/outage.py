"""Server down / back notices: every few minutes the server's enabled proxy services are checked (the doctor's rule).
One that stays down for a while (not a restart, and not while an Apply or an update runs) is an outage: the admins
are told at once, and the users who were online lately (with alerts on) get a calm note. When it is back, the same
people hear that it is back."""

from __future__ import annotations

import datetime
import json
import time

from loguru import logger

from hiddifypanel.cache import redis_client
from hiddifypanel.models import AdminUser, ConfigEnum, User, hconfig

from . import bot, doctor
from .texts import T, t
from .ui import Cb, Style, btn, h, keyboard, lang_of, with_retry

#: A service down this long is an outage (an Apply or a restart takes less).
GRACE = 5 * 60
#: Users who were online this recently are told.
RECENT = datetime.timedelta(hours=24)
#: One outage note per user at most this often (a flapping server does not flood them).
USER_EVERY = 6 * 3600
MAX_USERS = 3000

_FIRST = "tgbot:outage:first"
_ON = "tgbot:outage:on"
_TOLD = "tgbot:outage:told"
_USER = "tgbot:outage:user:{}"
_KEEP = 7 * 24 * 3600


def _busy() -> bool:
    """An Apply, an install or an update is running: its restarts are not an outage."""
    try:
        from hiddifypanel.panel.commercial.restapi.v2.admin.apply_api import running_actions

        return bool(running_actions())
    except Exception as e:
        logger.debug(f"tgbot outage: actions not known: {e}")
        return False


def _decode(raw) -> str:
    return raw.decode() if isinstance(raw, bytes) else str(raw or "")


def _send(chat_id: int, text: str, markup, lang: str) -> bool:
    from . import topics

    try:
        topics.deliver(chat_id, "alerts", lang, lambda x: with_retry(lambda: bot.send_message(chat_id, text, reply_markup=markup, **x), attempts=3))
        return True
    except Exception as e:
        logger.debug(f"tgbot outage: {chat_id} not told: {e}")
        return False


def _admins() -> list[AdminUser]:
    return AdminUser.query.filter(AdminUser.telegram_id.isnot(None), AdminUser.telegram_id != 0, AdminUser.deleted.is_(False)).all()


def _recent_users() -> list[User]:
    since = datetime.datetime.now() - RECENT
    return (
        User.query.filter(User.deleted.is_(False), User.enable.is_(True), User.telegram_id.isnot(None), User.telegram_id != 0, User.last_online >= since)
        .limit(MAX_USERS)
        .all()
    )


def _declare(units: tuple[str, ...], since: float) -> None:
    from .notify import alerts_on

    redis_client.set(_ON, json.dumps({"since": since, "units": list(units)}), ex=_KEEP)
    told: list[int] = []
    when = datetime.datetime.fromtimestamp(since).strftime("%H:%M")
    for admin in _admins():
        lang = lang_of(admin, admin=True)
        text = f"🚨 {t(T.out_admin, lang, units=h(', '.join(units)), time=when)}"
        if _send(admin.telegram_id, text, keyboard([btn(t(T.btn_check, lang), Cb.check), btn(t(T.menu, lang), Cb.home)]), lang):
            told.append(admin.telegram_id)
    users = 0
    for user in _recent_users():
        if user.telegram_id in told or not alerts_on(user.telegram_id):
            continue
        if not redis_client.set(_USER.format(user.telegram_id), 1, nx=True, ex=USER_EVERY):
            continue
        lang = lang_of(user, admin=False)
        if _send(user.telegram_id, f"⚠️ {t(T.out_user, lang)}", None, lang):
            told.append(user.telegram_id)
            users += 1
    if told:
        redis_client.sadd(_TOLD, *told)
        redis_client.expire(_TOLD, _KEEP)
    logger.warning(f"tgbot outage: {', '.join(units)} down; told {len(told) - users} admins and {users} users")


def _recover(since: float) -> None:
    told = {int(_decode(x)) for x in (redis_client.smembers(_TOLD) or set())}
    admin_chats = {a.telegram_id: a for a in _admins()}
    minutes = max(round((time.time() - since) / 60), 1)
    for chat_id in told:
        admin = admin_chats.get(chat_id)
        if admin is not None:
            lang = lang_of(admin, admin=True)
            _send(chat_id, f"✅ {t(T.back_admin, lang, minutes=minutes)}", None, lang)
            continue
        user = User.query.filter(User.telegram_id == chat_id, User.deleted.is_(False)).first()
        lang = lang_of(user, admin=False)
        _send(chat_id, f"✅ {t(T.back_user, lang)}", keyboard([btn(t(T.doctor, lang), Cb.doctor, style=Style.primary)]), lang)
    redis_client.delete(_ON, _TOLD)
    logger.info(f"tgbot outage: over after {minutes} min; told {len(told)} chats")


def check() -> None:
    """Scheduled every few minutes (in one worker)."""
    if not hconfig(ConfigEnum.telegram_bot_token):
        return
    if _busy():
        redis_client.delete(_FIRST)
        return
    down = doctor.down_units()
    on = redis_client.get(_ON)
    now = time.time()
    if down:
        first = redis_client.get(_FIRST)
        if first is None:
            redis_client.set(_FIRST, now, ex=_KEEP)
            return
        if on is None and now - float(_decode(first)) >= GRACE:
            _declare(down, float(_decode(first)))
        return
    redis_client.delete(_FIRST)
    if on is not None:
        try:
            since = float(json.loads(_decode(on)).get("since", now))
        except ValueError:
            since = now
        _recover(since)
