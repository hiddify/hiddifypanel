"""Advanced mode: the panel's operations in the bot, for the super admins (the same people as the panel's Apply page).

- Apply: applies the configs (the Apply page's action); the bot says when it is over, and whether it finished.
- Config test: every config of the subscription tested from the server (the panel's config health check): the last
  result, and a new test on request; the bot sends the result when it is ready.
- Clean IP scanner: opens the panel's scanner page in Telegram (a Mini App). A clean IP is one that works from the
  admin's own internet, so the scan runs on their phone, not on the server.
"""

from __future__ import annotations

import datetime
import time

from loguru import logger

from hiddifypanel.models import AdminMode

from . import advanced, bot
from .texts import T, t
from .ui import RULE, Cb, Ctx, Screen, Style, app_btn, background, btn, h, keyboard, route, tg_time, with_retry

#: How long the bot waits for an Apply (or a config test) to end before it stops watching.
WATCH_FOR = 30 * 60
WATCH_EVERY = 10
#: Panel pages the Mini App may open for an admin (the "to" of its address).
APP_PAGES = {"scanner": "scanner", "config-tester": "config-tester", "apply": "apply", "nodes": "nodes"}
MAX_FAILED_SHOWN = 12


def allowed(ctx: Ctx) -> bool:
    return advanced.is_on() and ctx.admin is not None and ctx.admin.mode == AdminMode.super_admin


def app_url(page: str) -> str | None:
    """The Mini App's address that signs the admin in and opens ``page`` of the panel."""
    from .accounts import panel_app_url

    from .ui import can_open_as_app

    base = panel_app_url()
    url = f"{base}?to={page}" if base and page in APP_PAGES else None
    return url if can_open_as_app(url) else None


def _when(ts: float | None, lang: str) -> str:
    if not ts:
        return t(T.never, lang)
    moment = datetime.datetime.fromtimestamp(ts)
    return tg_time(moment, "r", moment.strftime("%Y-%m-%d %H:%M"))


# --------------------------------------------------------------------------- apply


def _apply_api():
    from hiddifypanel.panel.commercial.restapi.v2.admin import apply_api

    return apply_api


def apply_screen(ctx: Ctx, note: str | None = None) -> Screen:
    api = _apply_api()
    running = api.running_actions()
    last = api._last_runs().get("apply") or {}
    lines = [f"🛠 <b>{ctx.tr(T.op_apply_title)}</b>", RULE, f"<i>{ctx.tr(T.op_apply_hint)}</i>", ""]
    if running:
        lines.append(f"⏳ {ctx.tr(T.op_running, what=h(', '.join(running)))}")
    lines.append(f"🕘 {ctx.tr(T.op_last_apply)}: {_when(last.get('mtime'), ctx.lang)}" + (f"  {'✅' if last.get('finished') else '⚠️'}" if last else ""))
    if note:
        lines += ["", f"✅ <i>{h(note)}</i>"]
    rows = []
    if not running:
        rows.append([btn(ctx.tr(T.op_apply_now), Cb.apply, "ask", style=Style.primary)])
    if url := app_url("apply"):
        rows.append([app_btn(f"🖥 {ctx.tr(T.op_open_page)}", url)])
    rows.append([btn(ctx.tr(T.refresh), Cb.apply), btn(ctx.tr(T.back), Cb.back)])
    return Screen("\n".join(lines), keyboard(*rows))


def _watch_apply(chat_id: int, lang: str, started: float) -> None:
    """In the background: tells the admin when the Apply is over."""
    api = _apply_api()
    time.sleep(WATCH_EVERY)
    deadline = started + WATCH_FOR
    while time.time() < deadline and "apply" in api.running_actions():
        time.sleep(WATCH_EVERY)
    if time.time() >= deadline:
        return
    finished = (api._last_runs().get("apply") or {}).get("finished")
    text = f"✅ {t(T.op_apply_done, lang)}" if finished else f"⚠️ {t(T.op_apply_unsure, lang)}"
    rows = [[app_btn(f"🖥 {t(T.op_open_page, lang)}", url)]] if (url := app_url("apply")) else []
    try:
        with_retry(lambda: bot.send_message(chat_id, text, reply_markup=keyboard(*rows) if rows else None), attempts=3)
    except Exception as e:
        logger.debug(f"tgbot: apply end not told: {e}")


@route(Cb.apply, admin=True)
def show_apply(ctx: Ctx, args: list[str]) -> None:
    """ap → the screen · ap:ask → confirm · ap:go → apply."""
    if not allowed(ctx):
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    step = args[0] if args else ""
    if step == "ask":
        ctx.toast()
        return ctx.show(Screen(f"🛠 <b>{ctx.tr(T.op_apply_title)}</b>\n{RULE}\n{ctx.tr(T.op_apply_confirm)}", keyboard([btn(ctx.tr(T.confirm), Cb.apply, "go", style=Style.success), btn(ctx.tr(T.cancel), Cb.apply)])))
    if step == "go":
        from .miniapp import needs_unlock

        if needs_unlock(ctx, "apply", "ap:go"):
            return
        api = _apply_api()
        try:
            api.start_action("apply")
        except Exception as e:  # another action is running, or the panel is too old: its own message
            description = getattr(e, "description", None) or getattr(e, "message", None) or str(e)
            logger.info(f"tgbot: apply not started: {description}")
            return ctx.toast(ctx.tr(T.op_not_started), alert=True)
        started, chat_id, lang = time.time(), ctx.chat_id, ctx.lang
        background(lambda: _watch_apply(chat_id, lang, started))
        ctx.toast(ctx.tr(T.op_apply_started))
        return ctx.show(apply_screen(ctx, ctx.tr(T.op_apply_started)))
    ctx.toast()
    ctx.show(apply_screen(ctx))


# --------------------------------------------------------------------------- config test


def _health():
    from hiddifypanel.proxy_v3 import config_health

    return config_health


def result_lines(lang: str, result: dict | None) -> list[str]:
    if not result:
        return [t(T.op_no_test, lang)]
    lines = [f"🕘 {_when(result.get('at'), lang)}"]
    for app, summary in (result.get("apps") or {}).items():
        name = {"xray": "Xray / v2ray", "hiddify": "Hiddify"}.get(app, app)
        if summary.get("error"):
            lines.append(f"⚠️ <b>{h(name)}</b>: {t(T.op_test_error, lang)} <i>{h(summary['error'][:120])}</i>")
            continue
        total, ok = int(summary.get("total") or 0), int(summary.get("ok") or 0)
        mark = "✅" if total and ok >= total else ("⚠️" if ok else "❌")
        lines.append(f"{mark} <b>{h(name)}</b>: {t(T.op_test_ok, lang, ok=ok, total=total)}")
        failed = summary.get("failed") or []
        if failed:
            shown = "\n".join(f"❌ {h(f.get('name', '?'))[:60]}" for f in failed[:MAX_FAILED_SHOWN])
            more = f"\n… +{len(failed) - MAX_FAILED_SHOWN}" if len(failed) > MAX_FAILED_SHOWN else ""
            lines.append(f"<blockquote expandable>{shown}{more}</blockquote>")
    return lines


def test_screen(ctx: Ctx, note: str | None = None) -> Screen:
    health = _health()
    running = health.is_running()
    lines = [f"🧪 <b>{ctx.tr(T.op_test_title)}</b>", RULE, f"<i>{ctx.tr(T.op_test_hint)}</i>", ""]
    if running:
        lines += [f"⏳ {ctx.tr(T.op_testing)}", ""]
    lines += result_lines(ctx.lang, health.last())
    if note:
        lines += ["", f"✅ <i>{h(note)}</i>"]
    rows = []
    if not running:
        rows.append([btn(ctx.tr(T.op_test_now), Cb.cfgtest, "go", style=Style.primary)])
    if url := app_url("config-tester"):
        rows.append([app_btn(f"🖥 {ctx.tr(T.op_open_page)}", url)])
    rows.append([btn(ctx.tr(T.refresh), Cb.cfgtest), btn(ctx.tr(T.back), Cb.back)])
    return Screen("\n".join(lines), keyboard(*rows))


def _watch_test(chat_id: int, lang: str) -> None:
    health = _health()
    deadline = time.time() + WATCH_FOR
    time.sleep(WATCH_EVERY)
    while time.time() < deadline and health.is_running():
        time.sleep(WATCH_EVERY)
    if health.is_running():
        return
    text = "\n".join([f"🧪 <b>{t(T.op_test_title, lang)}</b>", RULE, *result_lines(lang, health.last())])
    try:
        with_retry(lambda: bot.send_message(chat_id, text, reply_markup=keyboard([btn(f"🧪 {t(T.op_test_title, lang)}", Cb.cfgtest)])), attempts=3)
    except Exception as e:
        logger.debug(f"tgbot: config test result not told: {e}")


@route(Cb.cfgtest, admin=True)
def show_test(ctx: Ctx, args: list[str]) -> None:
    """ct → the last result · ct:go → test now."""
    if not allowed(ctx):
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    if args[:1] == ["go"]:
        from flask import current_app

        if not _health().start_in_background(current_app._get_current_object()):
            return ctx.toast(ctx.tr(T.op_testing), alert=True)
        chat_id, lang = ctx.chat_id, ctx.lang
        background(lambda: _watch_test(chat_id, lang))
        ctx.toast(ctx.tr(T.op_test_started))
        return ctx.show(test_screen(ctx, ctx.tr(T.op_test_started)))
    ctx.toast()
    ctx.show(test_screen(ctx))


# --------------------------------------------------------------------------- the keys


def status_rows(ctx: Ctx) -> list[list]:
    """The status screen's keys to these (Advanced, super admins)."""
    if not allowed(ctx):
        return []
    row = [btn(f"🛠 {ctx.tr(T.op_apply_title)}", Cb.apply), btn(f"🧪 {ctx.tr(T.op_test_title)}", Cb.cfgtest)]
    from .updates import allowed as may_update

    rows = [row, [btn(ctx.tr(T.up_key), Cb.update, style=Style.primary)]] if may_update(ctx) else [row]
    if url := app_url("scanner"):
        rows.append([app_btn(ctx.tr(T.op_scanner), url, style=Style.primary)])
    return rows
