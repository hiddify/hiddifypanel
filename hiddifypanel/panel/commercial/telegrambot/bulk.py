"""Advanced mode: one action on many users at once (the users list's "Bulk" key).

Pick the users by the list's tabs (all, active, ending soon, ended, online), then the action (days, data, renew,
reset the usage, on, off, delete), see how many it touches, confirm. Only the admin's own users (and their
sub-admins'), the same limits as one user's card: turning users on stops at the admin's active-user limit, and the
panel never loses its last user.
"""

from __future__ import annotations

import json

from loguru import logger

from hiddifypanel.database import db
from hiddifypanel.models import User

from . import accounts, advanced
from .accounts import Filter
from .texts import T
from .ui import RULE, Cb, Ctx, Screen, Style, btn, h, keyboard, route

#: At most this many users in one bulk action (a bigger panel does it in steps, from the panel).
MAX_BULK = 3000
DAY_CHOICES = (7, 30, 90)
#: How long a confirm screen's users are kept for its confirm press
CONFIRM_TTL = 10 * 60
GB_CHOICES = (10, 50, 100)
#: action -> (label, needs a value)
ACTIONS = ("days", "gb", "renew", "reset", "on", "off", "del")


def targets(ctx: Ctx, f: Filter) -> list[User]:
    """The admin's users the tab keeps (no more than MAX_BULK), by the users list's own rule."""
    admin = ctx.admin
    assert admin
    query = accounts.narrowed(admin, f).order_by(User.id)
    if f in (Filter.all, Filter.online):
        return query.limit(MAX_BULK).all()
    return [u for u in query.all() if accounts.matches(u, f)][:MAX_BULK]


def _ids_key(ctx: Ctx) -> str:
    from .resellers import state_prefix

    return f"tgbot:bulk:{state_prefix()}{ctx.chat_id}"


def _remember(ctx: Ctx, f: Filter, action: str, value: int, users: list[User]) -> None:
    """The users the confirm screen shows: the press that confirms changes exactly these (ten minutes)."""
    from hiddifypanel.cache import redis_client

    redis_client.set(_ids_key(ctx), json.dumps({"key": f"{f.value}:{action}:{value}", "ids": [u.id for u in users]}), ex=CONFIRM_TTL)


def _confirmed(ctx: Ctx, f: Filter, action: str, value: int) -> list[User] | None:
    """The users the confirm screen showed (still the admin's), when it was for this very action; read once."""
    from hiddifypanel.cache import redis_client

    key = _ids_key(ctx)
    raw = redis_client.get(key)
    redis_client.delete(key)
    try:
        saved = json.loads(raw) if raw else {}
    except ValueError:
        saved = {}
    if saved.get("key") != f"{f.value}:{action}:{value}" or not isinstance(saved.get("ids"), list):
        return None
    admin = ctx.admin
    assert admin
    ids = [int(i) for i in saved["ids"] if str(i).isdigit()]
    return admin.recursive_users_query().filter(User.id.in_(ids)).order_by(User.id).all() if ids else []


def _filter(args: list[str]) -> Filter | None:
    try:
        return Filter(args[0])
    except (IndexError, ValueError):
        return None


def _icons():
    from .admin import _FILTER_ICON, _FILTER_TEXT

    return _FILTER_ICON, _FILTER_TEXT


def choose_screen(ctx: Ctx) -> Screen:
    icon, text = _icons()
    admin = ctx.admin
    assert admin
    n = accounts.counts(admin)
    rows = [[btn(f"{icon[f]} {ctx.tr(text[f])} · {n[f]}", Cb.bulk, f.value)] for f in Filter]
    lines = [f"🧰 <b>{ctx.tr(T.bu_title)}</b>", RULE, ctx.tr(T.bu_pick_users)]
    return Screen("\n".join(lines), keyboard(*rows, [btn(ctx.tr(T.back), Cb.back)]))


def actions_screen(ctx: Ctx, f: Filter) -> Screen:
    icon, text = _icons()
    count = len(targets(ctx, f))
    lines = [f"🧰 <b>{ctx.tr(T.bu_title)}</b>  ·  {icon[f]} {ctx.tr(text[f])}", RULE, ctx.tr(T.bu_count, n=count), "", ctx.tr(T.bu_pick_action)]
    v = f.value
    rows = [
        [btn(f"+{d} {ctx.tr(T.unit_d)}", Cb.bulk, v, "days", d) for d in DAY_CHOICES],
        [btn(f"+{g} {ctx.tr(T.gb)}", Cb.bulk, v, "gb", g) for g in GB_CHOICES],
        [btn(ctx.tr(T.renew), Cb.bulk, v, "renew", 0, style=Style.success), btn(ctx.tr(T.reset_usage), Cb.bulk, v, "reset", 0)],
        [btn(ctx.tr(T.enable), Cb.bulk, v, "on", 0, style=Style.success), btn(ctx.tr(T.disable), Cb.bulk, v, "off", 0)],
        [btn(ctx.tr(T.delete), Cb.bulk, v, "del", 0, style=Style.danger)],
        [btn(ctx.tr(T.back), Cb.back)],
    ]
    if not count:
        rows = [rows[-1]]
    return Screen("\n".join(lines), keyboard(*rows))


def _what(ctx: Ctx, action: str, value: int) -> str:
    return {
        "days": f"+{value} {ctx.tr(T.unit_d)}",
        "gb": f"+{value} {ctx.tr(T.gb)}",
        "renew": ctx.tr(T.renew),
        "reset": ctx.tr(T.reset_usage),
        "on": ctx.tr(T.enable),
        "off": ctx.tr(T.disable),
        "del": ctx.tr(T.delete),
    }[action]


def confirm_screen(ctx: Ctx, f: Filter, action: str, value: int) -> Screen:
    icon, text = _icons()
    users = targets(ctx, f)
    _remember(ctx, f, action, value, users)
    names = ", ".join(h(u.name) for u in users[:8]) + (" …" if len(users) > 8 else "")
    lines = [
        f"🧰 <b>{ctx.tr(T.bu_title)}</b>",
        RULE,
        ctx.tr(T.bu_confirm, what=f"<b>{_what(ctx, action, value)}</b>", n=len(users), group=f"{icon[f]} {ctx.tr(text[f])}"),
        f"<blockquote expandable>{names}</blockquote>" if names else "",
    ]
    if action == "del":
        lines.append(f"⚠️ <i>{ctx.tr(T.bu_del_warn)}</i>")
    go = btn(ctx.tr(T.confirm), Cb.bulk, f.value, action, value, 1, style=Style.danger if action in ("del", "off") else Style.success)
    return Screen("\n".join(x for x in lines if x), keyboard([go, btn(ctx.tr(T.cancel), Cb.bulk, f.value)]))


def _within_active_limit(admin, users: list[User], *, only_off: bool) -> tuple[list[User], int]:
    """``users`` cut to the admin's room for active users: the active ones always, the inactive ones while they fit.
    ``only_off``: only the switched-off ones are wanted (turning on)."""
    inactive = [u for u in users if not u.enable] if only_off else [u for u in users if not u.is_active]
    room = admin.room_to_activate(len(inactive))
    allowed = {u.id for u in inactive[:room]}
    if only_off:
        return [u for u in inactive if u.id in allowed], len(inactive) - len(allowed)
    return [u for u in users if u.is_active or u.id in allowed], len(inactive) - len(allowed)


def run(ctx: Ctx, f: Filter, action: str, value: int) -> tuple[int, int]:
    """Does it: (users changed, users skipped by a limit)."""
    admin = ctx.admin
    assert admin
    users = _confirmed(ctx, f, action, value)
    if users is None:
        users = targets(ctx, f)
    skipped = 0
    if action == "del":
        left = User.query.filter(User.deleted.is_(False)).count()
        if len(users) >= left:  # the panel keeps one user at least
            skipped = len(users) - left + 1
            users = users[: max(left - 1, 0)]
        for u in users:
            u.remove(commit=False)
        db.session.commit()
        from hiddifypanel import hutils

        hutils.apply_users.quick_apply_users(users_only=True)
        hutils.node.parent.notify_childs_users_changed()
        return len(users), skipped
    # Any user not active now that this can turn on (on, renew, more days or data for an ended package) counts
    # against the admin's active-user limit: the first ones that fit are changed, the others are left as they are.
    if action in ("on", "renew", "days", "gb"):
        users, skipped = _within_active_limit(admin, users, only_off=action == "on")
    changed = []
    for u in users:
        match action:
            case "days":
                accounts.add_days(u, value)
            case "gb":
                accounts.add_gb(u, value)
            case "renew":
                accounts.renew(u)
            case "reset":
                u.reset_usage()
            case "on":
                u.enable = True
            case "off":
                if not u.enable:
                    continue
                u.enable = False
        changed.append(u)
    db.session.commit()
    if changed:
        accounts.apply(changed)
    return len(changed), skipped


@route(Cb.bulk, admin=True)
def show_bulk(ctx: Ctx, args: list[str]) -> None:
    """bu → pick users · bu:<f> → pick the action · bu:<f>:<action>:<value> → confirm · …:1 → do it."""
    if not advanced.is_on():
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    if accounts.is_read_only():
        return ctx.toast(ctx.tr(T.read_only_node), alert=True)
    f = _filter(args)
    if f is None:
        ctx.toast()
        return ctx.show(choose_screen(ctx))
    if len(args) < 3:
        ctx.toast()
        return ctx.show(actions_screen(ctx, f))
    action = args[1]
    try:
        value = int(args[2])
    except ValueError:
        value = 0
    if action not in ACTIONS or (action == "days" and value not in DAY_CHOICES) or (action == "gb" and value not in GB_CHOICES):
        return ctx.toast(ctx.tr(T.unknown))
    if args[3:4] != ["1"]:
        ctx.toast()
        return ctx.show(confirm_screen(ctx, f, action, value))
    from .miniapp import needs_unlock

    if needs_unlock(ctx, "bulk", ":".join([Cb.bulk.value, *args])):
        return
    ctx.toast(ctx.tr(T.bu_working))
    try:
        done, skipped = run(ctx, f, action, value)
    except Exception as e:
        db.session.rollback()
        logger.exception(f"tgbot: bulk {action} failed: {e}")
        return ctx.toast(ctx.tr(T.error_generic), alert=True)
    note = ctx.tr(T.bu_done, what=_what(ctx, action, value), n=done)
    if skipped:
        note += "\n" + ctx.tr(T.bu_skipped, n=skipped)
    screen = actions_screen(ctx, f)
    ctx.show(Screen(f"✅ <i>{note}</i>\n\n" + screen.text, screen.markup))


def list_row(ctx: Ctx) -> list:
    """The users list's key to it (Advanced, a panel that can change users)."""
    if not advanced.is_on() or accounts.is_read_only():
        return []
    return [btn(ctx.tr(T.bu_title), Cb.bulk)]
