"""Back, one step at a time, on a person's screens: each screen they open is kept on a short path; Back shows the one
before it, and the start screen (their card) at the first step. Menu clears the path."""

from __future__ import annotations

from loguru import logger

from .ui import ROUTES, Cb, Ctx, route

#: The screens a person moves between (actions, like a setting or sending a card, are not steps).
SCREENS = {Cb.me_links, Cb.guide, Cb.doctor, Cb.chart, Cb.support, Cb.history, Cb.settings, Cb.lang}
#: An admin's screens (the user list with its filters, a user, the status, the chats…)
ADMIN_SCREENS = {Cb.users, Cb.search, Cb.card, Cb.links, Cb.status, Cb.bandwidth, Cb.chats, Cb.chat, Cb.admin_settings, Cb.lang, Cb.free_link, Cb.new, Cb.new_count, Cb.broadcast, Cb.nodes, Cb.domains, Cb.bulk, Cb.admins, Cb.admin_card, Cb.apply, Cb.cfgtest, Cb.lock}
DEPTH = 12
#: Screens whose arguments only choose what they show (a filter, a page, an order): any of them is the same step
VIEWS = {Cb.users, Cb.search, Cb.chats, Cb.history}


def is_screen(kind: Cb, args: list[str]) -> bool:
    if kind is Cb.lang:
        return not args  # the language list, not choosing one
    if kind in (Cb.chart, Cb.bandwidth):
        return args[-1:] != ["r"]  # refreshing it (or another period in place) is not a step
    return kind in SCREENS


def is_admin_screen(kind: Cb, args: list[str]) -> bool:
    if kind is Cb.lang:
        return not args
    if kind is Cb.bandwidth:
        return bool(args) and args[-1:] != ["r"]  # a period's chart; another period in place is not a step
    if kind is Cb.broadcast:
        return args[:1] not in (["go"], ["x"])  # sending or dropping the message is not a step
    return kind in ADMIN_SCREENS


def _path(ctx: Ctx) -> list[list]:
    raw = ctx.state.get("nav") or []
    return [p for p in raw if isinstance(p, list) and len(p) == 2]


def reset(ctx: Ctx, kind: Cb | None = None, args: list[str] | None = None) -> None:
    ctx.state.update(nav=[[kind.value, args or []]] if kind else [])


def push(ctx: Ctx, kind: Cb, args: list[str]) -> None:
    """The screen being opened, as a browser keeps its history:
    - a screen already on the path (the device list again from a device) cuts the path back to it;
    - the same screen with as many arguments (another page of the history) takes the last step's place;
    - anything else (a device from the device list, the languages from settings) is a step further."""
    path = _path(ctx)
    entry = [kind.value, [str(a) for a in args]]
    if entry in path:
        path = path[: path.index(entry) + 1]
    elif path and path[-1][0] == kind.value and (len(path[-1][1]) == len(args) or kind in VIEWS):
        path[-1] = entry
    else:
        path.append(entry)
    ctx.state.update(nav=path[-DEPTH:])


@route(Cb.back, admin=False, anyone=True)
def go_back(ctx: Ctx, _args: list[str]) -> None:
    path = _path(ctx)
    if path:
        path.pop()
    ctx.state.update(nav=path)
    ctx.toast()
    if path:
        kind_raw, args = path[-1]
        try:
            target = ROUTES.get(Cb(kind_raw))
        except ValueError:
            target = None
        if target is not None:
            try:
                return target.handler(ctx, list(args))
            except Exception as e:
                logger.info(f"tgbot nav: back to {kind_raw} failed: {e}")
    from .handlers import open_home

    open_home(ctx)
