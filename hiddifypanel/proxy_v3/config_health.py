"""Config health: the panel tests its own subscription every few hours and remembers which configs work.

It runs the config tester (``config_tester.run``) on the subscription of one active user, as the Xray apps
(v2rayN / v2rayNG / Happ) and as the Hiddify app get it, from the server itself. A config that does not work from
the server never works for anyone (a wrong template, a core that rejects it, an inbound that is missing), so these
are the ones worth an admin's attention; filtering in Iran is another matter and is not tested here.

The last result is kept in redis; when configs break that worked in the previous check, the super admins hear about
it from the Telegram bot (when there is one).
"""

from __future__ import annotations

import json
import threading
import time

from loguru import logger

from hiddifypanel.cache import redis_client

_LAST = "hiddify:config-health:last"
_RUNNING = "hiddify:config-health:running"
#: (app name, path after the user's page, user agent): what each kind of app downloads
APPS = (
    ("xray", "xray/", "v2rayN/7.0"),
    ("hiddify", "", "HiddifyNext/5.0.2 (linux) like ClashMeta v2ray sing-box"),
)
MAX_FAILED_LISTED = 60
#: Cloudflare's, not Google's: panels often send Google through WARP, and a WARP hiccup is not a broken config
TEST_URL = "https://cp.cloudflare.com/generate_204"
#: two requests per config: one dropped request is not an alarm
REPEATS = 2
#: seconds before the failed configs are tested once more (a reload of the cores takes a few seconds)
RETRY_AFTER = 30


def last() -> dict | None:
    raw = redis_client.get(_LAST)
    return json.loads(raw) if raw else None


def is_running() -> bool:
    return bool(redis_client.exists(_RUNNING))


def _probe_user():
    """An active user the test can download the subscription of (the oldest one: the most likely to stay)."""
    from hiddifypanel.models import User

    for user in User.query.filter(User.enable.is_(True)).order_by(User.id).limit(200):
        if user.is_active:
            return user
    return None


def _host() -> str:
    from hiddifypanel.models import Domain

    names = [d.domain for d in Domain.get_domains() if d.domain and "*" not in d.domain] + [Domain.get_panel_link() or ""]
    return next((n for n in names if n), "")


def _is_status_line(event: dict) -> bool:
    """The subscription's first entry shows the user's usage and days ("⏳ 1.2/50GB 📅 27 days"): not a config."""
    name = str(event.get("name") or "").strip()
    return name.startswith("⏳") or "📅" in name


def check() -> dict | None:
    """Tests every config once per app; returns (and keeps) the summary. None when there is nothing to test."""
    from hiddifypanel.panel import hiddify
    from hiddifypanel.proxy_v3 import config_tester
    from hiddifypanel.proxy_v3.config_tester_types import TesterError

    user, host = _probe_user(), _host()
    if user is None or not host:
        return None
    page = hiddify.get_account_panel_link(user, host)
    result: dict = {"at": int(time.time()), "user": user.name, "apps": {}}
    for app, path, agent in APPS:
        summary: dict = {"total": 0, "ok": 0, "failed": [], "error": ""}
        originals: list = []  # the failed configs, to test once more
        try:
            for event in config_tester.run(page + path, agent, test_url=TEST_URL, workers=8, timeout=10, repeats=REPEATS):
                if event.get("event") == "start":
                    summary["total"] = int(event.get("total") or 0)
                elif event.get("event") == "result" and _is_status_line(event):
                    summary["total"] -= 1
                elif event.get("event") == "result":
                    if event.get("ok"):
                        summary["ok"] += 1
                    else:
                        summary["failed"].append({"name": str(event.get("name") or ""), "error": str(event.get("error") or "")[:200]})
                        originals.append(event.get("original"))
            if originals:
                # A config that failed is tested once more a little later: the cores reload when an admin saves a
                # domain or applies, and the configs tested at that moment fail although nothing is wrong with them.
                time.sleep(RETRY_AFTER)
                passed = set()
                for event in config_tester.rerun(originals, test_url=TEST_URL, workers=8, timeout=10, repeats=REPEATS):
                    if event.get("event") == "result" and event.get("ok"):
                        passed.add(str(event.get("name") or ""))
                summary["failed"] = [f for f in summary["failed"] if f["name"] not in passed]
                summary["ok"] += len(passed)
        except TesterError as e:
            summary["error"] = str(e)
        except Exception as e:  # one app failing must not lose the other's result
            logger.exception("config health: {} failed", app)
            summary["error"] = type(e).__name__
        summary["failed"] = summary["failed"][:MAX_FAILED_LISTED]
        result["apps"][app] = summary
    previous = last()
    redis_client.set(_LAST, json.dumps(result))
    _notify(previous, result)
    return result


def run_locked() -> dict | None:
    """The scheduled run (and "Check now"): one at a time, whatever the number of workers."""
    if not redis_client.set(_RUNNING, 1, nx=True, ex=3600):
        return None
    try:
        return check()
    finally:
        redis_client.delete(_RUNNING)


def start_in_background(app) -> bool:
    """"Check now" from the page: the test takes a minute or two, the request does not wait for it."""
    if is_running():
        return False

    def work():
        with app.app_context():
            run_locked()

    threading.Thread(target=work, name="config-health", daemon=True).start()
    return True


def _notify(previous: dict | None, current: dict) -> None:
    """The super admins hear when configs break that worked before (not every time the same ones are still broken)."""
    if previous is None:
        return
    newly: list[str] = []
    for app, summary in current["apps"].items():
        before = {f["name"] for f in (previous.get("apps", {}).get(app, {}).get("failed") or [])}
        newly += [f"{f['name']} ({app})" for f in summary["failed"] if f["name"] not in before]
    if not newly:
        return
    try:
        from hiddifypanel.models import AdminUser, ConfigEnum, hconfig
        from hiddifypanel.models.admin import AdminMode

        if not hconfig(ConfigEnum.telegram_bot_token):
            return
        from hiddifypanel.panel.commercial.telegrambot import bot

        fa = str(getattr(hconfig(ConfigEnum.admin_lang), "value", hconfig(ConfigEnum.admin_lang)) or "").startswith("fa")
        head = "⚠️ این کانفیگ‌ها از خود سرور دیگر کار نمی‌کنند:" if fa else "⚠️ These configs stopped working (tested from the server):"
        tail = "جزئیات: داشبورد پنل ← سلامت کانفیگ‌ها" if fa else "Details: the panel's dashboard › Config health"
        text = "\n".join([head, *("• " + n for n in newly[:20]), *(["…"] if len(newly) > 20 else []), "", tail])
        for admin in AdminUser.query.filter(AdminUser.mode == AdminMode.super_admin, AdminUser.telegram_id.isnot(None)):
            try:
                bot.send_message(admin.telegram_id, text)
            except Exception as e:
                logger.warning("config health: telegram to {} failed: {}", admin.id, e)
    except Exception:
        logger.exception("config health: notify failed")
