"""The admin side: home, the users list (filters, search, pages), the user card and its actions, creating one
or many users, and backups. Everything happens in one message that the buttons edit."""

from __future__ import annotations

import datetime
from collections.abc import Sequence

from loguru import logger
from telebot import types

from hiddifypanel.database import db
from hiddifypanel.models import AdminMode, AdminUser, User

from . import accounts, bot
from .accounts import Filter
from .texts import T
from .ui import RULE, Cb, Ctx, Screen, app_row, background, btn, fmt_gb, h, keyboard, route, send_card, with_retry
from .user import account_card, links_text, share_screen

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
    users = accounts.visible_users(admin)
    active = sum(accounts.status(u) is accounts.Status.active for u in users)
    online = sum(accounts.is_online(u) for u in users)
    expiring = sum(accounts.is_expiring(u) for u in users)
    text = "\n".join(
        [
            ctx.tr(T.admin_hello, name=h(admin.name)),
            RULE,
            ctx.tr(T.admin_summary, total=len(users), active=active, online=online, expiring=expiring),
        ]
    )
    rows: list[Sequence[types.InlineKeyboardButton]] = [
        [btn(ctx.tr(T.btn_users), Cb.users, Filter.all.value, 0), btn(ctx.tr(T.btn_new), Cb.new, 0, 0, 0)],
        [btn(ctx.tr(T.btn_status), Cb.status)] + ([btn(ctx.tr(T.btn_check), Cb.check)] if admin.mode != AdminMode.agent else []),
    ]
    if admin.mode == AdminMode.super_admin:
        rows.append([btn(ctx.tr(T.btn_backup), Cb.backup)])
    rows.append(app_row(ctx.tr(T.btn_panel), accounts.panel_app_url()))
    return Screen(text, keyboard(*rows))


@route(Cb.home, admin=True)
def show_home(ctx: Ctx, _args: list[str]) -> None:
    ctx.state.update(awaiting=None)
    ctx.show(home_screen(ctx))
    ctx.toast()


# --------------------------------------------------------------------------- users list


def _user_button(ctx: Ctx, user: User) -> types.InlineKeyboardButton:
    icon = accounts.STATUS_ICON[accounts.status(user)]
    online = "⚡️" if accounts.is_online(user) else ""
    days = f"{user.remaining_days}{ctx.tr(T.unit_d)}" if user.start_date else f"{user.package_days}{ctx.tr(T.unit_d)}"
    label = f"{icon}{online} {user.name or '-'} · {user.current_usage_GB:.1f}/{user.usage_limit_GB:g} · {days}"
    return btn(label[:60], Cb.card, user.id)


def _pager(kind: Cb, prefix: list[object], page: int, pages: int) -> list[types.InlineKeyboardButton]:
    if pages <= 1:
        return []
    return [
        btn("‹" if page > 0 else " ", kind, *prefix, max(page - 1, 0)),
        btn(f"{page + 1} / {pages}", kind, *prefix, page),
        btn("›" if page < pages - 1 else " ", kind, *prefix, min(page + 1, pages - 1)),
    ]


def _page(users: list[User], page: int) -> tuple[list[User], int, int]:
    pages = max((len(users) + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = min(max(page, 0), pages - 1)
    return users[page * PAGE_SIZE : (page + 1) * PAGE_SIZE], page, pages


def users_screen(ctx: Ctx, f: Filter, page: int) -> Screen:
    admin = ctx.admin
    assert admin
    users = [u for u in accounts.visible_users(admin) if accounts.matches(u, f)]
    shown, page, pages = _page(users, page)
    ctx.state.update(back=[Cb.users.value, f.value, page])

    tabs = [btn(("• " if x is f else "") + ctx.tr(_FILTER_TEXT[x]), Cb.users, x.value, 0) for x in Filter]
    text = f"👥 <b>{ctx.tr(T.users_title)}</b> · {ctx.tr(_FILTER_TEXT[f])}\n{ctx.tr(T.users_count, n=len(users))}"
    if not users:
        text += f"\n\n<i>{ctx.tr(T.users_empty)}</i>"
    return Screen(
        text,
        keyboard(
            tabs[:3],
            tabs[3:],
            *([_user_button(ctx, u)] for u in shown),
            _pager(Cb.users, [f.value], page, pages),
            [btn(ctx.tr(T.search), Cb.search_ask), btn(ctx.tr(T.menu), Cb.home)],
        ),
    )


@route(Cb.users, admin=True)
def show_users(ctx: Ctx, args: list[str]) -> None:
    try:
        f = Filter(args[0])
    except (IndexError, ValueError):
        f = Filter.all
    ctx.show(users_screen(ctx, f, _int(args, 1)))
    ctx.toast()


@route(Cb.search_ask, admin=True)
def ask_search(ctx: Ctx, _args: list[str]) -> None:
    ctx.state.update(awaiting="search")
    ctx.show(Screen(f"🔍 <b>{ctx.tr(T.search)}</b>\n\n{ctx.tr(T.search_prompt)}", keyboard([_back_btn(ctx, T.cancel)])))
    ctx.toast()


def search_screen(ctx: Ctx, query: str, page: int) -> Screen:
    admin = ctx.admin
    assert admin
    found = accounts.find_users(admin, query)
    if len(found) == 1 and page == 0:
        return card_screen(ctx, found[0])
    shown, page, pages = _page(found, page)
    ctx.state.update(back=[Cb.search.value, page], query=query)
    text = f"🔍 <b>{ctx.tr(T.search_results, q=h(query))}</b>\n{ctx.tr(T.users_count, n=len(found))}"
    if not found:
        text += f"\n\n<i>{ctx.tr(T.users_empty)}</i>"
    return Screen(
        text,
        keyboard(
            *([_user_button(ctx, u)] for u in shown),
            _pager(Cb.search, [], page, pages),
            [btn(ctx.tr(T.search), Cb.search_ask), btn(ctx.tr(T.search_clear), Cb.users, Filter.all.value, 0)],
            [btn(ctx.tr(T.menu), Cb.home)],
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
    toggle = btn(ctx.tr(T.disable), Cb.act, uid, "off") if user.enable else btn(ctx.tr(T.enable), Cb.act, uid, "on")
    return Screen(
        "\n".join(lines),
        keyboard(
            [btn(ctx.tr(T.links), Cb.links, uid), btn(ctx.tr(T.qr), Cb.qr, uid)],
            [btn(ctx.tr(T.add_days), Cb.act, uid, "days"), btn(ctx.tr(T.add_gb), Cb.act, uid, "gb")],
            [btn(ctx.tr(T.renew), Cb.act, uid, "renew"), btn(ctx.tr(T.reset_usage), Cb.act, uid, "reset")],
            [toggle, btn(ctx.tr(T.delete), Cb.act, uid, "del")],
            [_back_btn(ctx), btn(ctx.tr(T.refresh), Cb.card, uid)],
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
        ctx.show(Screen(links_text(user, ctx.lang), keyboard([btn(ctx.tr(T.qr), Cb.qr, user.id)], [btn(ctx.tr(T.back), Cb.card, user.id)])))
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
            ctx.show(Screen(head + ctx.tr(T.delete_confirm), keyboard([btn(ctx.tr(T.delete), Cb.act, user.id, "del", 1), btn(ctx.tr(T.cancel), Cb.card, user.id)])))
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


def new_screen(ctx: Ctx, gb: int, days: int, count: int) -> Screen:
    admin = ctx.admin
    assert admin
    name = str(ctx.state.get("new_name") or _default_name(admin))
    summary = ctx.tr(
        T.new_summary,
        gb=fmt_gb(gb, ctx.lang) if gb else "—",
        days=f"{days} {ctx.tr(T.unit_d)}" if days else "—",
        count=count or "—",
        name=h(name),
    )
    text = f"➕ <b>{ctx.tr(T.new_title)}</b>\n{RULE}\n{summary}\n\n"
    rows: list[Sequence[types.InlineKeyboardButton]] = []
    if not gb:
        text += ctx.tr(T.new_gb)
        b = [btn(f"{v} {ctx.tr(T.gb)}", Cb.new, v, days, count) for v in GB_CHOICES]
        rows += [b[:4], b[4:]]
    elif not days:
        text += ctx.tr(T.new_days)
        b = [btn(f"{v} {ctx.tr(T.unit_d)}", Cb.new, gb, v, count) for v in DAY_CHOICES]
        rows += [b[:4], b[4:], [btn(ctx.tr(T.back), Cb.new, 0, 0, 0)]]
    elif not count:
        text += ctx.tr(T.new_count)
        b = [btn(f"× {v}", Cb.new, gb, days, v) for v in COUNT_CHOICES]
        rows += [b[:4], b[4:], [btn(ctx.tr(T.back), Cb.new, gb, 0, 0)]]
    else:
        rows += [
            [btn(ctx.tr(T.new_create), Cb.new_go, gb, days, count)],
            [btn(ctx.tr(T.new_name), Cb.new_name, gb, days, count), btn(ctx.tr(T.back), Cb.new, gb, days, 0)],
        ]
    rows.append([btn(ctx.tr(T.cancel), Cb.home)])
    return Screen(text, keyboard(*rows))


@route(Cb.new, admin=True)
def show_new(ctx: Ctx, args: list[str]) -> None:
    gb, days, count = _int(args, 0), _int(args, 1), _int(args, 2)
    if not (gb or days or count):
        ctx.state.update(new_name=None, awaiting=None)
    ctx.show(new_screen(ctx, gb, days, count))
    ctx.toast()


@route(Cb.new_name, admin=True)
def ask_new_name(ctx: Ctx, args: list[str]) -> None:
    ctx.state.update(awaiting="new_name", new_args=[_int(args, 0), _int(args, 1), _int(args, 2)])
    ctx.show(Screen(f"✏️ {ctx.tr(T.new_name_prompt)}", keyboard([btn(ctx.tr(T.back), Cb.new, *args[:3])])))
    ctx.toast()


@route(Cb.new_go, admin=True)
def create_users(ctx: Ctx, args: list[str]) -> None:
    admin = ctx.admin
    assert admin
    gb = min(max(_int(args, 0), 1), accounts.MAX_USAGE_GB)
    days = min(max(_int(args, 1), 1), accounts.MAX_PACKAGE_DAYS)
    count = min(max(_int(args, 2), 1), max(COUNT_CHOICES))
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


def _send_cards(chat_id: int, lang: str, user_ids: list[int], *, gb: int, days: int) -> None:
    """One card per new user (forwardable, refreshable), then the panel again under them."""
    ctx = Ctx(chat_id, lang, admin=AdminUser.query.filter(AdminUser.telegram_id == chat_id).first())
    for user in User.query.filter(User.id.in_(user_ids)).order_by(User.id).all():
        screen = share_screen(lang, user)
        with_retry(lambda: send_card(chat_id, screen))
    done = ctx.tr(T.new_done_one) if len(user_ids) == 1 else ctx.tr(T.new_done_many, n=len(user_ids), gb=gb, days=days)
    ctx.show(
        Screen(
            f"✅ {done}",
            keyboard([btn(ctx.tr(T.btn_users), Cb.users, Filter.all.value, 0), btn(ctx.tr(T.btn_new), Cb.new, 0, 0, 0)], [btn(ctx.tr(T.menu), Cb.home)]),
        )
    )


def on_text(ctx: Ctx, text: str) -> None:
    """A typed message: the answer to a prompt, otherwise a search."""
    awaiting = ctx.state.get("awaiting")
    ctx.state.update(awaiting=None)
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

        path = write_backup_file()
        with path.open("rb") as fp:
            bot.send_document(ctx.chat_id, types.InputFile(fp, file_name=path.name), caption=ctx.tr(T.backup_caption), reply_markup=keyboard([btn(ctx.tr(T.close), Cb.close)]))
    except Exception as e:
        logger.exception(e)
        bot.send_message(ctx.chat_id, f"⚠️ {ctx.tr(T.backup_failed)}\n<code>{h(e)}</code>")
        return
    ctx.message_id = None
    ctx.show(home_screen(ctx))
