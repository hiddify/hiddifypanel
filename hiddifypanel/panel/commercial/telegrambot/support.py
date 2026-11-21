"""Support inside the bot, private both ways: a person writes to their own support team (text, photos, files,
voice) and nobody else sees it; the team answers as "Support", never as its own account (text is sent by the bot,
media is copied, so no "forwarded from").

What the person sees:
- a support screen with the last messages as bubbles and where the conversation stands;
- "Write a message": Telegram's reply field with a hint;
- receipts as reactions on their own messages: 🕊 sent, 👀 seen by support, 👌 answered;
- "Support is typing…" (a message draft) while an admin writes the answer in Telegram.
"""

from __future__ import annotations

import datetime
import json
import random

from loguru import logger
from telebot import types

from hiddifypanel import free_test
from hiddifypanel.cache import redis_client
from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, User
from hiddifypanel.models.message import Conversation, Message, Sender

from . import bot
from .texts import T, t
from .ui import btn, Cb, Ctx, h, keyboard, lang_of, route, Screen, Style, tg_time

#: A message's receipt can still change this long after it was sent.
_PENDING_TTL = 7 * 24 * 3600
_PENDING = "tgbot:support:pending:{}"
SENT, SEEN, ANSWERED = "🕊", "👀", "👌"
#: The messages of a support chat in the person's chat (theirs and the bot's), so "End Chat" can clear them. Telegram
#: lets a bot delete messages for 48 hours.
_SESSION = "tgbot:support:session:{}"
_SESSION_TTL = 48 * 3600

#: What a non-text message is called in the inbox (its caption follows).
#: The media that can carry a caption (the others get "Support" in a line before them).
CAPTIONED = {"photo", "document", "voice", "video", "audio", "animation"}
MEDIA_LABEL = {"photo": "📷", "document": "📎", "voice": "🎤", "video": "🎬", "audio": "🎵", "sticker": "🙂", "video_note": "📹"}


# --------------------------------------------------------------------------- the chat's messages, to clear


def remember(chat_id: int, sent: object) -> None:
    """Keep a message (a Message, a MessageId or an id) of this support chat. Never raises."""
    message_id = sent if isinstance(sent, int) else getattr(sent, "message_id", None)
    if not message_id:
        return
    key = _SESSION.format(chat_id)
    try:
        redis_client.rpush(key, int(message_id))
        redis_client.ltrim(key, -300, -1)
        redis_client.expire(key, _SESSION_TTL)
    except Exception as e:
        logger.debug(f"tgbot support: message not kept: {e}")


def answer_buttons(lang: str) -> types.InlineKeyboardMarkup:
    """Under an answer from support: answer back, or end the chat (it is cleared from the person's chat)."""
    return keyboard([btn(t(T.sp_answer_back, lang), Cb.support_write), btn(t(T.sp_end, lang), Cb.support_end)])


@route(Cb.support_end, admin=False, anyone=True)
def end_chat(ctx: Ctx, _args: list[str]) -> None:
    """Clear this support chat's messages from the person's chat and show the menu. The inbox keeps everything."""
    key = _SESSION.format(ctx.chat_id)
    try:
        ids = {int(x) for x in (redis_client.lrange(key, 0, -1) or [])}
        redis_client.delete(key)
    except Exception:
        ids = set()
    if ctx.message_id:
        ids.add(int(ctx.message_id))
    ordered = sorted(ids)
    for i in range(0, len(ordered), 100):  # Telegram takes 100 at a time
        try:
            bot.delete_messages(ctx.chat_id, ordered[i : i + 100])
        except Exception as e:  # older than 48 hours, or already gone: one by one, what can go
            logger.debug(f"tgbot support: bulk delete failed: {e}")
            for message_id in ordered[i : i + 100]:
                try:
                    bot.delete_message(ctx.chat_id, message_id)
                except Exception:
                    pass
    ctx.state.update(awaiting=None)
    ctx.toast(ctx.tr(T.sp_ended))
    from .handlers import open_home

    # The keyboard came with one of the cleared messages (the line after writing): send it again
    open_home(ctx, keys=True)


# --------------------------------------------------------------------------- receipts


def _react(chat_id: int, message_id: int, emoji: str) -> bool:
    try:
        bot.set_message_reaction(chat_id, message_id, [types.ReactionTypeEmoji(emoji)])
        return True
    except Exception as e:
        logger.debug(f"tgbot support: no {emoji} on {chat_id}/{message_id}: {e}")
        return False


def sent(conv: Conversation, message: types.Message) -> bool:
    """The person's message reached support: 🕊, and it waits for 👀 and 👌. False when no reaction could be set."""
    ok = _react(message.chat.id, message.message_id, SENT)
    remember(message.chat.id, message.message_id)
    key = _PENDING.format(conv.id)
    try:
        redis_client.rpush(key, json.dumps([message.chat.id, message.message_id]))
        redis_client.ltrim(key, -20, -1)
        redis_client.expire(key, _PENDING_TTL)
    except Exception as e:
        logger.debug(f"tgbot support: receipt not kept: {e}")
    return ok


def _pending(conv: Conversation) -> list[tuple[int, int]]:
    try:
        raw = redis_client.lrange(_PENDING.format(conv.id), 0, -1) or []
    except Exception:
        return []
    out = []
    for item in raw:
        try:
            chat_id, message_id = json.loads(item)
            out.append((int(chat_id), int(message_id)))
        except (ValueError, TypeError):
            continue
    return out


def seen(conv: Conversation) -> None:
    """An admin opened the conversation (the inbox, or "Seen" in Telegram): 👀 on what waits."""
    for chat_id, message_id in _pending(conv):
        _react(chat_id, message_id, SEEN)


def answered(conv: Conversation) -> None:
    """An answer went out: 👌, and nothing waits any more."""
    for chat_id, message_id in _pending(conv):
        _react(chat_id, message_id, ANSWERED)
    try:
        redis_client.delete(_PENDING.format(conv.id))
    except Exception:
        pass


def typing(conv: Conversation, lang: str) -> None:
    """"Support is typing…" in the person's chat while an admin writes (a draft; it goes away by itself)."""
    try:
        bot.send_message_draft(conv.telegram_id, random.randint(1, 2**31 - 1), f"🛟 <i>{t(T.sp_typing, lang)}</i>", parse_mode="HTML")
    except Exception as e:
        logger.debug(f"tgbot support: no typing draft for {conv.telegram_id}: {e}")


# --------------------------------------------------------------------------- the person's screen


def status_line(conv: Conversation | None, lang: str) -> str:
    """Where the conversation stands, from the person's side."""
    if conv is None or not conv.messages:
        return f"💡 {t(T.sp_empty, lang)}"
    last = conv.messages[-1]
    if last.sender == Sender.admin.value:
        return f"✅ {t(T.sp_answered, lang)}"
    if not conv.unread:
        return f"👀 {t(T.sp_seen, lang)}"
    return f"⏳ {t(T.sp_waiting, lang)}"


def _day_items(messages: list[Message], lang: str) -> list[tuple[datetime.date | None, str]]:
    """(day, message) pairs for ``chats.day_pages``: who and when, then the text."""
    items = []
    for m in messages:
        who = f"🙋 {t(T.sp_you, lang)}" if m.sender == Sender.user.value else f"🛟 {t(T.msg_from, lang)}"
        body = h((m.text or "").strip())
        if len(body) > 600:
            body = body[:600] + "…"
        items.append((m.created_at.date() if m.created_at else None, f"<b>{who}</b> · {tg_time(m.created_at, 't', m.created_at.strftime('%H:%M')) if m.created_at else ''}\n{body}"))
    return items


def screen(ctx: Ctx, conv: Conversation | None) -> Screen:
    """The last day the person talked with support: its date, then one folded box (its first message; the arrow opens
    the whole day), like the history."""
    from .chats import day_pages

    lines = [f"💬 <b>{ctx.tr(T.sp_title)}</b>", f"<i>🔒 {ctx.tr(T.sp_private)}</i>", ""]
    messages = [m for m in (conv.messages if conv else []) if m.kind == "text" and (m.text or "").strip()]
    if messages:
        last = messages[-1].created_at.date() if messages[-1].created_at else None
        day = [m for m in messages if (m.created_at.date() if m.created_at else None) == last]
        lines += [day_pages(_day_items(day, ctx.lang), SCREEN_CHARS)[-1], ""]
    lines.append(status_line(conv, ctx.lang))
    return Screen(
        "\n".join(lines),
        keyboard(
            [btn(ctx.tr(T.sp_write), Cb.support_write, style=Style.primary)],
            [btn(ctx.tr(T.doctor), Cb.doctor), btn(ctx.tr(T.back), Cb.back if ctx.user else Cb.home)],
        ),
    )


@route(Cb.support, admin=False, anyone=True)
def show_support(ctx: Ctx, args: list[str]) -> None:
    conv = free_test.current_conversation(ctx.chat_id, ctx.user)
    if conv is None:
        return ctx.toast(ctx.tr(T.sp_nobody), alert=True)
    if conv.id is None:  # made just now for this account: kept, so the screen and the receipts have it
        db.session.commit()
    before = ctx.state.get("upanel") if args[:1] == ["h"] else None
    ctx.show(screen(ctx, conv))
    if args[:1] == ["h"]:  # from "how to write": that line is the screen now; what was typed and the old screen go
        from .handlers import _delete

        for old in (args[1] if len(args) > 1 and args[1].isdigit() else None, before):
            if old and int(old) != ctx.message_id:
                _delete(ctx.chat_id, int(old))
    remember(ctx.chat_id, ctx.message_id)
    ctx.toast()


@route(Cb.support_write, admin=False, anyone=True)
def ask_message(ctx: Ctx, _args: list[str]) -> None:
    """A small keyboard (only Cancel) under the message field, with a hint in it: what is sent next goes to support
    (text, photo, file, voice). No reply quote on the person's message."""
    ctx.toast()
    ctx.state.update(awaiting="support")
    from . import menukey

    remember(ctx.chat_id, menukey.prompt(ctx, f"✍️ {ctx.tr(T.sp_write_hint)}", ctx.tr(T.sp_placeholder)))


def writing(ctx: Ctx) -> bool:
    return ctx.state.get("awaiting") == "support"


def cancelled(ctx: Ctx, text: str) -> bool:
    """"Cancel" pressed on the writing keyboard: nothing is sent, and the Menu key comes back."""
    if not writing(ctx) or text.strip() != ctx.tr(T.sp_cancel):
        return False
    ctx.state.update(awaiting=None)
    from . import menukey

    menukey._forget_cancel(ctx.chat_id)
    remember(ctx.chat_id, bot.send_message(ctx.chat_id, f"✖️ {ctx.tr(T.sp_cancelled)}", reply_markup=menukey.keyboard_for(ctx.lang, person=ctx.user is not None)))
    return True


def done_writing(ctx: Ctx) -> None:
    """After the message: the Menu key comes back, with one line saying where the answer will come."""
    if not writing(ctx):
        return
    ctx.state.update(awaiting=None)
    try:
        from . import menukey

        menukey._forget_cancel(ctx.chat_id)
        remember(ctx.chat_id, bot.send_message(ctx.chat_id, f"✉️ {ctx.tr(T.sp_delivered)}", reply_markup=menukey.keyboard_for(ctx.lang, person=ctx.user is not None)))
    except Exception as e:
        logger.debug(f"tgbot support: keyboard not removed: {e}")


# --------------------------------------------------------------------------- the person's chat history

#: The support screen's last day stays well under Telegram's 4096 characters (its header and buttons around it)
SCREEN_CHARS = 3000
#: A history page stays well under Telegram's 4096 characters.
HISTORY_PAGE_CHARS = 3300


def history_pages(chat_id: int, lang: str) -> list[str]:
    """Every message this chat had with support (all its conversations), oldest first: by day, each day one folded
    box that opens with its first message (the same as the admin's history)."""
    from .chats import day_pages

    convs = Conversation.query.filter(Conversation.telegram_id == chat_id).all()
    messages = sorted((m for c in convs for m in c.messages if m.kind == "text" and (m.text or "").strip()), key=lambda m: (m.created_at or datetime.datetime.min, m.id))
    return day_pages(_day_items(messages, lang), HISTORY_PAGE_CHARS)


def history_screen(ctx: Ctx, page: int) -> Screen:
    """Page 0 is the newest; older ones go back in time."""
    pages = history_pages(ctx.chat_id, ctx.lang)
    title = f"🗂 <b>{ctx.tr(T.hist_title)}</b>"
    if not pages:
        return Screen(f"{title}\n\n<i>{ctx.tr(T.hist_empty)}</i>", keyboard([btn(ctx.tr(T.support), Cb.support), btn(ctx.tr(T.back), Cb.back)]))
    page = min(max(page, 0), len(pages) - 1)
    index = len(pages) - 1 - page
    head = f"{title}  ·  {index + 1}/{len(pages)}" if len(pages) > 1 else title
    nav = []
    if index > 0:
        nav.append(btn(ctx.tr(T.hist_older), Cb.history, page + 1))
    if page > 0:
        nav.append(btn(ctx.tr(T.hist_newer), Cb.history, page - 1))
    return Screen(f"{head}\n{pages[index]}", keyboard(nav, [btn(ctx.tr(T.support), Cb.support), btn(ctx.tr(T.back), Cb.back)]))


@route(Cb.history, admin=False, anyone=True)
def show_history(ctx: Ctx, args: list[str]) -> None:
    page = int(args[0]) if args and args[0].isdigit() else 0
    ctx.show(history_screen(ctx, page))
    ctx.toast()


# --------------------------------------------------------------------------- media from the person


def _label(message: types.Message) -> str:
    icon = MEDIA_LABEL.get(message.content_type, "📎")
    caption = (message.caption or "").strip()
    return f"{icon} {caption}" if caption else icon


def relay_media(ctx: Ctx, message: types.Message) -> bool:
    """A photo, file or voice from the person goes to their support (copied, so it carries no "forwarded from").
    False when they talk to nobody."""
    from .free import RATE_PER_MINUTE, _person, _who

    if not writing(ctx):  # sent anywhere else: not for support (the caller says how to write to it)
        return False
    conv = free_test.current_conversation(ctx.chat_id, ctx.user)
    if conv is None:
        return False
    key = f"tgbot:msg-rate:{ctx.chat_id}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, 60)
    if count > RATE_PER_MINUTE:
        db.session.rollback()
        bot.send_message(ctx.chat_id, f"⏳ {ctx.tr(T.msg_slow)}")
        return True
    name, username = _person(message.from_user)
    if name:
        conv.name = name[:128]
    if username:
        conv.username = username[:64]
    label = _label(message)
    free_test.add_message(conv, Sender.user, label[: free_test.MAX_TEXT])
    db.session.commit()
    admin = AdminUser.by_id(conv.admin_id)
    if admin is not None and admin.telegram_id:
        lang = lang_of(admin, admin=True)
        try:
            if message.content_type in CAPTIONED:  # one message, like a text notice: who, the caption quoted
                caption = notice(conv, (message.caption or "").strip() or label, lang)[:1024]
                bot.copy_message(admin.telegram_id, ctx.chat_id, message.message_id, caption=caption, parse_mode="HTML", reply_markup=admin_buttons(conv, lang))
            else:
                bot.send_message(admin.telegram_id, f"💬 <b>{_who(conv)}</b>")
                bot.copy_message(admin.telegram_id, ctx.chat_id, message.message_id, reply_markup=admin_buttons(conv, lang))
        except Exception as e:
            logger.debug(f"tgbot support: media not relayed to admin {admin.id}: {e}")
    sent(conv, message)
    done_writing(ctx)
    return True


# --------------------------------------------------------------------------- the admin


def admin_buttons(conv: Conversation, lang: str) -> types.InlineKeyboardMarkup:
    row = [btn(t(T.reply, lang), Cb.reply, conv.id, style=Style.primary)]
    if conv.user_uuid and (account := User.by_uuid(conv.user_uuid)) is not None:
        row.append(btn(t(T.sp_account, lang), Cb.card, account.id))
    return keyboard(row, [btn(t(T.sp_mark_seen, lang), Cb.support_seen, conv.id), btn(t(T.sp_later, lang), Cb.support_later, conv.id)])


def notice(conv: Conversation, text: str, lang: str) -> str:
    """The admin's notice of a new message: who, and the message in a quote."""
    from .free import _who

    account = User.by_uuid(conv.user_uuid) if conv.user_uuid else None
    who = _who(conv) + (f"  ·  👤 {h(account.name)}" if account is not None else "")
    return f"💬 <b>{t(T.sp_new, lang)}</b>\n{who}\n\n<blockquote>{h(text)}</blockquote>"


@route(Cb.support_later, admin=True)
def read_later(ctx: Ctx, args: list[str]) -> None:
    """The admin reads it later: the notice leaves the chat, the menu comes, and the message stays unread (🔵 in
    Support History, where it is read)."""
    from .handlers import _delete, open_home
    from . import nav

    ctx.toast(ctx.tr(T.sp_later_done))
    if ctx.message_id:
        _delete(ctx.chat_id, ctx.message_id)
    nav.reset(ctx)
    open_home(ctx)


@route(Cb.support_seen, admin=True)
def mark_seen(ctx: Ctx, args: list[str]) -> None:
    from .free import _mine

    conv = _mine(ctx, args)
    if conv is None:
        return ctx.toast(ctx.tr(T.gone), alert=True)
    conv.unread = 0
    db.session.commit()
    seen(conv)
    ctx.toast(ctx.tr(T.sp_marked_seen))
    if not ctx.message_id:
        return
    only_reply = keyboard([btn(ctx.tr(T.reply), Cb.reply, conv.id, style=Style.primary)])
    try:  # the notice keeps only Reply: a text notice (its buttons inside it) is written again
        bot.edit_message_text(notice(conv, conv.last_text or "", ctx.lang), ctx.chat_id, ctx.message_id, reply_markup=only_reply)
    except Exception:
        try:  # a photo or file: only its keyboard changes
            bot.edit_message_reply_markup(ctx.chat_id, ctx.message_id, reply_markup=only_reply)
        except Exception as e:
            logger.debug(f"tgbot support: notice not updated: {e}")


def admin_media(ctx: Ctx, message: types.Message) -> bool:
    """A photo, file or voice an admin sends after pressing Reply goes to the person, copied (no trace of the
    admin's account). False when the admin is not answering anyone."""
    if ctx.state.get("awaiting") != "reply":
        return False
    from . import menukey

    conv = db.session.get(Conversation, int(ctx.state.get("reply_to") or 0))
    prompt = ctx.state.get("reply_prompt")
    ctx.state.update(awaiting=None, reply_to=None, reply_prompt=None)
    if prompt:  # the reply field's hint is done
        try:
            bot.delete_message(ctx.chat_id, int(prompt))
        except Exception:
            pass
    if conv is None or ctx.admin is None or conv.admin_id != ctx.admin.id:
        menukey.tell(ctx, f"⚠️ {ctx.tr(T.gone)}")
        return True
    from . import topics
    from .free import _conv_lang

    lang = _conv_lang(conv)
    answer_button = answer_buttons(lang)
    head = f"🛟 <b>{t(T.msg_from, lang)}</b>"
    try:
        if message.content_type in CAPTIONED:  # one message: the media, "Support" and the admin's own caption
            caption = (message.caption or "").strip()
            text = f"{head}\n\n{h(caption)}" if caption else head
            remember(conv.telegram_id, topics.deliver(conv.telegram_id, "support", lang, lambda x: bot.copy_message(conv.telegram_id, ctx.chat_id, message.message_id, caption=text[:1024], parse_mode="HTML", reply_markup=answer_button, **x)))
        else:  # stickers and round videos take no caption: "Support" just before
            remember(conv.telegram_id, topics.deliver(conv.telegram_id, "support", lang, lambda x: bot.send_message(conv.telegram_id, head, **x)))
            remember(conv.telegram_id, topics.deliver(conv.telegram_id, "support", lang, lambda x: bot.copy_message(conv.telegram_id, ctx.chat_id, message.message_id, reply_markup=answer_button, **x)))
    except Exception as e:
        logger.info(f"tgbot support: media not delivered to {conv.telegram_id}: {e}")
        menukey.tell(ctx, f"⚠️ {ctx.tr(T.reply_failed, name=h(conv.name))}")
        return True
    free_test.add_message(conv, Sender.admin, _label(message)[: free_test.MAX_TEXT])
    conv.unread = 0
    db.session.commit()
    answered(conv)
    menukey.tell(ctx, f"✅ {ctx.tr(T.reply_sent, name=h(conv.name))}")
    return True
