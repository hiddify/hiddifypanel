"""Config health: the panel tests its own subscription every few hours and remembers which configs work.

It runs the config tester (``config_tester.run``) on the subscription of one active user, as the Xray apps
(v2rayN / v2rayNG / Happ) and as the Hiddify app get it, from the server itself. A config that does not work from
the server never works for anyone (a wrong template, a core that rejects it, an inbound that is missing), so these
are the ones worth an admin's attention; filtering in Iran is another matter and is not tested here.

The last result is kept in redis. A config that fails is tested again in a quarter of an hour; when it fails in two checks
in a row (a moment's hiccup does not), the super admins hear about it from the Telegram bot (when there is one).
"""

from __future__ import annotations

import ipaddress
import json
import re
import threading
import time

from loguru import logger

from hiddifypanel.cache import redis_client

_LAST = "hiddify:config-health:last"
_RUNNING = "hiddify:config-health:running"
#: (app name, path after the user's page): what each kind of app downloads; the user agent is the installed core's
APPS = (
    ("xray", "xray/"),
    ("hiddify", ""),
)
MAX_FAILED_LISTED = 60
#: Cloudflare's, not Google's: panels often send Google through WARP, and a WARP hiccup is not a broken config
TEST_URL = "https://cp.cloudflare.com/generate_204"
#: two requests per config: one dropped request is not an alarm
REPEATS = 2
#: seconds before the failed configs are tested once more (a reload of the cores takes a few seconds)
RETRY_AFTER = 30
#: seconds before a check that found new failures is run again: the alert waits for two failed checks in a row
CONFIRM_AFTER = 15 * 60


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


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


def _host() -> str:
    """The panel's own address for the test: a name first. The server's certificate is for its names (a domain,
    or the sslip.io name of its IP), so ``https://<bare IP>`` fails the certificate check although nothing is wrong."""
    from hiddifypanel.models import Domain

    names = [d.domain for d in Domain.get_domains() if d.domain and "*" not in d.domain] + [Domain.get_panel_link() or ""]
    names = [n for n in names if n]
    return next((n for n in names if not _is_ip(n)), names[0] if names else "")


#: why a subscription could not be tested, from the tester's message (the page explains each kind and where to look)
_KINDS = (
    ("certificate", re.compile(r"CERTIFICATE|SSLError|certificate verify|doesn't match|hostname mismatch|SSL", re.I)),
    ("timeout", re.compile(r"timed? ?out|Timeout", re.I)),
    ("dns", re.compile(r"NameResolution|Name or service not known|getaddrinfo|resolve", re.I)),
    ("unreachable", re.compile(r"Connection refused|ConnectionError|Max retries|Connection reset|unreachable", re.I)),
    ("http", re.compile(r"\b[45]\d\d (Client|Server) Error", re.I)),
    ("empty", re.compile(r"No config found|does not support this subscription|could not find any config", re.I)),
    ("core", re.compile(r"hiddify-core|xray", re.I)),
)


def _error_kind(message: str) -> str:
    return next((kind for kind, pattern in _KINDS if pattern.search(message)), "other")


def _clean(message: str) -> str:
    """The tester's message without the subscription's path (the proxy path and the user's UUID are secrets)."""
    message = re.sub(r"(url: |https?://[^/\s'\"]+)/[^\s'\"]*", r"\1/…", message)
    return re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "…", message, flags=re.I)[:500]


def _is_status_line(event: dict) -> bool:
    """The subscription's first entry shows the user's usage and days ("⏳ 1.2/50GB 📅 27 days"): not a config."""
    name = str(event.get("name") or "").strip()
    return name.startswith("⏳") or "📅" in name


def _is_group(event: dict) -> bool:
    """Xray's "Auto": the subscription's entry that balances over all the configs (each one is tested on its own)."""
    original = event.get("original")
    routing = original.get("routing") if isinstance(original, dict) else None
    return isinstance(routing, dict) and bool(routing.get("balancers"))


def _test_app(url: str, agent: str, app: str, verify: bool = True) -> dict:
    """Every config of the subscription as one kind of app gets it: {total, ok, failed, error, error_kind}."""
    from hiddifypanel.proxy_v3 import config_tester
    from hiddifypanel.proxy_v3.config_tester_types import TesterError

    summary: dict = {"total": 0, "ok": 0, "failed": [], "error": ""}
    #: every tested config's name → it works (the failed list is cut short; the proxies' health needs all of them)
    tested: dict[str, bool] = {}
    try:
        for event in config_tester.run(url, agent, test_url=TEST_URL, workers=8, timeout=10, repeats=REPEATS, verify=verify):
            if event.get("event") == "start":
                summary["total"] = int(event.get("total") or 0)
            elif event.get("event") == "result" and (_is_status_line(event) or _is_group(event)):
                summary["total"] -= 1
            elif event.get("event") == "result":
                tested[str(event.get("name") or "")] = bool(event.get("ok"))
                if event.get("ok"):
                    summary["ok"] += 1
                else:
                    summary["failed"].append({"name": str(event.get("name") or ""), "error": str(event.get("error") or "")[:200]})
        if summary["failed"]:
            # The failed configs get a second chance a little later: the cores reload when an admin saves a domain
            # or applies, and the configs tested at that moment fail although nothing is wrong with them. The whole
            # subscription is fetched and run again (its configs can not be re-run from the results alone).
            time.sleep(RETRY_AFTER)
            failed = {f["name"] for f in summary["failed"]}
            passed = set()
            for event in config_tester.run(url, agent, test_url=TEST_URL, workers=8, timeout=10, repeats=REPEATS, verify=verify):
                name = str(event.get("name") or "")
                if event.get("event") == "result" and name in failed and event.get("ok"):
                    passed.add(name)
            summary["failed"] = [f for f in summary["failed"] if f["name"] not in passed]
            summary["ok"] += len(passed)
            tested.update(dict.fromkeys(passed, True))
    except TesterError as e:
        summary["error"], summary["error_kind"] = _clean(str(e)), _error_kind(str(e))
    except Exception as e:  # one app failing must not lose the other's result
        logger.exception("config health: {} failed", app)
        summary["error"], summary["error_kind"] = type(e).__name__, "other"
    summary["failed"] = summary["failed"][:MAX_FAILED_LISTED]
    if not summary["error"]:
        summary["proxies"] = _proxy_status(tested)
    return summary


def _proxy_status(tested: dict[str, bool]) -> dict[str, str]:
    """Each custom proxy with tested configs → down (every config of it failed) / partial / up."""
    from hiddifypanel.proxy_v3 import config_tester_proxies

    try:
        results = [config_tester_proxies.TestedConfig(name=name, ok=ok) for name, ok in tested.items() if name]
        return {str(h["id"]): h["status"] for h in config_tester_proxies.health(results)}
    except Exception:  # the counts above stay useful without it
        logger.exception("config health: proxy status failed")
        return {}


def proxies_known(result: dict | None = None) -> bool:
    """The last check can tell which proxies are down: every app was tested, with this version's per-proxy record."""
    apps = ((last() if result is None else result) or {}).get("apps") or {}
    return all(not (apps.get(app) or {}).get("error") and "proxies" in (apps.get(app) or {}) for app, _path in APPS)


def dead_proxies(result: dict | None = None) -> list[dict]:
    """The custom proxies that work for nobody: every config of theirs failed as the Xray apps AND as the Hiddify app
    get it, in the last check. A proxy with one working config in either app stays out (it works somewhere), and so
    does everything when an app could not be tested at all. Only the ones still on: [{id, name}]."""
    from hiddifypanel.models import Child
    from hiddifypanel.models.custom_proxy import CustomProxy

    result = last() if result is None else result
    apps = (result or {}).get("apps") or {}
    statuses = []
    for app, _path in APPS:
        summary = apps.get(app) or {}
        if summary.get("error") or "proxies" not in summary:
            return []
        statuses.append(summary["proxies"])
    down = set.intersection(*({int(i) for i, status in s.items() if status == "down"} for s in statuses))
    if not down:
        return []
    proxies = CustomProxy.query.filter(CustomProxy.child_id == Child.current().id, CustomProxy.id.in_(down)).all()
    return [{"id": p.id, "name": p.name} for p in sorted(proxies, key=lambda p: p.name or "") if p.enable]


def check() -> dict | None:
    """Tests every config once per app; returns (and keeps) the summary. None when there is nothing to test."""
    from hiddifypanel.panel import hiddify

    user, host = _probe_user(), _host()
    if user is None or not host:
        return None
    page = hiddify.get_account_panel_link(user, host)
    # Only a bare IP to use: the server asks itself, and no certificate names an IP
    verify = not _is_ip(host)
    result: dict = {"at": int(time.time()), "user": user.name, "host": host, "apps": {}}
    from hiddifypanel.proxy_v3.config_tester import default_user_agent

    for app, path in APPS:
        agent = default_user_agent(app)
        summary = _test_app(page + path, agent, app, verify)
        if summary["error"]:
            # The subscription could not be fetched (e.g. a reload of the cores right then): once more, later
            time.sleep(RETRY_AFTER)
            summary = _test_app(page + path, agent, app, verify)
        result["apps"][app] = summary
    previous = last()
    send, suspects = _confirmed(previous, result)
    redis_client.set(_LAST, json.dumps(result))
    _notify(send)
    if suspects:
        _confirm_later()
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


def _failed(result: dict | None) -> set[str]:
    return {f"{f['name']} ({app})" for app, summary in ((result or {}).get("apps") or {}).items() for f in summary.get("failed") or []}


def _confirmed(previous: dict | None, current: dict) -> tuple[list[str], set[str]]:
    """(configs to tell the admins about, configs that failed for the first time).

    A config is told about once it failed in this check and the one before, and only once: ``current["confirmed"]``
    keeps the ones told about while they still fail. A check from before ``confirmed`` existed: its failures count as
    told about (they were, then)."""
    now = _failed(current)
    before = _failed(previous)
    told = set((previous or {}).get("confirmed", before)) & now
    confirmed = now & before
    current["confirmed"] = sorted(confirmed | told)
    send = sorted(confirmed - told) if previous is not None else []
    return send, now - before


def _confirm_later() -> None:
    """The check once more in a quarter of an hour, not at the next scheduled one in 6 hours. A restart of the panel
    loses it, and the scheduled check confirms then."""
    from flask import current_app

    try:
        app = current_app._get_current_object()
    except RuntimeError:
        return

    def work():
        with app.app_context():
            run_locked()

    timer = threading.Timer(CONFIRM_AFTER, work)
    timer.name, timer.daemon = "config-health-confirm", True
    timer.start()


def _notify(newly: list[str]) -> None:
    """The super admins hear when configs break that worked before (not every time the same ones are still broken)."""
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
