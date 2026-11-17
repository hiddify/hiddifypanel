"""Daily nudges: each user whose package is about to end hears about it once, and each admin gets one summary
of their users instead of a message per user."""

from __future__ import annotations

import datetime
from collections import defaultdict

from loguru import logger
from telebot import types

from hiddifypanel.cache import redis_client
from hiddifypanel.models import AdminUser, ConfigEnum, User, hconfig

from . import accounts, bot
from .accounts import Filter
from .texts import T, t
from .ui import BRAND, Cb, Style, app_row, btn, celebrate, fmt_gb, h, keyboard, lang_of, with_retry

NOTIFY_DAYS = 3
NOTIFY_RATIO = 0.85
ADMIN_LIST_MAX = 15


def _ending(user: User) -> tuple[T, dict[str, object]] | None:
    """Why this user should hear from us today, if at all."""
    if accounts.status(user) is not accounts.Status.active:
        return None
    if user.start_date is not None and user.remaining_days <= NOTIFY_DAYS:
        return T.notify_days, {"n": user.remaining_days}
    if user.usage_limit and accounts.usage_ratio(user) >= NOTIFY_RATIO:
        return T.notify_data, {"left": fmt_gb(max(user.usage_limit_GB - user.current_usage_GB, 0), lang_of(user, admin=False))}
    return None


def status_changed(user: User) -> None:
    """Tell the user their account was switched on (a new period, a renewal) or off (the package ran out), with
    their account card, in their language. Never raises: the usage update that calls it must go on."""
    if not user.telegram_id or not hconfig(ConfigEnum.telegram_bot_token):
        return
    from .user import account_card

    lang = lang_of(user, admin=False)
    head = f"✅ <b>{t(T.notify_on, lang)}</b>" if user.is_active else f"⛔️ <b>{t(T.notify_off, lang)}</b>"
    markup = keyboard([btn(t(T.refresh, lang), Cb.me), btn(t(T.links, lang), Cb.me_links)], app_row(BRAND, accounts.links(user).home, Style.primary))
    try:
        text = f"{head}\n\n{account_card(user, lang)}"
        from . import topics

        if user.is_active:  # on again: a small celebration
            topics.deliver(user.telegram_id, "alerts", lang, lambda x: with_retry(lambda: celebrate(bot.send_message, user.telegram_id, text, reply_markup=markup, **x)))
        else:
            topics.deliver(user.telegram_id, "alerts", lang, lambda x: with_retry(lambda: bot.send_message(user.telegram_id, text, reply_markup=markup, **x)))
    except Exception as e:
        logger.info(f"tgbot: status notice to {user.uuid} not sent: {e}")


# --------------------------------------------------------------------------- staged alerts

#: (ratio, stage): 80% then 90% of the data. Running out is the "package ended" notice (status_changed).
DATA_STAGES = ((0.9, 2), (0.8, 1))
#: (days left at most, stage)
DAY_STAGES = ((1, 2), (3, 1))
_ALERT_KEY = "tgbot:alert:{}:{}"
_ALERT_TTL = 180 * 24 * 3600
ALERTS_PREF = "alerts"


def data_stage(user: User) -> int:
    if accounts.status(user) is not accounts.Status.active or not user.usage_limit:
        return 0
    ratio = accounts.usage_ratio(user)
    return next((stage for limit, stage in DATA_STAGES if ratio >= limit), 0)


def day_stage(user: User) -> int:
    if accounts.status(user) is not accounts.Status.active or user.start_date is None:
        return 0
    left = user.remaining_days
    return next((stage for limit, stage in DAY_STAGES if 0 <= left <= limit), 0)


def alerts_on(chat_id: int) -> bool:
    from hiddifypanel.models import BotPref

    return BotPref.get(chat_id, ALERTS_PREF, "1") != "0"


def _advance(user: User, kind: str, stage: int) -> bool:
    """True when ``stage`` is past the one this user last heard about. A lower stage (renewed, more data or days,
    reset) is remembered too, so the next crossing is told again."""
    key = _ALERT_KEY.format(kind, user.id)
    raw = redis_client.get(key)
    told = int(raw) if raw not in (None, b"", "") else 0
    if stage == told:
        return False
    redis_client.set(key, stage, ex=_ALERT_TTL)
    return stage > told


def _alert_markup(user: User, lang: str) -> types.InlineKeyboardMarkup:
    return keyboard(
        [btn(t(T.chart, lang), Cb.chart), btn(t(T.support, lang), Cb.support)],
        app_row(BRAND, accounts.links(user).home, Style.primary),
        [btn(t(T.alerts_off_btn, lang), Cb.pref, ALERTS_PREF, 0)],
    )


def alert(user: User, *, days: bool = False) -> bool:
    """Tell ``user`` about a stage of their data (and, with ``days``, of their time) they just reached, once. Never
    raises: it runs inside the usage update and the daily job. True when a message went out."""
    try:
        if not user.telegram_id:
            return False
        messages = []
        if _advance(user, "data", stage := data_stage(user)):
            messages.append(("data", stage))
        if days and _advance(user, "days", stage := day_stage(user)):
            messages.append(("days", stage))
        if not messages or not alerts_on(user.telegram_id):
            return False
        lang = lang_of(user, admin=False)
        lines = []
        for kind, _stage in messages:
            if kind == "data":
                percent = min(round(accounts.usage_ratio(user) * 100), 100)
                left = fmt_gb(max(user.usage_limit_GB - user.current_usage_GB, 0), lang)
                lines.append(f"⚠️ {t(T.alert_data, lang, name=h(user.name), percent=percent, left=left)}")
            else:
                left_days = max(user.remaining_days, 0)
                lines.append(f"⏳ {t(T.alert_days, lang, name=h(user.name), n=left_days)}" if left_days > 1 else f"⏳ {t(T.alert_last_day, lang, name=h(user.name))}")
        from . import topics

        markup = _alert_markup(user, lang)
        topics.deliver(user.telegram_id, "alerts", lang, lambda x: bot.send_message(user.telegram_id, "\n\n".join(lines), reply_markup=markup, **x))
        return True
    except Exception as e:
        logger.info(f"tgbot: alert to user {getattr(user, 'id', '?')} not sent: {e}")
        return False


def usage_alerts(users: list[User]) -> None:
    """After a usage update: the users whose data just crossed 80% or 90%."""
    if not users or not hconfig(ConfigEnum.telegram_bot_token):
        return
    for user in users:
        alert(user)


def run() -> None:
    """Scheduled once a day; the redis key keeps a second worker (or a restart) from sending twice."""
    if not hconfig(ConfigEnum.telegram_bot_token):
        return
    if not redis_client.set(f"tgbot:notify:{datetime.date.today()}", 1, nx=True, ex=36 * 3600):
        return
    from . import register_bot

    if not bot.username:
        register_bot()

    per_admin: dict[int, list[User]] = defaultdict(list)
    for user in User.query.filter(User.deleted.is_(False), User.enable.is_(True)).all():
        reason = _ending(user)
        if reason is None:
            continue
        per_admin[user.added_by or 1].append(user)
    # The users themselves: each stage once (3 days / 1 day left, 80% / 90% of the data), not every day
    for user in User.query.filter(User.deleted.is_(False), User.enable.is_(True), User.telegram_id.isnot(None)).all():
        alert(user, days=True)

    for admin_id, users in per_admin.items():
        admin = AdminUser.by_id(admin_id)
        if not admin or not admin.telegram_id:
            continue
        lang = lang_of(admin, admin=True)
        lines = [t(T.notify_admin, lang, n=len(users)), ""]
        for user in users[:ADMIN_LIST_MAX]:
            days = user.remaining_days if user.start_date else user.package_days
            lines.append(t(T.notify_admin_line, lang, name=h(user.name), days=days, used=f"{user.current_usage_GB:.1f}", total=f"{user.usage_limit_GB:g}"))
        if len(users) > ADMIN_LIST_MAX:
            lines.append(t(T.notify_admin_more, lang, n=len(users) - ADMIN_LIST_MAX))
        try:
            bot.send_message(admin.telegram_id, "\n".join(lines), reply_markup=keyboard([btn(t(T.f_expiring, lang), Cb.users, Filter.expiring.value, 0)]))
        except Exception as e:
            logger.debug(f"tgbot: notify admin {admin.id}: {e}")
