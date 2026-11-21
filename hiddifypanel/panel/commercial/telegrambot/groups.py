"""The bot in a group: /me answers only the person who asked, with an ephemeral message (Bot API 10.2+) the others
do not see, so nobody's links or usage show in the group. Everything else in a group is left alone."""

from __future__ import annotations

from loguru import logger
from telebot import types

from hiddifypanel.models import AdminUser, User

from . import accounts, bot
from .texts import T, t
from .ui import BRAND, keyboard, lang_of, url_btn

GROUPS = ["group", "supergroup"]


def _bot_link(start: str = "") -> str:
    name = bot.username or ""
    return f"https://t.me/{name}" + (f"?start={start}" if start else "")


def answer(message: types.Message) -> None:
    """The asker's account card, for their eyes only; someone the bot does not know is shown the way in."""
    from .user import account_card

    sender = message.from_user
    if sender is None:
        return
    user = User.query.filter(User.telegram_id == sender.id, User.deleted.is_(False)).first()
    admin = None if user else AdminUser.query.filter(AdminUser.telegram_id == sender.id, AdminUser.deleted.is_(False)).first()
    lang = lang_of(user or admin, admin=admin is not None, telegram=getattr(sender, "language_code", None))
    if user is not None:
        links = accounts.links(user)
        text = account_card(user, lang)
        markup = keyboard([url_btn(BRAND, links.page), url_btn(t(T.grp_open_bot, lang), _bot_link())])
    else:
        text = f"👋 {t(T.grp_not_linked, lang)}"
        markup = keyboard([url_btn(t(T.grp_open_bot, lang), _bot_link("start"))])
    bot.send_message(
        message.chat.id,
        text,
        reply_markup=markup,
        link_preview_options=types.LinkPreviewOptions(is_disabled=True),
        ephemeral_message_parameters=types.EphemeralMessageParameters(receiver_user_id=sender.id),
    )
    # The command itself is noise in the group: removed when the bot may (it is an admin there)
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass


@bot.message_handler(commands=["me", "start", "menu"], chat_types=GROUPS)
def on_group_command(message: types.Message) -> None:
    try:
        answer(message)
    except Exception as e:
        logger.info(f"tgbot groups: /me not answered in {message.chat.id}: {e}")
