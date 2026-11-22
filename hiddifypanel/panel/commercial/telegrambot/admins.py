"""Advanced mode: the admin's sub-admins and agents (resellers) in the bot.

The list shows everyone under the admin (the same tree as the panel's Admins page), each with their users. A card
shows one of them: their limits, users and traffic, and turns them off or on, raises their user limits, and copies
their panel link. An admin allowed to add sub-admins can make a new agent here (its panel link comes back to copy).
The panel's rules stay: nobody sees or changes an admin outside their tree, nor themselves, nor the owner.
"""

from __future__ import annotations

from loguru import logger

from hiddifypanel.database import db
from hiddifypanel.models import AdminMode, AdminUser

from . import accounts, advanced
from .texts import T
from .ui import RULE, Cb, Ctx, Screen, Style, btn, copy_btn, fmt_gb, h, keyboard, route

PAGE = 8
LIMIT_STEPS = (10, 50)
MAX_LIMIT = 100_000
_MODE_ICON = {AdminMode.super_admin: "👑", AdminMode.admin: "🛡", AdminMode.agent: "🧑‍💼"}
_MODE_TEXT = {AdminMode.super_admin: T.am_owner, AdminMode.admin: T.am_admin, AdminMode.agent: T.am_agent}


def allowed(ctx: Ctx) -> bool:
    return advanced.is_on() and ctx.admin is not None and ctx.admin.mode != AdminMode.agent


def can_create(ctx: Ctx) -> bool:
    from hiddifypanel import admin_capabilities as caps

    return ctx.admin is not None and caps.has(ctx.admin, caps.ADD_SUB_ADMINS)


def under(ctx: Ctx) -> list[AdminUser]:
    """Everyone under the admin (not the admin, not the owner)."""
    admin = ctx.admin
    assert admin
    ids = set(admin.recursive_sub_admins_ids()) - {admin.id}
    owner = AdminUser.get_super_admin()
    return [a for a in AdminUser.query.filter(AdminUser.id.in_(ids)).order_by(AdminUser.name).all() if a.id != owner.id] if ids else []


def visible(ctx: Ctx, admin_id: int) -> AdminUser | None:
    return next((a for a in under(ctx) if a.id == admin_id), None)


def _users(a: AdminUser) -> tuple[int, int]:
    users = a.recursive_users_query().all()
    return len(users), sum(1 for u in users if u.is_active)


def list_screen(ctx: Ctx, page: int = 0) -> Screen:
    people = under(ctx)
    pages = max((len(people) + PAGE - 1) // PAGE, 1)
    page = min(max(page, 0), pages - 1)
    shown = people[page * PAGE : (page + 1) * PAGE]
    lines = [f"🧑‍💼 <b>{ctx.tr(T.am_title)}</b>", RULE, ctx.tr(T.am_count, n=len(people))]
    rows = []
    for a in shown:
        total, active = _users(a)
        mark = "" if a.enable else "⛔️ "
        rows.append([btn(f"{mark}{_MODE_ICON.get(a.mode, '🧑‍💼')} {a.name[:28]} · 👥 {active}/{total}", Cb.admin_card, a.id)])
    if not people:
        lines += ["", ctx.tr(T.am_none)]
    if pages > 1:
        rows.append([btn("«", Cb.admins, max(page - 1, 0)), btn(f"{page + 1}/{pages}", Cb.admins, page), btn("»", Cb.admins, min(page + 1, pages - 1))])
    if can_create(ctx):
        rows.append([btn(ctx.tr(T.am_new_agent), Cb.agent_new, style=Style.success)])
    rows.append([btn(ctx.tr(T.back), Cb.back)])
    return Screen("\n".join(lines), keyboard(*rows))


def _panel_link(a: AdminUser) -> str:
    from hiddifypanel.panel import hiddify

    try:
        return hiddify.get_account_panel_link(a, accounts.user_host())
    except Exception as e:
        logger.debug(f"tgbot: admin link not made: {e}")
        return ""


def card_screen(ctx: Ctx, a: AdminUser, note: str | None = None) -> Screen:
    total, active = _users(a)
    parent = AdminUser.by_id(a.parent_admin_id) if a.parent_admin_id else None
    lines = [
        f"{_MODE_ICON.get(a.mode, '🧑‍💼')} <b>{h(a.name)}</b>  ·  {ctx.tr(_MODE_TEXT.get(a.mode, T.am_agent))}",
        RULE,
        f"{'🟢' if a.enable else '⛔️'} {ctx.tr(T.am_on if a.enable else T.am_off)}",
        f"👥 {ctx.tr(T.am_users, active=active, total=total)}",
        f"📏 {ctx.tr(T.am_limits, users=a.max_users, active=a.max_active_users)}",
        f"📊 {ctx.tr(T.traffic_total)}: {fmt_gb(a.total_usage_GB(), ctx.lang)}" + (f" / {fmt_gb(a.max_total_usage_GB, ctx.lang)}" if a.max_total_usage_GB else ""),
    ]
    if parent and ctx.admin and parent.id != ctx.admin.id:
        lines.append(f"↖️ {ctx.tr(T.am_under, name=h(parent.name))}")
    if a.telegram_id:
        lines.append(f"✈️ {ctx.tr(T.am_has_telegram)}")
    if note:
        lines += ["", f"✅ <i>{h(note)}</i>"]
    aid = a.id
    toggle = btn(ctx.tr(T.disable), Cb.admin_card, aid, "off", 0, style=Style.danger) if a.enable else btn(ctx.tr(T.enable), Cb.admin_card, aid, "on", 0, style=Style.success)
    rows = [
        [btn(f"👥 +{s}", Cb.admin_card, aid, "users", s) for s in LIMIT_STEPS] + [btn(f"🟢 +{s}", Cb.admin_card, aid, "active", s) for s in LIMIT_STEPS],
        [toggle, copy_btn(ctx.tr(T.am_copy_link), _panel_link(a))],
        [btn(ctx.tr(T.back), Cb.admins), btn(ctx.tr(T.refresh), Cb.admin_card, aid)],
    ]
    return Screen("\n".join(lines), keyboard(*rows))


def create_agent(ctx: Ctx, name: str) -> AdminUser:
    admin = ctx.admin
    assert admin
    agent = AdminUser(name=name.strip()[:60] or "Agent", mode=AdminMode.agent, parent_admin_id=admin.id, can_add_admin=False, max_users=100, max_active_users=100)
    db.session.add(agent)
    db.session.commit()
    from hiddifypanel import hutils

    hutils.node.parent.notify_childs_users_changed()
    return agent


@route(Cb.admins, admin=True)
def show_admins(ctx: Ctx, args: list[str]) -> None:
    if not allowed(ctx):
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    page = int(args[0]) if args[:1] and args[0].isdigit() else 0
    ctx.toast()
    ctx.show(list_screen(ctx, page))


@route(Cb.admin_card, admin=True)
def show_admin_card(ctx: Ctx, args: list[str]) -> None:
    """ac:<id> → the card · ac:<id>:<on|off|users|active>:<value> → change it."""
    if not allowed(ctx):
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    a = visible(ctx, int(args[0])) if args[:1] and args[0].isdigit() else None
    if a is None:
        return ctx.toast(ctx.tr(T.gone), alert=True)
    if len(args) < 3:
        ctx.toast()
        return ctx.show(card_screen(ctx, a))
    if accounts.is_read_only():
        return ctx.toast(ctx.tr(T.read_only_node), alert=True)
    action, value = args[1], int(args[2]) if args[2].isdigit() else 0
    match action:
        case "on":
            a.enable = True
            note = ctx.tr(T.enabled)
        case "off":
            a.enable = False
            note = ctx.tr(T.disabled)
        case "users" if value in LIMIT_STEPS:
            a.max_users = min((a.max_users or 0) + value, MAX_LIMIT)
            note = ctx.tr(T.am_limit_up, n=value)
        case "active" if value in LIMIT_STEPS:
            a.max_active_users = min((a.max_active_users or 0) + value, MAX_LIMIT)
            note = ctx.tr(T.am_limit_up, n=value)
        case _:
            return ctx.toast(ctx.tr(T.unknown))
    db.session.commit()
    from hiddifypanel import hutils

    hutils.node.parent.notify_childs_users_changed()
    ctx.toast(note)
    ctx.show(card_screen(ctx, a, note))


@route(Cb.agent_new, admin=True)
def ask_agent_name(ctx: Ctx, _args: list[str]) -> None:
    if not allowed(ctx) or not can_create(ctx):
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    if accounts.is_read_only():
        return ctx.toast(ctx.tr(T.read_only_node), alert=True)
    ctx.state.update(awaiting="agent_name")
    ctx.toast()
    ctx.show(Screen(f"🧑‍💼 <b>{ctx.tr(T.am_new_agent)}</b>\n{RULE}\n✏️ {ctx.tr(T.am_name_prompt)}", keyboard([btn(ctx.tr(T.back), Cb.admins)])))


def on_name(ctx: Ctx, text: str) -> None:
    """The typed name of the new agent."""
    if not allowed(ctx) or not can_create(ctx) or accounts.is_read_only():
        return
    agent = create_agent(ctx, text)
    ctx.show(card_screen(ctx, agent, ctx.tr(T.am_created, name=agent.name)))
