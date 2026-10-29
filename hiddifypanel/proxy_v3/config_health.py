"""Config health: the panel tests its own subscription every few hours and remembers which configs work.

It runs the config tester (``config_tester.run``) on the subscription of one active user, as the Xray apps
(v2rayN / v2rayNG / Happ) and as the Hiddify app get it, from the server itself. A config that does not work from
the server never works for anyone (a wrong template, a core that rejects it, an inbound that is missing), so these
are the ones worth an admin's attention; filtering in Iran is another matter and is not tested here.

The last result is kept in redis; when configs break that worked in the previous check, the super admins hear about
it from the Telegram bot (when there is one).
"""

from __future__ import annotations

import hmac
import ipaddress
import json
import secrets
import re
import threading
import time

from loguru import logger

from hiddifypanel.cache import redis_client

_LAST = "hiddify:config-health:last"
_RUNNING = "hiddify:config-health:running"
#: the check's own subscription request carries this token (?health_check=): it gets every config, the hidden ones too,
#: so a hidden config is tested again and comes back when it works
_TOKEN = "hiddify:config-health:token"
TOKEN_PARAM = "health_check"
#: (app name, path after the user's page, user agent): what each kind of app downloads
APPS = (
    ("xray", "xray/", "v2rayN/7.0"),
    ("hiddify", "", "HiddifyNext/5.0.2 (linux) like ClashMeta v2ray sing-box"),
)
MAX_FAILED_LISTED = 60
#: names of the configs that passed, kept to tell a failed config from a working one with the same name
MAX_PASSED_LISTED = 1000
#: a check older than this is not used to hide configs (the scheduled one runs every 6 hours)
HIDE_MAX_AGE = 24 * 3600
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


def _test_app(url: str, agent: str, app: str, verify: bool = True) -> dict:
    """Every config of the subscription as one kind of app gets it: {total, ok, failed, error, error_kind}."""
    from hiddifypanel.proxy_v3 import config_tester
    from hiddifypanel.proxy_v3.config_tester_types import TesterError

    summary: dict = {"total": 0, "ok": 0, "failed": [], "passed": [], "error": ""}
    try:
        for event in config_tester.run(url, agent, test_url=TEST_URL, workers=8, timeout=10, repeats=REPEATS, verify=verify):
            if event.get("event") == "start":
                summary["total"] = int(event.get("total") or 0)
            elif event.get("event") == "result" and _is_status_line(event):
                summary["total"] -= 1
            elif event.get("event") == "result":
                if event.get("ok"):
                    summary["ok"] += 1
                    summary["passed"].append(str(event.get("name") or ""))
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
            summary["passed"] += sorted(passed)
    except TesterError as e:
        summary["error"], summary["error_kind"] = _clean(str(e)), _error_kind(str(e))
    except Exception as e:  # one app failing must not lose the other's result
        logger.exception("config health: {} failed", app)
        summary["error"], summary["error_kind"] = type(e).__name__, "other"
    summary["failed"] = summary["failed"][:MAX_FAILED_LISTED]
    summary["passed"] = summary["passed"][:MAX_PASSED_LISTED]
    return summary


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
    token = secrets.token_urlsafe(24)
    redis_client.set(_TOKEN, token, ex=3600)
    query = f"?{TOKEN_PARAM}={token}"
    for app, path, agent in APPS:
        summary = _test_app(page + path + query, agent, app, verify)
        if summary["error"]:
            # The subscription could not be fetched (e.g. a reload of the cores right then): once more, later
            time.sleep(RETRY_AFTER)
            summary = _test_app(page + path + query, agent, app, verify)
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


# --- Hiding failed configs from the users (setting config_health_hide_failed) ---

_hidden_cache: tuple[float, dict[str, frozenset[str]]] | None = None
_HIDDEN_CACHE_SECONDS = 30


def config_name(name: str) -> str:
    """A config's name as the check and the renderer both see it: spaces collapsed, without the " §2" a client config
    adds to a repeated name."""
    return re.sub(r"\s+", " ", re.sub(r"\s*§\d+\s*$", "", name or "")).strip()


def _hidden_for_app(summary: dict) -> frozenset[str]:
    """The failed configs of one app that are safe to hide. Nothing when the subscription could not be tested, or when
    no config passed (then the test itself is broken, e.g. the server can not reach the test URL, and hiding would leave
    the users with nothing). A name that also passed (two configs with one name) is kept."""
    if summary.get("error") or not summary.get("failed") or not summary.get("ok"):
        return frozenset()
    passed = {config_name(n) for n in summary.get("passed") or []}
    return frozenset(n for f in summary["failed"] if (n := config_name(f.get("name", ""))) and n not in passed)


def hidden_configs() -> dict[str, frozenset[str]]:
    """App ("xray", "hiddify") → the names of the configs to leave out of the users' configs; empty when the setting is
    off or the last check is too old. Kept for a few seconds: it is asked for every proxy of every subscription."""
    global _hidden_cache
    from hiddifypanel.models import ConfigEnum, hconfig

    if not hconfig(ConfigEnum.config_health_hide_failed):
        return {}
    now = time.monotonic()
    if _hidden_cache and now - _hidden_cache[0] < _HIDDEN_CACHE_SECONDS:
        return _hidden_cache[1]
    result: dict[str, frozenset[str]] = {}
    try:
        current = last()
    except Exception:
        current = None
    if current and time.time() - int(current.get("at") or 0) < HIDE_MAX_AGE:
        result = {app: names for app, summary in (current.get("apps") or {}).items() if (names := _hidden_for_app(summary))}
    _hidden_cache = (now, result)
    return result


def is_check_request() -> bool:
    """The current request is the check's own subscription download (it must see the hidden configs too)."""
    try:
        from flask import has_request_context, request

        if not has_request_context() or not (got := request.args.get(TOKEN_PARAM)):
            return False
        want = redis_client.get(_TOKEN)
    except Exception:
        return False
    want = want.decode() if isinstance(want, bytes) else str(want or "")
    return bool(want) and hmac.compare_digest(got, want)


def health_app(app_group: str) -> str:
    """The checked app whose results apply to a client: the Xray apps get the "xray" check, every other client (the
    Hiddify app, sing-box, Clash) the "hiddify" one."""
    return "xray" if str(app_group or "").lower() == "xray" else "hiddify"
