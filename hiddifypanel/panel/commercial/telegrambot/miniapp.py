"""Advanced mode: what only a Mini App can do, on one small page of the bot (api/v1/tgbot/app/act/).

- Biometric lock: an admin chooses (in the bot's Settings) which actions need their fingerprint or face: deleting a
  user, bulk actions, Apply, the backup, changing an admin. Such an action first opens the page, which asks the
  phone's biometrics (Telegram's BiometricManager); when it says yes, the bot sends the action's key again and that
  one press goes through (two minutes, once).
- QR scan: the admin scans a user's QR code (their page or subscription link) with the phone's camera and the bot
  sends that user's card, when the user is theirs.
- Emoji status: a user puts Hiddify's icon by their name in Telegram until their package ends (Telegram Premium).
- Haptics: the page's buttons and results tap the phone (Telegram's HapticFeedback).

Every page is opened with a one-time token the bot made for that chat; the result comes back with Telegram's signed
initData, and only the chat the token was made for may use it.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets

from loguru import logger
from telebot import types

from hiddifypanel.cache import redis_client
from hiddifypanel.models import BotPref

from . import advanced, bot
from .texts import LANGUAGES, T, t
from .ui import RULE, Cb, Ctx, Screen, Style, app_btn, btn, can_open_as_app, keyboard, route, with_retry

#: Actions an admin can lock, in the order the settings show them
LOCKABLE = ("del", "bulk", "apply", "backup", "admin")
_LOCK_TEXT = {"del": T.bl_del, "bulk": T.bl_bulk, "apply": T.bl_apply, "backup": T.bl_backup, "admin": T.bl_admin}
LOCK_PREF = "adv_lock"
#: sha256 of the key kept in the phone's biometric storage (Telegram gives it back only after the fingerprint/face)
LOCK_KEY_PREF = "adv_lock_key"
TOKEN_TTL = 10 * 60
UNLOCK_TTL = 120
_PENDING_KEY = "tgbot:act:{}"
_UNLOCKED = "tgbot:unlocked:{}:{}"
_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
#: The emoji status icon (from the bot's icon set): the shield
STATUS_EMOJI = "🛡"
MAX_STATUS_DAYS = 365


# --------------------------------------------------------------------------- tokens and the page's address


def page_url(kind: str, token: str, **extra: object) -> str | None:
    from .accounts import panel_app_url

    base = panel_app_url()
    if not base:
        return None
    query = "&".join([f"do={kind}", f"t={token}", *(f"{k}={v}" for k, v in extra.items())])
    url = f"{base}act/?{query}"
    return url if can_open_as_app(url) else None


def _bot_id() -> int:
    """The agent's bot this runs in (its Mini App pages are signed with that bot's token), 0 for the panel's."""
    from hiddifypanel.panel.commercial.restapi.v1.tgbot import managed_bot

    m = managed_bot.get()
    return m.bot_id if m else 0


def new_token(chat_id: int, kind: str, **data: object) -> str:
    token = secrets.token_urlsafe(18)
    redis_client.set(_PENDING_KEY.format(token), json.dumps({"chat": chat_id, "kind": kind, "bot": _bot_id(), **data}), ex=TOKEN_TTL)
    return token


def lasting_token(chat_id: int, kind: str, **data: object) -> str:
    """A token for a key drawn again and again (the users list, a user's card): the same one while it is unused,
    so redrawing a screen does not leave a new token behind each time."""
    last = f"tgbot:act:last:{_bot_id()}:{chat_id}:{kind}:{data.get('lang', '')}"
    token = redis_client.get(last)
    token = token.decode() if isinstance(token, bytes) else token
    if token and redis_client.expire(_PENDING_KEY.format(token), TOKEN_TTL):  # still unused: ten more minutes
        redis_client.expire(last, TOKEN_TTL)
        return token
    token = new_token(chat_id, kind, **data)
    redis_client.set(last, token, ex=TOKEN_TTL)
    return token


def peek_token(token: str) -> dict | None:
    """The token's data, left in place."""
    if not token or len(token) > 64:
        return None
    raw = redis_client.get(_PENDING_KEY.format(token))
    try:
        return json.loads(raw) if raw else None
    except ValueError:
        return None


def take_token(token: str) -> dict | None:
    """The token's data, once (it is deleted as it is read)."""
    if not token or len(token) > 64:
        return None
    key = _PENDING_KEY.format(token)
    pipe = redis_client.pipeline()
    pipe.get(key)
    pipe.delete(key)
    raw, _ = pipe.execute()
    try:
        return json.loads(raw) if raw else None
    except ValueError:
        return None


# --------------------------------------------------------------------------- biometric lock


def locked(chat_id: int) -> set[str]:
    try:
        raw = BotPref.get(chat_id, LOCK_PREF)
    except Exception:
        return set()
    return {a for a in raw.split(",") if a in LOCKABLE}


def set_locked(chat_id: int, actions: set[str]) -> None:
    BotPref.put(chat_id, LOCK_PREF, ",".join(a for a in LOCKABLE if a in actions))


def _lock_key(chat_id: int) -> str:
    try:
        return BotPref.get(chat_id, LOCK_KEY_PREF) or ""
    except Exception:
        return ""


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def reset_locks(chat_id: int) -> None:
    """No lock and no phone key for this chat (the admin opened their panel link again: a new phone, a lost key)."""
    BotPref.put(chat_id, LOCK_PREF, "")
    BotPref.put(chat_id, LOCK_KEY_PREF, "")


def _digest(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()[:24]


def needs_unlock(ctx: Ctx, action: str, data: str, *, force: bool = False) -> bool:
    """True when ``action`` is locked for this admin (``force``: asked anyway, as for changing the locks) and not
    unlocked yet: the lock screen is shown instead. A press unlocked by the biometrics a moment ago goes through
    (once). Without a key on the phone yet, the confirmation also puts one there."""
    if not advanced.is_on() or (not force and action not in locked(ctx.chat_id)):
        return False
    key = _UNLOCKED.format(ctx.chat_id, _digest(data))
    if redis_client.get(key):
        redis_client.delete(key)
        return False
    setting = not _lock_key(ctx.chat_id)
    token = new_token(ctx.chat_id, "lock", data=data, action=action, lang=ctx.lang, set=setting)
    url = page_url("lock", token, m="set" if setting else "use")
    if url is None:  # no address a Mini App can open: the lock cannot be asked, the admin is not stuck
        logger.warning("tgbot: biometric lock skipped: the panel has no domain a Mini App can open")
        return False
    ctx.toast()
    ctx.show(
        Screen(
            f"🔐 <b>{ctx.tr(T.bl_title)}</b>\n{RULE}\n{ctx.tr(T.bl_ask, what=ctx.tr(_LOCK_TEXT[action]))}",
            keyboard([app_btn(ctx.tr(T.bl_confirm), url, Style.primary)], [btn(ctx.tr(T.back), Cb.back)]),
        )
    )
    return True


def _unlocked(pending: dict) -> None:
    chat, data = int(pending["chat"]), str(pending["data"])
    lang = str(pending.get("lang") or "en")
    redis_client.set(_UNLOCKED.format(chat, _digest(data)), 1, ex=UNLOCK_TTL)
    action = str(pending.get("action") or "")
    label = t(_LOCK_TEXT[action], lang) if action in _LOCK_TEXT else t(T.confirm, lang)
    markup = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(f"✅ {label}", callback_data=data)]])
    with_retry(lambda: bot.send_message(chat, f"🔓 {t(T.bl_ok, lang)}", reply_markup=markup), attempts=3)


def lock_screen(ctx: Ctx, note: str | None = None) -> Screen:
    on = locked(ctx.chat_id)
    lines = [f"🔐 <b>{ctx.tr(T.bl_title)}</b>", RULE, f"<i>{ctx.tr(T.bl_hint)}</i>"]
    if note:
        lines += ["", f"✅ <i>{note}</i>"]
    rows = [[btn(f"{'🔒' if a in on else '🔓'} {ctx.tr(_LOCK_TEXT[a])}", Cb.lock, a, 0 if a in on else 1, style=Style.success if a in on else None)] for a in LOCKABLE]
    rows.append([btn(ctx.tr(T.back), Cb.admin_settings)])
    return Screen("\n".join(lines), keyboard(*rows))


@route(Cb.lock, admin=True)
def show_lock(ctx: Ctx, args: list[str]) -> None:
    """lk → the actions · lk:<action>:<1|0> → lock or unlock it."""
    if not advanced.is_on():
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    if len(args) >= 2 and args[0] in LOCKABLE and args[1] in ("0", "1"):
        from hiddifypanel.database import db

        # Changing a lock asks the biometrics too (else whoever holds the phone could just take it off), and the
        # first one puts the key in the phone (so a phone without biometrics never gets locked out)
        if needs_unlock(ctx, args[0], ":".join([Cb.lock.value, *args]), force=True):
            return
        on = locked(ctx.chat_id)
        if args[1] == "1":
            on.add(args[0])
        else:
            on.discard(args[0])
        set_locked(ctx.chat_id, on)
        db.session.commit()
        ctx.toast(ctx.tr(T.adv_saved))
        return ctx.show(lock_screen(ctx, ctx.tr(T.adv_saved)))
    ctx.toast()
    ctx.show(lock_screen(ctx))


# --------------------------------------------------------------------------- QR scan


def scan_button(ctx: Ctx) -> types.InlineKeyboardButton | None:
    if not advanced.is_on():
        return None
    url = page_url("scan", lasting_token(ctx.chat_id, "scan", lang=ctx.lang))
    return app_btn(ctx.tr(T.qs_button), url) if url else None


def _scanned(pending: dict, text: str) -> None:
    from hiddifypanel.models import AdminUser, User

    from . import accounts
    from .admin import card_screen

    chat, lang = int(pending["chat"]), str(pending.get("lang") or "en")
    admin = AdminUser.query.filter(AdminUser.telegram_id == chat, AdminUser.deleted.is_(False)).first()
    match = _UUID.search(text or "")
    user = User.query.filter(User.uuid == match.group(0).lower(), User.deleted.is_(False)).first() if match and admin else None
    user = accounts.get_visible(admin, user.id) if user and admin else None
    if user is None:
        with_retry(lambda: bot.send_message(chat, f"🔎 {t(T.qs_not_found, lang)}"), attempts=3)
        return
    screen = card_screen(Ctx(chat, lang, admin=admin), user)
    with_retry(lambda: bot.send_message(chat, screen.text, reply_markup=screen.markup), attempts=3)


# --------------------------------------------------------------------------- emoji status


def status_button(ctx: Ctx) -> types.InlineKeyboardButton | None:
    """For a user with a package: Hiddify's icon by their name until it ends."""
    from .icons import icon_for

    user = ctx.user
    if not advanced.is_on() or user is None:
        return None
    emoji_id = icon_for(STATUS_EMOJI)
    if not emoji_id:
        return None
    days = user.remaining_days if user.start_date else user.package_days
    days = max(1, min(int(days or 1), MAX_STATUS_DAYS))
    url = page_url("emoji", lasting_token(ctx.chat_id, "emoji", lang=ctx.lang), e=emoji_id, d=days * 86400)
    return app_btn(ctx.tr(T.es_button), url) if url else None


# --------------------------------------------------------------------------- the page's answer


def answer(init_data: str, body: dict, bot_token: str) -> tuple[dict, int]:
    """The page's result: signed by Telegram, for the token's own chat."""
    from hiddifypanel.panel.commercial.restapi.v1.tgbot import managed_bot

    from . import resellers
    from .webapp import telegram_user_id

    token = str(body.get("t") or "")
    pending = peek_token(token)
    if pending is None:
        return {"error": "expired"}, 403
    # The page was opened from the bot that made the token: Telegram signed it with that bot's token
    bot_id = int(pending.get("bot") or 0)
    managed = resellers.find(bot_id) if bot_id else None
    if bot_id and (managed is None or not resellers.allowed()):
        return {"error": "expired"}, 403
    tg_id = telegram_user_id(init_data, managed.token if managed else bot_token)
    if tg_id is None or int(pending.get("chat") or 0) != tg_id:  # a forged or foreign answer leaves the token as it was
        return {"error": "invalid_sign_in"}, 403
    if take_token(token) is None:  # used a moment ago by another answer
        return {"error": "expired"}, 403
    kind = pending.get("kind")
    mark = managed_bot.set(managed)  # the answer comes from that same bot
    try:
        if kind == "lock" and body.get("ok") is True:
            if pending.get("set"):  # the first confirmation: the key now kept in the phone's biometric storage
                secret = str(body.get("secret") or "")
                if len(secret) < 32:
                    return {"error": "refused"}, 400
                from hiddifypanel.database import db

                BotPref.put(int(pending["chat"]), LOCK_KEY_PREF, _sha(secret))
                db.session.commit()
            else:  # Telegram gives the key back only after the fingerprint/face: a page that only says "ok" is not enough
                import hmac

                stored = _lock_key(int(pending["chat"]))
                if not stored or not hmac.compare_digest(stored, _sha(str(body.get("token") or ""))):
                    return {"error": "refused"}, 403
            _unlocked(pending)
        elif kind == "scan":
            _scanned(pending, str(body.get("text") or "")[:500])
        elif kind == "emoji":
            pass  # Telegram itself set it (or the person said no): nothing to keep
        else:
            return {"error": "refused"}, 400
    except Exception as e:
        logger.exception(f"tgbot: mini app {kind} failed: {e}")
        return {"error": "failed"}, 500
    finally:
        managed_bot.reset(mark)
    return {"ok": True}, 200


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hiddify</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
:root{color-scheme:light dark}
body{margin:0;min-height:100vh;display:grid;place-items:center;font:16px system-ui,sans-serif;
background:var(--tg-theme-bg-color,#0f172a);color:var(--tg-theme-text-color,#e2e8f0)}
.box{text-align:center;padding:28px;max-width:340px}
.icon{font-size:64px;margin-bottom:12px}
#m{line-height:1.6;opacity:.9}
button{margin-top:22px;width:100%;padding:14px;border:0;border-radius:14px;font:600 16px system-ui,sans-serif;
background:var(--tg-theme-button-color,#2563eb);color:var(--tg-theme-button-text-color,#fff)}
.err{color:#ef4444}
</style></head>
<body><div class="box"><div class="icon" id="i">🔐</div><div id="m">…</div><button id="b" hidden></button></div>
<script>
const TEXTS = __TEXTS__, RTL = ['fa', 'ar', 'ur', 'ps'];
(function () {
  const tg = window.Telegram && Telegram.WebApp;
  const q = new URLSearchParams(location.search), kind = q.get('do'), token = q.get('t');
  const code = String((tg && tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.language_code) || '').toLowerCase().split(/[-_]/)[0];
  const L = TEXTS[code] || TEXTS['__DEFAULT__'] || TEXTS.en;
  document.documentElement.lang = code; document.documentElement.dir = RTL.includes(code) ? 'rtl' : 'ltr';
  const m = document.getElementById('m'), b = document.getElementById('b'), i = document.getElementById('i');
  const tap = (s) => { try { tg.HapticFeedback.impactOccurred(s || 'light'); } catch (e) {} };
  const buzz = (s) => { try { tg.HapticFeedback.notificationOccurred(s); } catch (e) {} };
  const fail = (t) => { buzz('error'); m.textContent = t; m.className = 'err'; b.hidden = false; b.textContent = L.close; b.onclick = () => tg.close(); };
  const send = async (extra) => {
    try {
      const r = await fetch('', {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(Object.assign({init_data: tg.initData, t: token}, extra))});
      if (!r.ok) return fail(L.failed);
      buzz('success'); m.textContent = L.done; setTimeout(() => tg.close(), 700);
    } catch (e) { fail(L.failed); }
  };
  if (!tg || !tg.initData || !token) { m.textContent = L.open_in_bot; return; }
  tg.ready(); tg.expand();
  if (kind === 'lock') {
    i.textContent = '🔐'; m.textContent = L.lock;
    const bm = tg.BiometricManager;
    const go = () => {
      tap('medium');
      if (!bm || !bm.isInited) return fail(L.no_bio);
      if (!bm.isBiometricAvailable) return fail(L.no_bio);
      const setting = q.get('m') === 'set';
      // The first time a random key goes into the phone's biometric storage; later Telegram gives it back only
      // after the fingerprint/face, and the server checks it
      const auth = () => bm.authenticate({reason: L.lock}, (ok, key) => {
        if (!ok) return fail(L.denied);
        if (setting) {
          const raw = new Uint8Array(32); crypto.getRandomValues(raw);
          const secret = Array.from(raw, (x) => x.toString(16).padStart(2, '0')).join('');
          return bm.updateBiometricToken(secret, (saved) => saved ? send({ok: true, secret: secret}) : fail(L.no_bio));
        }
        return key ? send({ok: true, token: key}) : fail(L.no_key);
      });
      if (bm.isAccessGranted) return auth();
      bm.requestAccess({reason: L.lock}, (granted) => granted ? auth() : fail(L.denied));
    };
    b.hidden = false; b.textContent = L.confirm; b.onclick = go;
    if (bm) bm.init(() => {});
  } else if (kind === 'scan') {
    i.textContent = '📷'; m.textContent = L.scan;
    const open = () => { tap(); tg.showScanQrPopup({text: L.scan}, (text) => { send({text: text}); return true; }); };
    b.hidden = false; b.textContent = L.scan_again; b.onclick = open;
    open();
  } else if (kind === 'emoji') {
    i.textContent = '⭐️'; m.textContent = L.emoji;
    const emoji = q.get('e'), duration = parseInt(q.get('d') || '0', 10);
    const set = () => {
      tap('medium');
      if (!tg.isVersionAtLeast || !tg.isVersionAtLeast('8.0') || !tg.setEmojiStatus) return fail(L.no_emoji);
      tg.setEmojiStatus(emoji, duration ? {duration: duration} : {}, (ok) => ok ? send({ok: true}) : fail(L.no_emoji));
    };
    b.hidden = false; b.textContent = L.emoji_set; b.onclick = set;
  } else { m.textContent = L.failed; }
})();
</script></body></html>"""


def page() -> str:
    from hiddifypanel.models import ConfigEnum, hconfig

    keys = {
        "lock": T.bl_page,
        "confirm": T.bl_confirm,
        "no_bio": T.bl_no_bio,
        "no_key": T.bl_no_key,
        "denied": T.bl_denied,
        "scan": T.qs_page,
        "scan_again": T.qs_again,
        "emoji": T.es_page,
        "emoji_set": T.es_set,
        "no_emoji": T.es_no,
        "done": T.ma_done,
        "failed": T.app_sign_in_failed,
        "open_in_bot": T.app_open_in_bot,
        "close": T.close,
    }
    texts = {code: {k: t(v, code) for k, v in keys.items()} for code in LANGUAGES}
    default = str(hconfig(ConfigEnum.lang) or "en")
    payload = json.dumps(texts, ensure_ascii=False).replace("</", "<\\/")
    return PAGE.replace("__TEXTS__", payload).replace("__DEFAULT__", default if default in LANGUAGES else "en")
