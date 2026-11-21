"""The admin's conversations with people (a key of their keyboard): the newest first, with what is unread and the
last message; one opens its whole history, by day, with Reply."""

from __future__ import annotations

import datetime

from telebot import types

from hiddifypanel.database import db
from hiddifypanel.models import User
from hiddifypanel.models.message import Conversation, Message, Sender

from .texts import T
from .ui import btn, Cb, Ctx, h, keyboard, route, Screen, Style, tg_time

PAGE_SIZE = 8
#: A history page stays well under Telegram's 4096 characters.
PAGE_CHARS = 3300
_MARK = {"fa": "‏", "ar": "‏", "ur": "‏", "ps": "‏"}


def _when(moment: datetime.datetime | None) -> str:
    if not moment:
        return ""
    if moment.date() == datetime.date.today():
        return tg_time(moment, "t", moment.strftime("%H:%M"))
    return tg_time(moment, "d", moment.strftime("%m-%d"))


def _iso(text: str) -> str:
    return f"⁨{text}⁩"


def _snippet(conv: Conversation) -> str:
    text = " ".join((conv.last_text or "").split())
    return text[:60] + ("…" if len(text) > 60 else "")


def chats_screen(ctx: Ctx, page: int) -> Screen:
    admin = ctx.admin
    assert admin
    query = Conversation.query.filter(Conversation.admin_id == admin.id)
    total = query.count()
    unread = sum(c.unread or 0 for c in query.filter(Conversation.unread > 0).all())
    pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = min(max(page, 0), pages - 1)
    convs = query.order_by(Conversation.last_at.desc()).offset(page * PAGE_SIZE).limit(PAGE_SIZE).all()
    mark = _MARK.get(ctx.lang, "‎")
    info = [ctx.tr(T.ch_count, n=total)] + ([ctx.tr(T.ch_unread, n=unread)] if unread else []) + ([f"{page + 1} / {pages}"] if pages > 1 else [])
    lines = [f"💬 <b>{ctx.tr(T.ch_title)}</b>", f"<i>{'  ·  '.join(info)}</i>", ""]
    if not convs:
        lines.append(f"<i>{ctx.tr(T.ch_empty)}</i>")
    rows = []
    for i, c in enumerate(convs, page * PAGE_SIZE + 1):
        dot = "🔵" if c.unread else "⚪️"
        new = f" · <b>{ctx.tr(T.ch_new, n=c.unread)}</b>" if c.unread else ""
        who = "↩️ " if c.last_sender == Sender.admin.value else ""
        lines.append(f"{mark}<b>{i}.</b> {dot} <b>{_iso(h(c.name or '—'))}</b>{new} · {_when(c.last_at)}")
        lines.append(f"{mark}<i>{who}{_iso(h(_snippet(c)))}</i>")
        rows.append(btn(f"{mark}{dot} {_iso((c.name or '—')[:22])}" + (f" ({c.unread})" if c.unread else ""), Cb.chat, c.id))
    grid = [rows[i : i + 2] for i in range(0, len(rows), 2)]
    nav = []
    if page > 0:
        nav.append(btn("‹", Cb.chats, page - 1))
    if page < pages - 1:
        nav.append(btn("›", Cb.chats, page + 1))
    body = "\n".join(lines[:3]) + ("\n<blockquote>" + "\n".join(lines[3:]) + "</blockquote>" if convs else "\n" + "\n".join(lines[3:]))
    return Screen(body, keyboard(*grid, nav, [btn(ctx.tr(T.back), Cb.back)]))


@route(Cb.chats, admin=True)
def show_chats(ctx: Ctx, args: list[str]) -> None:
    ctx.show(chats_screen(ctx, int(args[0]) if args and args[0].isdigit() else 0))
    ctx.toast()


def day_pages(items: list[tuple[datetime.date | None, str]], page_chars: int = PAGE_CHARS) -> list[str]:
    """(day, message) pairs, oldest first, as pages: each day's date, then one folded box (Telegram's expandable quote)
    that shows the day's first message and opens, with its arrow, to every message of that day. A day too long for one
    page goes on over the next with its date again. Used by the admin's and the person's history alike."""
    days: list[tuple[datetime.date | None, list[str]]] = []
    for day, bubble in items:
        if not days or days[-1][0] != day:
            days.append((day, []))
        days[-1][1].append(bubble)

    def block(day: datetime.date | None, bubbles: list[str]) -> str:
        head = f"📅 <b>{tg_time(day, 'wD', day.isoformat())}</b>" if day else "📅"
        return f"{head}\n<blockquote expandable>" + "\n\n".join(bubbles) + "</blockquote>"

    pages: list[str] = []
    page: list[str] = []
    size = 0
    for day, bubbles in days:
        chunk: list[str] = []
        for bubble in bubbles:
            if chunk and len(block(day, chunk + [bubble])) > page_chars:  # this day goes on over the next page
                page.append(block(day, chunk))
                pages.append("\n\n".join(page))
                page, size, chunk = [], 0, []
            chunk.append(bubble)
        text = block(day, chunk)
        if page and size + len(text) > page_chars:
            pages.append("\n\n".join(page))
            page, size = [], 0
        page.append(text)
        size += len(text) + 2
    if page:
        pages.append("\n\n".join(page))
    return pages


def conversation_pages(conv: Conversation, lang: str, tr) -> list[str]:
    """The conversation by day (``day_pages``), oldest first."""
    messages = [m for m in conv.messages if (m.text or "").strip() or m.kind in _KIND]
    return day_pages([(m.created_at.date() if m.created_at else None, _bubble(conv, m, tr)) for m in messages])


#: What happened to a free test, said in words (its text holds only numbers)
_KIND = {"request": T.ch_k_request, "granted": T.ch_k_granted, "declined": T.ch_k_declined}


def _bubble(conv: Conversation, m: Message, tr) -> str:
    if m.sender == Sender.admin.value:
        who = f"🛟 {tr(T.ch_you)}"
    elif m.sender == Sender.system.value:
        who = f"ℹ️ {tr(T.ch_system)}"
    else:
        who = f"🙋 {_iso(h(conv.name or '—'))}"
    kind = _KIND.get(m.kind)
    body = f"<i>{tr(kind)}</i>" if kind else h((m.text or "").strip())
    if len(body) > 600:
        body = body[:600] + "…"
    at = tg_time(m.created_at, "t", m.created_at.strftime("%H:%M")) if m.created_at else ""
    return f"<b>{who}</b> · {at}\n{body}"


def conversation_screen(ctx: Ctx, conv: Conversation, page: int) -> Screen:
    """Page 0 is the newest; older ones go back in time."""
    pages = conversation_pages(conv, ctx.lang, ctx.tr)
    account = User.by_uuid(conv.user_uuid) if conv.user_uuid else None
    who = f"💬 <b>{_iso(h(conv.name or '—'))}</b>" + (f"  ·  @{h(conv.username)}" if conv.username else "")
    if account is not None:
        who += f"\n👤 {_iso(h(account.name))}"
    rows: list[list[types.InlineKeyboardButton]] = []
    if not pages:
        text = f"{who}\n\n<i>{ctx.tr(T.hist_empty)}</i>"
    else:
        page = min(max(page, 0), len(pages) - 1)
        index = len(pages) - 1 - page
        head = f"{who}\n<i>{index + 1} / {len(pages)}</i>" if len(pages) > 1 else who
        text = f"{head}\n{pages[index]}"
        nav = []
        if index > 0:
            nav.append(btn(ctx.tr(T.hist_older), Cb.chat, conv.id, page + 1))
        if page > 0:
            nav.append(btn(ctx.tr(T.hist_newer), Cb.chat, conv.id, page - 1))
        rows.append(nav)
    actions = [btn(ctx.tr(T.reply), Cb.reply, conv.id, style=Style.primary)]
    if account is not None:
        actions.append(btn(ctx.tr(T.sp_account), Cb.card, account.id))
    rows += [actions, [btn(ctx.tr(T.back), Cb.back)]]
    return Screen(text, keyboard(*rows))


@route(Cb.chat, admin=True)
def show_conversation(ctx: Ctx, args: list[str]) -> None:
    from .free import _mine

    conv = _mine(ctx, args)
    if conv is None:
        ctx.toast(ctx.tr(T.gone), alert=True)
        return ctx.show(chats_screen(ctx, 0))
    if conv.unread:  # opened: read (the person sees 👀)
        conv.unread = 0
        db.session.commit()
        from . import support

        support.seen(conv)
    ctx.show(conversation_screen(ctx, conv, int(args[1]) if len(args) > 1 and args[1].isdigit() else 0))
    ctx.toast()
