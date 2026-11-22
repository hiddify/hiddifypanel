"""The admin side: home, the users list (filters, search, pages), the user card and its actions, creating one
or many users, and backups. Everything happens in one message that the buttons edit."""

from __future__ import annotations

import datetime
import io
from collections.abc import Sequence

from loguru import logger
from telebot import types

from hiddifypanel.database import db
from hiddifypanel.models import AdminMode, AdminUser, User

from . import accounts, bot
from .accounts import Filter, Sort
from .texts import T
from .ui import RULE, SELECTED, ago, ago_html, background, bar, btn, Cb, Ctx, fmt_gb, h, keyboard, off_btn, route, Screen, send_card, Style, with_retry
from .user import account_card, links_screen, share_screen

PAGE_SIZE = 8
GB_CHOICES = (1, 5, 10, 20, 30, 50, 100, 200)
DAY_CHOICES = (1, 7, 15, 30, 60, 90, 180, 365)
COUNT_CHOICES = (1, 2, 5, 10, 20, 50, 100)
ADD_DAY_CHOICES = (1, 7, 15, 30, 60, 90)
ADD_GB_CHOICES = (1, 5, 10, 20, 50, 100)

_FILTER_TEXT: dict[Filter, T] = {Filter.all: T.f_all, Filter.active: T.f_active, Filter.expiring: T.f_expiring, Filter.ended: T.f_ended, Filter.online: T.f_online}


def _int(args: list[str], i: int, default: int = 0) -> int:
    try:
        return int(args[i])
    except (IndexError, ValueError):
        return default


# --------------------------------------------------------------------------- home


def home_screen(ctx: Ctx) -> Screen:
    admin = ctx.admin
    assert admin
    counts = accounts.summary(admin)
    text = "\n".join(
        [
            ctx.tr(T.admin_hello, name=h(admin.name)),
            RULE,
            ctx.tr(T.admin_summary, total=counts.total, active=counts.active, online=counts.online, expiring=counts.expiring),
        ]
    )
    # Every action is a key of the keyboard by the message box (menukey.ADMIN_ROWS); the panel app is the menu button
    rows: list[Sequence[types.InlineKeyboardButton]] = [[btn(ctx.tr(T.refresh), Cb.home)]]
    return Screen(text, keyboard(*rows))


@route(Cb.home, admin=True)
def show_home(ctx: Ctx, _args: list[str]) -> None:
    ctx.state.update(awaiting=None)
    ctx.show(home_screen(ctx))
    ctx.toast()


# --------------------------------------------------------------------------- users list


#: The list's tabs: an icon and how many users each keeps (the same icons as the admin's home).
_FILTER_ICON: dict[Filter, str] = {Filter.all: "👥", Filter.active: "🟢", Filter.expiring: "⏳", Filter.ended: "🔴", Filter.online: "⚡️"}
_SORT_TEXT: dict[Sort, T] = {Sort.new: T.sort_new, Sort.usage: T.sort_usage, Sort.days: T.sort_days, Sort.seen: T.sort_seen, Sort.name: T.sort_name}
_LIST_BAR = 8


_RTL = {"fa", "ar", "ur", "ps"}


def _dir(lang: str) -> str:
    """An invisible mark that sets a line's direction (the chat's language), so every row lines up the same way: the
    icon always on the same side, whatever script the name is in (Telegram guesses each line's direction from its
    first letter otherwise)."""
    return "\u200f" if lang in _RTL else "\u200e"


def _iso(text: str) -> str:
    """A name in its own direction: a Persian name in an English line (or the other way) keeps its place."""
    return f"\u2068{text}\u2069"


def _user_lines(ctx: Ctx, users: list[User], start: int, sort: Sort = Sort.new) -> str:
    """Each user in two lines: number, state and name; then the data bar, data and days (and when last seen)."""
    out = []
    for i, u in enumerate(users, start + 1):
        st = accounts.status(u)
        online = accounts.is_online(u)
        if not u.enable:
            days = ctx.tr(T.lst_off)
        elif st is accounts.Status.expired:
            days = ctx.tr(T.lst_ended)
        elif u.start_date is None:
            days = ctx.tr(T.lst_not_started)
        else:
            days = ctx.tr(T.lst_left, n=u.remaining_days)
        used = f"{u.current_usage_GB:.1f}/{u.usage_limit_GB:g} {ctx.tr(T.gb)}"
        seen = f" · 🕒 {ago_html(u.last_online, ctx.lang)}" if sort is Sort.seen and not online else ""
        head = f"<b>{i}.</b> {accounts.STATUS_ICON[st]} <b>{_iso(h((u.name or '-')[:32]))}</b>" + (" ⚡️" if online else "")
        mark = _dir(ctx.lang)
        out.append(f"{mark}{head}\n{mark}<code>{bar(accounts.usage_ratio(u), _LIST_BAR)}</code> {used} · {days}{seen}")
    return "\n".join(out)


def _user_grid(ctx: Ctx, users: list[User]) -> list[list[types.InlineKeyboardButton]]:
    """A button per user, two to a row, in the order of the lines above; every one in the chat's direction. The
    button's colour is the account's state (green active, red ended, soft grey off), ⚡️ when online."""
    mark = _dir(ctx.lang)
    buttons = [
        btn(f"{mark}{_iso((u.name or '-')[:22])}" + (" ⚡️" if accounts.is_online(u) else ""), Cb.card, u.id, style=_STATE_STYLE.get(accounts.status(u)))
        for u in users
    ]
    return [buttons[i : i + 2] for i in range(0, len(buttons), 2)]


#: A user's button colour by the account's state (off: no colour, the soft grey)
_STATE_STYLE = {accounts.Status.active: Style.success, accounts.Status.expired: Style.danger, accounts.Status.no_data: Style.danger}


def _pager(kind: Cb, prefix: list[object], page: int, pages: int, suffix: list[object] | None = None) -> list[types.InlineKeyboardButton]:
    if pages <= 1:
        return []
    tail = suffix or []
    # No arrow where there is no page to go to (a blank button is refused by Telegram)
    row = []
    if page > 1 and pages > 3:
        row.append(btn("«", kind, *prefix, 0, *tail))
    if page > 0:
        row.append(btn("‹", kind, *prefix, page - 1, *tail))
    row.append(off_btn(f"{page + 1} / {pages}", otherwise=btn(f"{page + 1} / {pages}", kind, *prefix, page, *tail)))  # the page shown
    if page < pages - 1:
        row.append(btn("›", kind, *prefix, page + 1, *tail))
    if page < pages - 2 and pages > 3:
        row.append(btn("»", kind, *prefix, pages - 1, *tail))
    return row


def _list_text(ctx: Ctx, title: str, found: accounts.Page, sort: Sort | None) -> str:
    lines = [title]
    info = [ctx.tr(T.users_count, n=found.total)]
    if sort is not None:
        info.append(ctx.tr(T.lst_sorted, by=ctx.tr(_SORT_TEXT[sort])))
    if found.pages > 1:
        info.append(ctx.tr(T.lst_page, page=found.page + 1, pages=found.pages))
    lines.append(f"<i>{'  ·  '.join(info)}</i>")
    if found.total:
        lines += ["", "<blockquote>" + _user_lines(ctx, found.users, found.page * PAGE_SIZE, sort or Sort.new) + "</blockquote>", f"<i>{ctx.tr(T.lst_hint)}</i>"]
    else:
        lines += ["", f"<i>{ctx.tr(T.users_empty)}</i>"]
    return "\n".join(lines)


def users_screen(ctx: Ctx, f: Filter, page: int, sort: Sort = Sort.new) -> Screen:
    admin = ctx.admin
    assert admin
    found = accounts.list_page(admin, f, sort, page, PAGE_SIZE)
    page = found.page
    ctx.state.update(back=[Cb.users.value, f.value, page, sort.value])
    n = accounts.counts(admin)
    # The tabs: an icon and a count each, the chosen one ticked (a segmented control)
    tabs = [
        off_btn(SELECTED + f"{_FILTER_ICON[x]} {n[x]}", otherwise=btn(SELECTED + f"{_FILTER_ICON[x]} {n[x]}", Cb.users, x.value, 0, sort.value)) if x is f else btn(f"{_FILTER_ICON[x]} {n[x]}", Cb.users, x.value, 0, sort.value)
        for x in Filter
    ]
    sorts = list(Sort)
    after = sorts[(sorts.index(sort) + 1) % len(sorts)]
    title = f"👥 <b>{ctx.tr(T.users_title)}</b>  ·  {_FILTER_ICON[f]} {ctx.tr(_FILTER_TEXT[f])}"
    return Screen(
        _list_text(ctx, title, found, sort),
        keyboard(
            tabs,
            *_user_grid(ctx, found.users),
            _pager(Cb.users, [f.value], page, found.pages, [sort.value]),
            [btn(ctx.tr(T.search), Cb.search_ask), btn(ctx.tr(T.sort_by, by=ctx.tr(_SORT_TEXT[after])), Cb.users, f.value, 0, after.value)],
            _advanced_row(ctx),
            [btn(ctx.tr(T.back), Cb.back)],
        ),
    )


def _advanced_row(ctx: Ctx) -> list:
    """Bulk actions and the admins (Advanced)."""
    from . import admins, bulk

    row = bulk.list_row(ctx)
    if admins.allowed(ctx):
        row.append(btn(ctx.tr(T.am_title), Cb.admins))
    return row


@route(Cb.users, admin=True)
def show_users(ctx: Ctx, args: list[str]) -> None:
    try:
        f = Filter(args[0])
    except (IndexError, ValueError):
        f = Filter.all
    try:
        sort = Sort(args[2])
    except (IndexError, ValueError):
        sort = Sort.new
    ctx.show(users_screen(ctx, f, _int(args, 1), sort))
    ctx.toast()


@route(Cb.search_ask, admin=True)
def ask_search(ctx: Ctx, _args: list[str]) -> None:
    ctx.state.update(awaiting="search")
    ctx.show(Screen(f"🔍 <b>{ctx.tr(T.search)}</b>\n\n{ctx.tr(T.search_prompt)}", keyboard([_back_btn(ctx, T.cancel)])))
    ctx.toast()


def search_screen(ctx: Ctx, query: str, page: int) -> Screen:
    admin = ctx.admin
    assert admin
    found = accounts.search_page(admin, query, page, PAGE_SIZE)
    if found.total == 1 and page == 0:
        return card_screen(ctx, found.users[0])
    page, pages = found.page, found.pages
    ctx.state.update(back=[Cb.search.value, page], query=query)
    return Screen(
        _list_text(ctx, f"🔍 <b>{ctx.tr(T.search_results, q=h(query))}</b>", found, None),
        keyboard(
            *_user_grid(ctx, found.users),
            _pager(Cb.search, [], page, pages),
            [btn(ctx.tr(T.search), Cb.search_ask), btn(ctx.tr(T.search_clear), Cb.users, Filter.all.value, 0)],
            [btn(ctx.tr(T.back), Cb.back)],
        ),
    )


@route(Cb.search, admin=True)
def show_search(ctx: Ctx, args: list[str]) -> None:
    ctx.show(search_screen(ctx, str(ctx.state.get("query") or ""), _int(args, 0)))
    ctx.toast()


def _back(ctx: Ctx) -> tuple[Cb, list[str]]:
    """Where "back" from a card goes: the list or search page it was opened from."""
    back = ctx.state.get("back")
    if isinstance(back, list) and back and back[0] in {Cb.users.value, Cb.search.value}:
        return Cb(back[0]), [str(a) for a in back[1:]]
    return Cb.users, [Filter.all.value, "0"]


def _back_btn(ctx: Ctx, label: T = T.back) -> types.InlineKeyboardButton:
    kind, args = _back(ctx)
    return btn(ctx.tr(label), kind, *args)


def _go_back(ctx: Ctx) -> None:
    kind, args = _back(ctx)
    if kind is Cb.search:
        ctx.show(search_screen(ctx, str(ctx.state.get("query") or ""), _int(args, 0)))
    else:
        show_users(ctx, args)


# --------------------------------------------------------------------------- user card


def card_screen(ctx: Ctx, user: User, note: str | None = None) -> Screen:
    owner = AdminUser.by_id(user.added_by) if user.added_by else None
    lines = [account_card(user, ctx.lang)]
    if owner and ctx.admin and owner.id != ctx.admin.id:
        lines.append(f"🧑‍💼 {ctx.tr(T.owner)}  ·  {h(owner.name)}")
    if user.comment:
        lines.append(f"💬 <i>{h(user.comment)}</i>")
    if note:
        lines += ["", f"✅ <i>{h(note)}</i>"]
    uid = user.id
    toggle = btn(ctx.tr(T.disable), Cb.act, uid, "off", style=Style.danger) if user.enable else btn(ctx.tr(T.enable), Cb.act, uid, "on", style=Style.success)
    return Screen(
        "\n".join(lines),
        keyboard(
            [btn(ctx.tr(T.links), Cb.links, uid), btn(ctx.tr(T.qr), Cb.qr, uid)],
            [btn(ctx.tr(T.chart), Cb.chart, uid)],
            [btn(ctx.tr(T.add_days), Cb.act, uid, "days"), btn(ctx.tr(T.add_gb), Cb.act, uid, "gb")],
            [btn(ctx.tr(T.renew), Cb.act, uid, "renew", style=Style.success), btn(ctx.tr(T.reset_usage), Cb.act, uid, "reset")],
            [toggle, btn(ctx.tr(T.delete), Cb.act, uid, "del", style=Style.danger)],
            [btn(ctx.tr(T.back), Cb.back), btn(ctx.tr(T.refresh), Cb.card, uid)],
        ),
    )


def _visible_user(ctx: Ctx, args: list[str]) -> User | None:
    assert ctx.admin
    user = accounts.get_visible(ctx.admin, _int(args, 0))
    if user is None:
        ctx.toast(ctx.tr(T.gone), alert=True)
        ctx.show(users_screen(ctx, Filter.all, 0))
    return user


@route(Cb.card, admin=True)
def show_card(ctx: Ctx, args: list[str]) -> None:
    if user := _visible_user(ctx, args):
        ctx.show(card_screen(ctx, user))
        ctx.toast()


@route(Cb.links, admin=True)
def show_links(ctx: Ctx, args: list[str]) -> None:
    if user := _visible_user(ctx, args):
        ctx.show(links_screen(user, ctx.lang, [btn(ctx.tr(T.qr), Cb.qr, user.id)], [btn(ctx.tr(T.back), Cb.back)]))
        ctx.toast()


@route(Cb.qr, admin=True)
def send_share_card(ctx: Ctx, args: list[str]) -> None:
    """The user's card as a new photo message, ready to forward to them."""
    if user := _visible_user(ctx, args):
        ctx.toast()
        send_card(ctx.chat_id, share_screen(ctx.lang, user))


@route(Cb.share, admin=True)
def refresh_share_card(ctx: Ctx, args: list[str]) -> None:
    if user := _visible_user(ctx, args):
        ctx.show(share_screen(ctx.lang, user))
        ctx.toast(ctx.tr(T.updated))


def _choices(ctx: Ctx, user: User, action: str, values: tuple[int, ...], unit: str) -> types.InlineKeyboardMarkup:
    buttons = [btn(f"+{v} {unit}", Cb.act, user.id, action, v) for v in values]
    return keyboard(buttons[:3], buttons[3:], [btn(ctx.tr(T.back), Cb.card, user.id)])


@route(Cb.act, admin=True)
def user_action(ctx: Ctx, args: list[str]) -> None:
    user = _visible_user(ctx, args)
    if user is None:
        return
    action = args[1] if len(args) > 1 else ""
    value = _int(args, 2)
    if accounts.is_read_only():
        ctx.toast(ctx.tr(T.read_only_node), alert=True)
        return
    head = f"👤 <b>{h(user.name)}</b>\n{RULE}\n"
    note: str | None = None
    match action, value:
        case "days", 0:
            ctx.show(Screen(head + ctx.tr(T.pick_days), _choices(ctx, user, "days", ADD_DAY_CHOICES, ctx.tr(T.unit_d))))
            return ctx.toast()
        case "gb", 0:
            ctx.show(Screen(head + ctx.tr(T.pick_gb), _choices(ctx, user, "gb", ADD_GB_CHOICES, ctx.tr(T.gb))))
            return ctx.toast()
        case "del", 0:
            ctx.show(Screen(head + ctx.tr(T.delete_confirm), keyboard([btn(ctx.tr(T.delete), Cb.act, user.id, "del", 1, style=Style.danger), btn(ctx.tr(T.cancel), Cb.card, user.id)])))
            return ctx.toast()
        case "del", _:
            if User.query.filter(User.deleted.is_(False)).count() <= 1:
                return ctx.toast(ctx.tr(T.last_user), alert=True)
            name = user.name
            accounts.remove(user)
            ctx.toast(ctx.tr(T.deleted, name=name))
            return _go_back(ctx)
        case "days", days:
            accounts.add_days(user, days)
            note = ctx.tr(T.added_days, n=days)
        case "gb", gb:
            accounts.add_gb(user, gb)
            note = ctx.tr(T.added_gb, n=gb)
        case "renew", _:
            # Renewing turns a disabled user on: the same active-user limit as "on"
            assert ctx.admin
            if not user.enable and not ctx.admin.can_activate_more_users():
                return ctx.toast(ctx.tr(T.limit_reached), alert=True)
            accounts.renew(user)
            note = ctx.tr(T.renewed)
        case "reset", _:
            user.reset_usage()
            note = ctx.tr(T.usage_reset)
        case "on", _:
            assert ctx.admin
            if not ctx.admin.can_activate_more_users():
                return ctx.toast(ctx.tr(T.limit_reached), alert=True)
            user.enable = True
            note = ctx.tr(T.enabled)
        case "off", _:
            user.enable = False
            note = ctx.tr(T.disabled)
        case _:
            return ctx.toast(ctx.tr(T.unknown))
    db.session.commit()
    accounts.apply([user])
    ctx.toast(note)
    ctx.show(card_screen(ctx, user, note))


# --------------------------------------------------------------------------- create users


def _default_name(admin: AdminUser) -> str:
    return f"{admin.name or 'tg'} {datetime.date.today():%m-%d}"


#: The most users made at once (a custom count)
MAX_BATCH = 100
#: Quick picks on the "how many" question
COUNT_PICKS = (5, 10, 20, 50)


def names_preview(name: str, count: int) -> str:
    """How the users will be called: NAME, or NAME-01 … NAME-10."""
    if count <= 1:
        return name
    w = max(2, len(str(count)))
    return f"{name}-{1:0{w}d}, {name}-{2:0{w}d} … {name}-{count:0{w}d}" if count > 2 else f"{name}-{1:0{w}d}, {name}-{2:0{w}d}"


def new_screen(ctx: Ctx, gb: int, days: int, count: int) -> Screen:
    """One step at a time: one user or how many, then the data, the days, (for many) their name, then Create."""
    admin = ctx.admin
    assert admin
    head = f"➕ <b>{ctx.tr(T.new_title)}</b>\n{RULE}\n"
    if not count:
        return Screen(
            f"{head}{ctx.tr(T.new_how)}",
            keyboard([btn(ctx.tr(T.new_one), Cb.new, 0, 0, 1, style=Style.success)], [btn(ctx.tr(T.new_many), Cb.new_count)], [btn(ctx.tr(T.back), Cb.back)]),
        )
    name = str(ctx.state.get("new_name") or _default_name(admin))
    summary = ctx.tr(
        T.new_summary,
        gb=fmt_gb(gb, ctx.lang) if gb else "—",
        days=f"{days} {ctx.tr(T.unit_d)}" if days else "—",
        count=count,
        name=h(names_preview(name, count)) if ctx.state.get("new_name") or count == 1 else "—",
    )
    text = f"{head}{summary}\n\n"
    rows: list[Sequence[types.InlineKeyboardButton]] = []
    if not gb:
        text += ctx.tr(T.new_gb)
        b = [btn(f"{v} {ctx.tr(T.gb)}", Cb.new, v, days, count) for v in GB_CHOICES]
        rows += [b[:4], b[4:], [btn(ctx.tr(T.back), Cb.new, 0, 0, 0)]]
    elif not days:
        text += ctx.tr(T.new_days)
        b = [btn(f"{v} {ctx.tr(T.unit_d)}", Cb.new, gb, v, count) for v in DAY_CHOICES]
        rows += [b[:4], b[4:], [btn(ctx.tr(T.back), Cb.new, 0, 0, count)]]
    elif count > 1 and not ctx.state.get("new_name"):
        # Many users: their name comes first (typed), each gets its number after it
        ctx.state.update(awaiting="new_name", new_args=[gb, days, count])
        text += f"✏️ {ctx.tr(T.new_many_name, example=h(names_preview('Hiddify', count)))}"
        rows += [[btn(ctx.tr(T.new_use_name, name=name[:30]), Cb.new_name, gb, days, count, "d")], [btn(ctx.tr(T.back), Cb.new, gb, 0, count)]]
    else:
        rows += [
            [btn(ctx.tr(T.new_create_n, n=count) if count > 1 else ctx.tr(T.new_create), Cb.new_go, gb, days, count, style=Style.success)],
            [btn(ctx.tr(T.new_name), Cb.new_name, gb, days, count), btn(ctx.tr(T.back), Cb.new, gb, 0, count)],
        ]
    return Screen(text, keyboard(*rows))


@route(Cb.new, admin=True)
def show_new(ctx: Ctx, args: list[str]) -> None:
    gb, days, count = _int(args, 0), _int(args, 1), min(_int(args, 2), MAX_BATCH)
    if not (gb or days):
        ctx.state.update(new_name=None, awaiting=None)
    ctx.show(new_screen(ctx, gb, days, count))
    ctx.toast()


@route(Cb.new_count, admin=True)
def ask_count(ctx: Ctx, _args: list[str], error: bool = False) -> None:
    """How many users: typed, or one of the quick picks."""
    ctx.state.update(awaiting="new_count", new_name=None)
    picks = [btn(f"× {v}", Cb.new, 0, 0, v) for v in COUNT_PICKS]
    text = f"➕ <b>{ctx.tr(T.new_title)}</b>\n{RULE}\n🔢 {ctx.tr(T.new_count_prompt, max=MAX_BATCH)}"
    if error:
        text += f"\n\n⚠️ <i>{ctx.tr(T.new_count_bad, max=MAX_BATCH)}</i>"
    ctx.show(Screen(text, keyboard(picks, [btn(ctx.tr(T.back), Cb.new, 0, 0, 0)])))
    ctx.toast()


def parse_count(text: str) -> int | None:
    """A typed count (Persian and Arabic digits too), or None."""
    digits = text.strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    return int(digits) if digits.isdigit() and 1 <= int(digits) <= MAX_BATCH else None


@route(Cb.new_name, admin=True)
def ask_new_name(ctx: Ctx, args: list[str]) -> None:
    if args[3:4] == ["d"]:  # the suggested name
        assert ctx.admin
        ctx.state.update(new_name=_default_name(ctx.admin), awaiting=None)
        ctx.show(new_screen(ctx, _int(args, 0), _int(args, 1), _int(args, 2)))
        return ctx.toast()
    ctx.state.update(awaiting="new_name", new_args=[_int(args, 0), _int(args, 1), _int(args, 2)])
    ctx.show(Screen(f"✏️ {ctx.tr(T.new_name_prompt)}", keyboard([btn(ctx.tr(T.back), Cb.new, *args[:3])])))
    ctx.toast()


@route(Cb.new_go, admin=True)
def create_users(ctx: Ctx, args: list[str]) -> None:
    admin = ctx.admin
    assert admin
    gb = min(max(_int(args, 0), 1), accounts.MAX_USAGE_GB)
    days = min(max(_int(args, 1), 1), accounts.MAX_PACKAGE_DAYS)
    count = min(max(_int(args, 2), 1), MAX_BATCH)
    if accounts.is_read_only():
        return ctx.toast(ctx.tr(T.read_only_node), alert=True)
    if not admin.can_have_more_users():
        return ctx.toast(ctx.tr(T.limit_reached), alert=True)
    ctx.toast(ctx.tr(T.new_working))
    ctx.show(Screen(f"⏳ {ctx.tr(T.new_working)}"))
    name = str(ctx.state.get("new_name") or _default_name(admin))
    users = accounts.create(admin, gb=gb, days=days, count=count, name=name)
    ctx.state.update(new_name=None, awaiting=None)
    ctx.show(Screen(f"📤 {ctx.tr(T.sending, n=len(users))}"))
    ids, chat_id, lang = [u.id for u in users], ctx.chat_id, ctx.lang
    background(lambda: _send_cards(chat_id, lang, ids, gb=gb, days=days))


#: Up to this many new users each get a card; more get one file of names and links
CARDS_AT_MOST = 10


def _send_cards(chat_id: int, lang: str, user_ids: list[int], *, gb: int, days: int) -> None:
    """One card per new user (forwardable, refreshable), then the panel again under them."""
    ctx = Ctx(chat_id, lang, admin=AdminUser.query.filter(AdminUser.telegram_id == chat_id).first())
    users = User.query.filter(User.id.in_(user_ids)).order_by(User.id).all()
    if len(users) <= CARDS_AT_MOST:
        for user in users:
            screen = share_screen(lang, user)
            with_retry(lambda: send_card(chat_id, screen))
    else:  # many: one file with every user's name and link, not a flood of cards
        lines = [f"{u.name}\t{accounts.links(u).sub}" for u in users]
        data = ("\n".join(lines) + "\n").encode()
        with_retry(lambda: bot.send_document(chat_id, types.InputFile(io.BytesIO(data), file_name=f"{users[0].name.rsplit('-', 1)[0]}-{len(users)}-users.txt"), caption=ctx.tr(T.new_file_caption, n=len(users))))
    done = ctx.tr(T.new_done_one) if len(user_ids) == 1 else ctx.tr(T.new_done_many, n=len(user_ids), gb=gb, days=days)
    ctx.show(
        Screen(
            f"✅ {done}",
            keyboard([btn(ctx.tr(T.btn_users), Cb.users, Filter.all.value, 0, style=Style.primary), btn(ctx.tr(T.btn_new), Cb.new, 0, 0, 0, style=Style.success)]),
        )
    )


def on_text(ctx: Ctx, text: str) -> None:
    """A typed message: the answer to a prompt, otherwise a search."""
    awaiting = ctx.state.get("awaiting")
    ctx.state.update(awaiting=None)
    if awaiting == "reply":
        from . import free

        return free.admin_reply(ctx, text)
    if awaiting == "new_count":
        n = parse_count(text)
        if n is None:
            return ask_count(ctx, [], error=True)
        ctx.show(new_screen(ctx, 0, 0, n))
        return
    if awaiting == "agent_name":
        from . import admins

        return admins.on_name(ctx, text)
    if awaiting == "new_name":
        ctx.state.update(new_name=text.strip()[:60])
        args = ctx.state.get("new_args") or [0, 0, 0]
        ctx.show(new_screen(ctx, *(int(a) for a in args[:3])))
        return
    ctx.show(search_screen(ctx, text.strip()[:100], 0))


# --------------------------------------------------------------------------- backup


@route(Cb.backup, admin=True)
def send_backup(ctx: Ctx, _args: list[str]) -> None:
    admin = ctx.admin
    assert admin
    if admin.mode != AdminMode.super_admin:
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    ctx.toast(ctx.tr(T.backup_working))
    try:
        from hiddifypanel.panel.commercial.restapi.v2.admin.backup_api import write_backup_file

        from . import backup_msg

        path = write_backup_file()
        with path.open("rb") as fp:
            backup_msg.send(ctx.chat_id, fp, path.name, admin, size=path.stat().st_size, tail=[btn(ctx.tr(T.close), Cb.close)])
    except Exception as e:
        logger.exception(e)
        bot.send_message(ctx.chat_id, f"⚠️ {ctx.tr(T.backup_failed)}\n<code>{h(e)}</code>")
        return
    ctx.message_id = None
    ctx.show(home_screen(ctx))
