"""Telegram Mini App sign-in: Telegram signs ``initData`` with the bot token, so a valid signature proves which
Telegram account opened the panel (https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

#: Telegram signs the data when the Mini App opens, and the page signs in right away: an hour is plenty, and a copy
#: of the data found later (a link shared by mistake) no longer signs anyone in.
MAX_AGE_SECONDS = 3600


def telegram_user_id(init_data: str, bot_token: str, *, now: float | None = None) -> int | None:
    """The Telegram user id in ``init_data`` when its signature is valid and fresh, else None."""
    if not init_data or not bot_token:
        return None
    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    received = fields.pop("hash", "")
    if not received:
        return None
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        return None
    try:
        if (now or time.time()) - int(fields.get("auth_date", "0")) > MAX_AGE_SECONDS:
            return None
        return int(json.loads(fields.get("user", "{}"))["id"])
    except (ValueError, KeyError, TypeError):
        return None


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hiddify</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
:root{color-scheme:light dark}
body{margin:0;min-height:100vh;display:grid;place-items:center;font:15px system-ui,sans-serif;
background:var(--tg-theme-bg-color,#0f172a);color:var(--tg-theme-text-color,#e2e8f0)}
.box{text-align:center;padding:24px}
.spin{width:36px;height:36px;margin:0 auto 16px;border-radius:50%;border:3px solid currentColor;border-top-color:transparent;
animation:r .8s linear infinite;opacity:.7}
@keyframes r{to{transform:rotate(1turn)}}
.err{color:#ef4444}
</style></head>
<body><div class="box"><div class="spin" id="s"></div><div id="m">Hiddify…</div></div>
<script>
const TEXTS = __TEXTS__, RTL = ['fa', 'ar', 'ur', 'ps'];
(async () => {
  const tg = window.Telegram && Telegram.WebApp;
  const code = String((tg && tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.language_code) || '').toLowerCase().split(/[-_]/)[0];
  const lang = TEXTS[code] ? code : '__DEFAULT__';
  const L = TEXTS[lang] || TEXTS.en;
  document.documentElement.lang = lang;
  if (RTL.includes(lang)) document.documentElement.dir = 'rtl';
  const msg = document.getElementById('m');
  msg.textContent = L.opening;
  const fail = (text) => { document.getElementById('s').remove(); msg.className = 'err'; msg.textContent = text; };
  if (!tg || !tg.initData) return fail(L.open_in_bot);
  tg.ready(); tg.expand();
  try {
    const res = await fetch('login/', {method: 'POST', credentials: 'same-origin',
      headers: {'Content-Type': 'application/json'}, body: JSON.stringify({init_data: tg.initData})});
    const body = await res.json();
    if (!res.ok || !body.redirect) return fail(L.failed);
    // A person's own page gets Telegram's data (the #tgWebApp… part), so it knows it is inside Telegram; the admin
    // panel never does: its address must not carry anything that could sign someone in.
    location.replace(body.keep_telegram ? body.redirect.split('#')[0] + location.hash : body.redirect);
  } catch (e) { fail(L.failed); }
})();
</script></body></html>
"""


def destination(tg_id: int, host: str) -> tuple[str, object | None, dict]:
    """Where the Telegram account ``tg_id`` (proved by Telegram's signature) may go: ("admin", the admin, answer) to
    the admin panel, ("user", the user, answer) to that person's own page, ("none", None, answer) for an account
    linked to nothing. Only the account linked to that very Telegram id: nobody reaches another one's panel or page."""
    from hiddifypanel.models import AdminUser, ConfigEnum, User, hconfig
    from hiddifypanel.panel import hiddify

    admin = AdminUser.query.filter(AdminUser.telegram_id == tg_id, AdminUser.deleted.is_(False)).first()
    if admin is not None:
        return "admin", admin, {"redirect": f"/{hconfig(ConfigEnum.proxy_path_admin)}/admin/v2/"}
    user = User.query.filter(User.telegram_id == tg_id, User.deleted.is_(False)).first()
    if user is not None:
        return "user", user, {"redirect": hiddify.get_account_panel_link(user, host), "keep_telegram": True}
    return "none", None, {"error": "This Telegram account is not linked to the panel. Send /start from the panel link first."}


def page() -> str:
    """The sign-in page with its few texts in every language the bot speaks (Telegram tells the page which one the
    person uses; the panel's default otherwise)."""
    from hiddifypanel.models import ConfigEnum, hconfig

    from .texts import LANGUAGES, T, t

    texts = {code: {"opening": t(T.app_opening, code), "open_in_bot": t(T.app_open_in_bot, code), "failed": t(T.app_sign_in_failed, code)} for code in LANGUAGES}
    default = str(hconfig(ConfigEnum.lang) or "en")
    # No text may close the <script> it sits in.
    payload = json.dumps(texts, ensure_ascii=False).replace("</", "<\\/")
    return PAGE.replace("__TEXTS__", payload).replace("__DEFAULT__", default if default in LANGUAGES else "en")
