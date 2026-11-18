"""The live usage card: a Telegram widget (Bot API 10.4) in the user's chat, two rings (data used, days left) that
the bot updates silently after each usage update. The widget's HTML is fixed once sent, so its words are in the
person's language from the start; only its state (chat_data, a short JSON) changes. One card per chat.

pyTelegramBotAPI has no widget methods yet: the Bot API is called directly."""

from __future__ import annotations

import datetime
import json
import zlib
from html import escape

from loguru import logger

from hiddifypanel.cache import redis_client
from hiddifypanel.models import BotPref, ConfigEnum, User, hconfig

from . import accounts, bot
from .accounts import Status
from .texts import T, t
from .ui import bar, Cb, Ctx, fmt_gb, h, lang_of, route, tg_time

HTML_MAX = 32768
HTML_ZIPPED_MAX = 4096
DATA_MAX = 1024
#: A card is refreshed at most this often per user (each edit counts as a message sent).
REFRESH_EVERY = 5 * 60
PREF = "widget"
_THROTTLE = "tgbot:widget:sent:{}"
_LAST = "tgbot:widget:last:{}"
RTL = {"fa", "ar", "ur", "ps"}
#: Telegram refused widgets for this bot (they are rolled out gradually): the pinned card is used, widgets are tried
#: again a day later.
_UNAVAILABLE = "tgbot:widget:unavailable"
UNAVAILABLE_FOR = 24 * 3600


def available() -> bool:
    return not redis_client.get(_UNAVAILABLE)


def _not_allowed(error: Exception) -> bool:
    return "widget_not_allowed" in str(error).lower()

_STATUS_TEXT = {Status.active: T.status_active, Status.disabled: T.status_disabled, Status.expired: T.status_expired, Status.no_data: T.status_no_data}

# Only what the widget sandbox allows: no color-mix, no :has, no web fonts, no network.
_HTML = """<style>
:root{color-scheme:light dark}
body{margin:0;font-family:system-ui,sans-serif;color:var(--tg-theme-text-color);font-size:var(--tg-text-font-size,15px)}
.w{padding:12px 14px 10px}
.top{display:flex;align-items:center;justify-content:space-between;gap:8px}
.pill{font-size:12px;font-weight:600;padding:3px 9px;border-radius:99px;background:var(--tg-theme-secondary-bg-color);color:var(--c,#34c759)}
.on{font-size:12px;color:#34c759;font-weight:600}
.rings{display:flex;justify-content:space-around;margin:10px 0 4px}
.r{display:flex;flex-direction:column;align-items:center;gap:2px;min-width:0}
.r svg{width:96px;height:96px;transform:rotate(-90deg)}
.r circle{fill:none;stroke-width:9;stroke-linecap:round}
.bg{stroke:var(--tg-theme-secondary-bg-color)}
.fg{transition:stroke-dashoffset .9s ease,stroke .5s}
.v{margin-top:-66px;height:66px;font-weight:700;font-size:19px;text-align:center}
.v small{display:block;font-size:11px;font-weight:500;color:var(--tg-theme-hint-color)}
.l{font-size:13px;font-weight:600}
.s{font-size:12px;color:var(--tg-theme-hint-color);text-align:center}
.f{margin-top:8px;font-size:11px;color:var(--tg-theme-hint-color);text-align:center}
</style>
<div class="w" dir="__DIR__">
<div class="top"><b>__TITLE__</b><span id="on" class="on"></span><span id="st" class="pill"></span></div>
<div class="rings">
<div class="r"><svg viewBox="0 0 100 100"><circle class="bg" cx="50" cy="50" r="42"/><circle id="g1" class="fg" cx="50" cy="50" r="42"/></svg><div class="v" id="v1"></div><span class="l">__DATA__</span><span class="s" id="s1"></span></div>
<div class="r"><svg viewBox="0 0 100 100"><circle class="bg" cx="50" cy="50" r="42"/><circle id="g2" class="fg" cx="50" cy="50" r="42"/></svg><div class="v" id="v2"></div><span class="l">__TIME__</span><span class="s" id="s2"></span></div>
</div>
<div class="f" id="f"></div>
</div>
<script>
var L=__LABELS__,C=263.9,W=window.TelegramWidget;
function ring(id,p,col){var e=document.getElementById(id);e.style.strokeDasharray=C;e.style.strokeDashoffset=C*(1-Math.max(0,Math.min(1,p)));e.style.stroke=col}
function set(id,x){document.getElementById(id).innerHTML=x}
function draw(){var d={};try{d=JSON.parse(W&&W.chatData||"{}")}catch(e){}
if(d.s===undefined)return;
var p=d.p/100,col=p>=1?"#ff3b30":p>=.8?"#ff9f0a":"#0a84ff";ring("g1",p,col);
set("v1",Math.min(d.p,999)+"%<small>"+d.u+" / "+d.t+"</small>");set("s1",d.l+" "+L.left);
if(d.d<0){ring("g2",1,"#34c759");set("v2","∞<small>"+d.D+" "+L.days+"</small>");set("s2",L.notStarted)}
else{var q=d.D?d.d/d.D:0;ring("g2",q,d.d<=3?"#ff9f0a":"#34c759");set("v2",d.d+"<small>/ "+d.D+" "+L.days+"</small>");set("s2",L.daysLeft)}
var st=document.getElementById("st");st.textContent=L.st[d.s]||"";st.style.setProperty("--c",d.s=="active"?"#34c759":d.s=="no_data"?"#ff9f0a":"#ff3b30");
set("on",d.o?"● "+L.online:"");set("f",L.updated+" "+d.h)}
if(W){W.onEvent("chatDataChanged",draw);W.onEvent("activated",draw)}
draw();if(W&&W.ready)W.ready();
</script>"""


def html(lang: str) -> str:
    """The card in ``lang`` (its words are fixed once sent)."""
    labels = {
        "left": t(T.wg_left, lang),
        "days": t(T.wg_days, lang),
        "daysLeft": t(T.wg_days_left, lang),
        "notStarted": t(T.wg_not_started, lang),
        "online": t(T.online_now, lang),
        "updated": t(T.wg_updated, lang),
        "st": {s.value: t(k, lang) for s, k in _STATUS_TEXT.items()},
    }
    # "</" can not close the script from inside a JSON string
    payload = json.dumps(labels, ensure_ascii=False).replace("</", "<\\/")
    return (
        _HTML.replace("__DIR__", "rtl" if lang in RTL else "ltr")
        .replace("__TITLE__", escape(t(T.wg_title, lang)))
        .replace("__DATA__", escape(t(T.data, lang)))
        .replace("__TIME__", escape(t(T.time, lang)))
        .replace("__LABELS__", payload)
    )


def fits(markup: str) -> bool:
    raw = markup.encode()
    return len(raw) <= HTML_MAX and len(zlib.compress(raw, 9)) <= HTML_ZIPPED_MAX


def state(user: User, lang: str, now: datetime.datetime | None = None) -> str:
    """The card's chat_data: a short JSON of what it shows (at most 1024 bytes)."""
    now = now or datetime.datetime.now()
    used, total = user.current_usage_GB, user.usage_limit_GB
    data = {
        "s": accounts.status(user).value,
        "p": min(round(accounts.usage_ratio(user) * 100), 999) if user.usage_limit else 0,
        "u": fmt_gb(used, lang),
        "t": fmt_gb(total, lang),
        "l": fmt_gb(max(total - used, 0), lang),
        "d": -1 if user.start_date is None else max(user.remaining_days, 0),
        "D": user.package_days or 0,
        "o": 1 if accounts.is_online(user) else 0,
        "h": now.strftime("%H:%M"),
    }
    out = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return out if len(out.encode()) <= DATA_MAX else json.dumps({**data, "u": "", "t": "", "l": ""}, separators=(",", ":"))


def _api(method: str, **params) -> dict:
    from telebot import apihelper

    return apihelper._make_request(bot.token, method, "post", params=params)


def text_card(user: User, lang: str, now: datetime.datetime | None = None) -> str:
    """The live card as a message (where Telegram does not allow widgets): bars for data and days, the state, the
    time it was updated. The bot edits it in place."""
    now = now or datetime.datetime.now()
    st = accounts.status(user)
    used, total = user.current_usage_GB, user.usage_limit_GB
    ratio = accounts.usage_ratio(user) if user.usage_limit else 0
    lines = [f"📟 <b>{t(T.wg_title, lang)}</b>  ·  {h(user.name)}", ""]
    lines.append(f"📦 <code>{bar(ratio, 12)}</code>  <b>{min(round(ratio * 100), 999)}%</b>")
    lines.append(f"<i>{fmt_gb(used, lang)} / {fmt_gb(total, lang)}  ·  {fmt_gb(max(total - used, 0), lang)} {t(T.wg_left, lang)}</i>")
    if user.start_date is None:
        lines += ["", f"⏳ <i>{t(T.wg_not_started, lang)}</i>"]
    else:
        days, total_days = max(user.remaining_days, 0), user.package_days or 0
        lines += ["", f"⏳ <code>{bar(days / total_days if total_days else 0, 12)}</code>  <b>{days}</b> / {total_days} {t(T.wg_days, lang)}"]
    state_line = f"{accounts.STATUS_ICON[st]} {t(_STATUS_TEXT[st], lang)}"
    if accounts.is_online(user):
        state_line += f"  ·  ⚡️ {t(T.online_now, lang)}"
    lines += ["", state_line, f"<i>{t(T.wg_updated, lang)} {tg_time(now, 't', now.strftime('%H:%M'))}  ·  {t(T.wg_caption, lang)}</i>"]
    return "\n".join(lines)


def _kept(chat_id: int) -> tuple[str, int] | None:
    """("w" widget | "t" pinned message, its id) of the chat's live card."""
    raw = BotPref.get(chat_id, PREF)
    mode, _, value = raw.partition(":") if ":" in raw else ("w", "", raw)
    return (mode, int(value)) if value.isdigit() else None


def _keep(user: User, mode: str, message_id: int | None, data: str) -> None:
    from hiddifypanel.database import db

    BotPref.put(user.telegram_id, PREF, f"{mode}:{message_id}" if message_id else "")
    db.session.commit()
    redis_client.set(_LAST.format(user.id), data, ex=30 * 24 * 3600)


def send(user: User, lang: str) -> int | None:
    """A new live card in the user's chat (the previous one stops updating): Telegram's widget where the bot may
    send widgets, else a message pinned at the top that the bot edits. Its message id, or None."""
    old = _kept(user.telegram_id)
    data = state(user, lang)
    if available():
        markup = html(lang)
        if fits(markup):
            caption = f"📟 <b>{h(user.name)}</b>  ·  {t(T.wg_caption, lang)}"
            try:
                sent = _api("sendWidget", chat_id=user.telegram_id, html=markup, chat_data=data, caption=caption, parse_mode="HTML")
                _unpin(user.telegram_id, old)
                _keep(user, "w", int(sent["message_id"]), data)
                return int(sent["message_id"])
            except Exception as e:
                if not _not_allowed(e):
                    raise
                # Widgets are not open to this bot yet: the pinned card, and widgets tried again tomorrow
                redis_client.set(_UNAVAILABLE, 1, ex=UNAVAILABLE_FOR)
                logger.info("tgbot widget: widgets not allowed for this bot yet; using the pinned live card")
    sent = bot.send_message(user.telegram_id, text_card(user, lang), disable_notification=True)
    _unpin(user.telegram_id, old)
    try:
        bot.pin_chat_message(user.telegram_id, sent.message_id, disable_notification=True)
    except Exception as e:
        logger.debug(f"tgbot widget: live card not pinned: {e}")
    _keep(user, "t", sent.message_id, data)
    return sent.message_id


def _unpin(chat_id: int, old: tuple[str, int] | None) -> None:
    if old and old[0] == "t":
        try:
            bot.unpin_chat_message(chat_id, old[1])
        except Exception:
            pass


def refresh(user: User, *, force: bool = False) -> bool:
    """Update the user's live card if it changed and was not updated in the last few minutes. Never raises."""
    try:
        if not user.telegram_id:
            return False
        kept = _kept(user.telegram_id)
        if kept is None:
            return False
        mode, message_id = kept
        lang = lang_of(user, admin=False)
        data = state(user, lang)
        last = redis_client.get(_LAST.format(user.id))
        last = last.decode() if isinstance(last, bytes) else last
        if last and json.loads(last) | {"h": ""} == json.loads(data) | {"h": ""}:
            return False
        if not force and not redis_client.set(_THROTTLE.format(user.id), 1, nx=True, ex=REFRESH_EVERY):
            return False
        if mode == "w":
            _api("editMessageWidgetData", chat_id=user.telegram_id, message_id=message_id, chat_data=data)
        else:
            bot.edit_message_text(text_card(user, lang), user.telegram_id, message_id)
        redis_client.set(_LAST.format(user.id), data, ex=30 * 24 * 3600)
        return True
    except Exception as e:
        text = str(e).lower()
        if "not found" in text or "message_id_invalid" in text or "can't be edited" in text:
            # The card was deleted: stop updating it
            from hiddifypanel.database import db

            BotPref.put(user.telegram_id, PREF, "")
            db.session.commit()
        logger.debug(f"tgbot widget: card of user {getattr(user, 'id', '?')} not refreshed: {e}")
        return False


def refresh_all(users: list[User]) -> None:
    """After a usage update."""
    if not users or not hconfig(ConfigEnum.telegram_bot_token):
        return
    for user in users:
        refresh(user)


@route(Cb.widget, admin=False)
def send_card(ctx: Ctx, _args: list[str]) -> None:
    user = ctx.user
    assert user
    try:
        send(user, ctx.lang)
        ctx.toast(ctx.tr(T.wg_sent))
    except Exception as e:
        logger.info(f"tgbot widget: not sent to user {user.id}: {e}")
        ctx.toast(ctx.tr(T.wg_unsupported), alert=True)
