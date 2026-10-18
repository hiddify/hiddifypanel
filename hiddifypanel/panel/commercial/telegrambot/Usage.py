"""The account card for messages the panel sends on its own (broadcasts, the send_msg API, usage alerts)."""

from __future__ import annotations

from telebot import types

from hiddifypanel.models import Domain, User

from .texts import T, t
from . import accounts
from .ui import Cb, app_row, btn, keyboard, lang_of
from .user import account_card


def get_usage_msg(uuid: str, domain: Domain | None = None) -> str:
    user = User.by_uuid(uuid)
    if not user:
        return ""
    return account_card(user, lang_of(user, admin=False))


def user_keyboard(uuid: str) -> types.InlineKeyboardMarkup:
    user = User.by_uuid(uuid)
    lang = lang_of(user, admin=False)
    rows = [[btn(t(T.refresh, lang), Cb.me), btn(t(T.links, lang), Cb.me_links)]]
    if user:
        rows.append(app_row(t(T.my_page, lang), accounts.links(user).home))
    return keyboard(*rows)
