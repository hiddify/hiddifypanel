"""Telegram Mini App sign-in: Telegram signs ``initData`` with the bot token, so a valid signature proves which
Telegram account opened the panel (https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

MAX_AGE_SECONDS = 24 * 3600


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
(async () => {
  const tg = window.Telegram && Telegram.WebApp;
  const msg = document.getElementById('m');
  const fail = (text) => { document.getElementById('s').remove(); msg.className = 'err'; msg.textContent = text; };
  if (!tg || !tg.initData) return fail('Open this page from the Telegram bot.');
  tg.ready(); tg.expand();
  try {
    const res = await fetch('login/', {method: 'POST', credentials: 'same-origin',
      headers: {'Content-Type': 'application/json'}, body: JSON.stringify({init_data: tg.initData})});
    const body = await res.json();
    if (!res.ok || !body.redirect) return fail(body.error || 'Sign-in failed');
    location.replace(body.redirect);
  } catch (e) { fail(String(e)); }
})();
</script></body></html>
"""
