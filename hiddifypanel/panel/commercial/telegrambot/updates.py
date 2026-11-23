"""Advanced mode, super admins: update the panel of this server or of a node, from the bot (the status screen's
"Update Panel" key).

The servers are listed as keys: green the ones answering, red the others. A green one asks first (an update takes
several minutes and restarts the panel), then runs the panel's own update: this server's Apply page action, or the
node's, called with the owner's own key (the admins are the same on the parent and its nodes, as when the owner opens
a node's panel). The message waits until the update is over and then says how it ended.

The panel restarts during its own update, so the end is not watched by a thread of this process: each update waiting
is kept in redis and a scheduled job (every minute, in one worker) looks at it, also after the restart.
"""

from __future__ import annotations

import json
import time

from loguru import logger
from pydantic import BaseModel, ConfigDict

from hiddifypanel.cache import redis_client
from hiddifypanel.models import AdminMode, AdminUser

from . import advanced, bot
from .texts import T, t
from .ui import RULE, Cb, Ctx, Screen, Style, btn, h, keyboard, route

_WATCH = "tgbot:upd:watch"  # hash: "<chat>:<message>" → json of the update being watched
#: An update that has not ended after this long is reported as unknown (look at its log on the Apply page)
WATCH_FOR = 45 * 60
#: The update has had time to start (its unit or lock) before an idle state means it is over
START_GRACE = 90
_APPLY_PATH = "api/v2/admin/apply/"


class _ApplyState(BaseModel):
    """The node's Apply page state (only what is used here)."""

    model_config = ConfigDict(extra="allow")
    running: list[str] = []
    last: dict = {}
    now: float = 0


def allowed(ctx: Ctx) -> bool:
    return advanced.is_on() and ctx.admin is not None and ctx.admin.mode == AdminMode.super_admin


def _servers() -> list:
    from .servers import _nodes

    return _nodes()


_SERVERS = "tgbot:upd:servers"
_SERVERS_TTL = 120


def _remember(servers: list) -> None:
    """The list as the admin saw it: the question and the start use it (asking every node again takes seconds)."""
    rows = [{"id": n.id, "name": n.name, "ok": bool(n.ok), "version": getattr(n.host, "panel_version", "") if n.ok and n.host else ""} for n in servers]
    redis_client.set(_SERVERS, json.dumps(rows), ex=_SERVERS_TTL)


def _known(server_id: int):
    from types import SimpleNamespace

    raw = redis_client.get(_SERVERS)
    try:
        rows = json.loads(raw) if raw else None
    except ValueError:
        rows = None
    if rows is None:
        servers = _servers()
        _remember(servers)
        return next((n for n in servers if n.id == server_id), None)
    row = next((r for r in rows if r["id"] == server_id), None)
    return SimpleNamespace(id=row["id"], name=row["name"], ok=row["ok"], host=SimpleNamespace(panel_version=row["version"])) if row else None


def _child(node_id: int):
    from hiddifypanel.models import Child, ChildMode

    return Child.query.filter(Child.id == node_id, Child.mode == ChildMode.remote).first()


def _client(child, owner: AdminUser, *, timeout: float = 30):
    from hiddifypanel.hutils.node.api_client import NodeApiClient

    return NodeApiClient(child.node_base_url, apikey=str(owner.uuid), max_retry=1, timeout=timeout, retry_on_timeout=False)


def _name(ctx: Ctx, n) -> str:
    return n.name if n.id else (n.name if n.name not in ("", "this-server") else ctx.tr(T.nd_this))


# --------------------------------------------------------------------------- screens


def list_screen(ctx: Ctx) -> Screen:
    try:
        servers = _servers()
        _remember(servers)
    except Exception as e:
        logger.warning(f"tgbot: servers not read for an update: {e}")
        servers = []
    rows = []
    for n in servers:
        version = getattr(n.host, "panel_version", "") if n.ok and n.host else ""
        label = f"{'🖥' if n.id == 0 else '🌐'} {_name(ctx, n)}" + (f"  ·  v{version}" if version else "")
        rows.append([btn(label[:60], Cb.update, n.id, style=Style.success if n.ok else Style.danger)])
    lines = [f"🔄 <b>{ctx.tr(T.up_title)}</b>", RULE, ctx.tr(T.up_pick), "", f"🟢 {ctx.tr(T.up_online)}  ·  🔴 {ctx.tr(T.up_offline)}"]
    rows.append([btn(ctx.tr(T.refresh), Cb.update), btn(ctx.tr(T.back), Cb.back)])
    return Screen("\n".join(lines), keyboard(*rows))


def _server(ctx: Ctx, server_id: int):
    return _known(server_id)


def confirm_screen(ctx: Ctx, n) -> Screen:
    lines = [
        f"🔄 <b>{ctx.tr(T.up_title)}</b>",
        RULE,
        f"{'🖥' if n.id == 0 else '🌐'} <b>{h(_name(ctx, n))}</b>",
        "",
        f"❓ {ctx.tr(T.up_confirm)}",
        f"<blockquote>⏱ {ctx.tr(T.up_takes)}\n♻️ {ctx.tr(T.up_restarts)}</blockquote>",
    ]
    return Screen("\n".join(lines), keyboard([btn(ctx.tr(T.up_yes), Cb.update, n.id, "go", style=Style.success)], [btn(ctx.tr(T.cancel), Cb.update)]))


def waiting_text(lang: str, name: str, since: float) -> str:
    minutes = max(int((time.time() - since) // 60), 0)
    return "\n".join(
        [
            f"⏳ <b>{t(T.up_running, lang, name=h(name))}</b>",
            RULE,
            t(T.up_wait, lang),
            f"<i>{t(T.up_elapsed, lang, n=minutes)}</i>",
        ]
    )


# --------------------------------------------------------------------------- starting it


def start(ctx: Ctx, n) -> tuple[bool, float]:
    """Starts the update; (started, the time it started by the server's own clock)."""
    if n.id == 0:
        from hiddifypanel.panel.commercial.restapi.v2.admin import apply_api

        apply_api.start_action("update")
        return True, time.time()
    child = _child(n.id)
    assert ctx.admin
    if child is None or not child.node_base_url:
        return False, 0.0
    # As the admin who pressed it (the admins are the same on the parent and its nodes)
    res = _client(child, ctx.admin).post(_APPLY_PATH + "update/", None, _ApplyState)
    if not isinstance(res, _ApplyState):
        logger.info(f"tgbot: node {n.id} update not started: {getattr(res, 'msg', res)}")
        return False, 0.0
    return True, float(res.now or time.time())


def _watch(chat_id: int, message_id: int, server_id: int, name: str, lang: str, server_started: float, admin_id: int) -> None:
    entry = {"chat": chat_id, "msg": message_id, "server": server_id, "name": name, "lang": lang, "started": time.time(), "server_started": server_started, "admin": admin_id}
    redis_client.hset(_WATCH, f"{chat_id}:{message_id}", json.dumps(entry))


@route(Cb.update, admin=True)
def show_update(ctx: Ctx, args: list[str]) -> None:
    """up → the servers · up:<id> → are you sure? · up:<id>:go → update it."""
    if not allowed(ctx):
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    if not args or not args[0].lstrip("-").isdigit():
        ctx.toast(ctx.tr(T.nd_checking))
        return ctx.show(list_screen(ctx))
    n = _server(ctx, int(args[0]))
    if n is None:
        return ctx.toast(ctx.tr(T.gone), alert=True)
    if not n.ok:
        return ctx.toast(ctx.tr(T.up_cannot_offline), alert=True)
    if args[1:2] != ["go"]:
        ctx.toast()
        return ctx.show(confirm_screen(ctx, n))
    from .miniapp import needs_unlock

    if needs_unlock(ctx, "apply", f"{Cb.update.value}:{n.id}:go"):
        return
    ctx.toast(ctx.tr(T.up_starting))  # the node may take seconds to answer: Telegram hears back at once
    try:
        started, server_started = start(ctx, n)
    except Exception as e:  # another action running there, or the panel too old
        logger.info(f"tgbot: update of {n.id} not started: {getattr(e, 'description', e)}")
        started, server_started = False, 0.0
    if not started:
        return ctx.show(Screen(f"⚠️ {ctx.tr(T.up_not_started)}", keyboard([btn(ctx.tr(T.up_title), Cb.update)])))
    name = _name(ctx, n)
    ctx.show(list_screen(ctx))  # the bot's screen goes on; the waiting is a message of its own
    sent = bot.send_message(ctx.chat_id, waiting_text(ctx.lang, name, time.time()))
    _watch(ctx.chat_id, sent.message_id, n.id, name, ctx.lang, server_started, ctx.admin.id)


# --------------------------------------------------------------------------- watching it (scheduled)


def _state_of(server_id: int, admin_id: int | None = None) -> dict | None:
    """The server's Apply state now; None when it cannot be asked (a panel restarting during its update)."""
    if server_id == 0:
        from hiddifypanel.panel.commercial.restapi.v2.admin import apply_api

        return {"running": apply_api.running_actions(), "last": apply_api._last_runs(), "now": time.time()}
    child = _child(server_id)
    if child is None:
        return None
    admin = AdminUser.by_id(admin_id) if admin_id else None
    res = _client(child, admin or AdminUser.get_super_admin(), timeout=15).get(_APPLY_PATH, _ApplyState)
    return res.model_dump() if isinstance(res, _ApplyState) else None


def outcome(entry: dict, state: dict | None, now: float) -> str | None:
    """"ok", "failed", "unknown" (too long), or None while it still runs."""
    if now - float(entry["started"]) > WATCH_FOR:
        return "unknown"
    if state is None or now - float(entry["started"]) < START_GRACE:
        return None
    if "update" in (state.get("running") or []):
        return None
    last = (state.get("last") or {}).get("update") or {}
    if float(last.get("mtime") or 0) < float(entry.get("server_started") or 0) - 5:
        return None  # its log has not been written since it started: not over yet
    return "ok" if last.get("finished") else "failed"


def watch_updates() -> None:
    """Scheduled every minute (one worker): the updates the bot started, until each one is over."""
    from hiddifypanel.models import ConfigEnum, hconfig

    if not hconfig(ConfigEnum.telegram_bot_token):
        return
    watched = redis_client.hgetall(_WATCH) or {}
    if not watched:
        return
    from . import register_bot

    if not bot.username:
        register_bot()
    now = time.time()
    for key, raw in watched.items():
        try:
            entry = json.loads(raw)
        except ValueError:
            redis_client.hdel(_WATCH, key)
            continue
        try:
            result = outcome(entry, _state_of(int(entry["server"]), entry.get("admin")), now)
        except Exception as e:
            logger.debug(f"tgbot: update of {entry.get('server')} not checked: {e}")
            result = None
        lang, name = entry.get("lang") or "en", entry.get("name") or ""
        if result is None:
            text = waiting_text(lang, name, float(entry["started"]))
        else:
            mark, key_text = {"ok": ("✅", T.up_done), "failed": ("⚠️", T.up_failed), "unknown": ("⏱", T.up_unknown)}[result]
            text = f"{mark} <b>{t(key_text, lang, name=h(name))}</b>"
            redis_client.hdel(_WATCH, key)
        try:
            bot.edit_message_text(text, int(entry["chat"]), int(entry["msg"]), reply_markup=keyboard([btn(t(T.up_title, lang), Cb.update)]) if result else None)
        except Exception as e:
            if "not modified" not in str(e) and result:
                try:  # the message is gone or too old to edit: a new one
                    bot.send_message(int(entry["chat"]), text)
                except Exception:
                    logger.debug(f"tgbot: update end not told: {e}")
