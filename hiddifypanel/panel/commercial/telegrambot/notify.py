"""Daily nudges: each user whose package is about to end hears about it once, and each admin gets one summary
of their users instead of a message per user."""

from __future__ import annotations

import datetime
from collections import defaultdict

from loguru import logger

from hiddifypanel.cache import redis_client
from hiddifypanel.models import AdminUser, ConfigEnum, User, hconfig

from . import accounts, bot
from .accounts import Filter
from .texts import T, t
from .ui import Cb, app_row, btn, fmt_gb, h, keyboard, lang_of

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
        if not user.telegram_id:
            continue
        lang = lang_of(user, admin=False)
        key, values = reason
        try:
            bot.send_message(user.telegram_id, f"⚠️ {t(key, lang, name=h(user.name), **values)}", reply_markup=keyboard([btn(t(T.refresh, lang), Cb.me), *app_row(t(T.my_page, lang), accounts.links(user).home)]))
        except Exception as e:
            logger.debug(f"tgbot: notify {user.uuid}: {e}")

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
