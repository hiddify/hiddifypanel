"""The bot's building blocks: one live "panel" message per chat that every button edits in place, typed
callback routing, per-chat state in redis, and the small formatters every screen uses."""

from __future__ import annotations

import datetime
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from html import escape
from typing import Any, TypeGuard

from loguru import logger
from telebot import types
from telebot.apihelper import ApiTelegramException

from hiddifypanel.cache import redis_client
from hiddifypanel.models import AdminUser, ConfigEnum, User, hconfig

from . import bot
from .texts import T, t

# --------------------------------------------------------------------------- callback data


class Cb(StrEnum):
    """First field of every button's callback data (Telegram allows 64 bytes, so they stay short)."""

    home = "h"
    users = "ul"  # ul:<filter>:<page>
    search = "us"  # us:<page>  (query is in the chat state)
    search_ask = "uq"
    card = "uc"  # uc:<user id>
    act = "ua"  # ua:<user id>:<action>[:<arg>]
    links = "ulk"  # ulk:<user id>
    qr = "qr"  # qr:<user id>  (sends the user's card)
    share = "sc"  # sc:<user id>  (refreshes a sent card)
    new = "nw"  # nw:<gb>:<days>:<count>  (0 = not chosen yet)
    new_name = "nn"  # nn:<gb>:<days>:<count>
    new_go = "ng"  # ng:<gb>:<days>:<count>
    status = "st"
    check = "cs"  # the server's address and its services
    backup = "bk"
    me = "me"  # the user's own account
    me_links = "ml"
    free = "fo"  # fo:<conversation id>  (the free test offer, for whoever opened an admin's link)
    free_ask = "fa"  # fa:<conversation id>  (ask for it)
    free_write = "fw"  # how to write to the admin
    free_link = "fl"  # the admin's own free test link and package
    free_answer = "fr"  # fr:<conversation id>:<a|d>  (the admin approves / declines)
    reply = "rp"  # rp:<conversation id>  (the admin's next text goes to that chat)
    widget = "wg"  # the live usage card (a Telegram widget)
    settings = "se"  # the person's settings: language, alerts
    pref = "pf"  # pf:<key>:<value>  set one of them
    chart = "ch"  # ch[:<user id>][:r]  the usage chart (a user id: an admin's; r: refresh in place)
    guide = "gd"  # gd[:<device>]  the setup guide
    doctor = "dr"  # the connection check ("I can't connect")
    support = "sp"  # the support screen (private messages with the person's support team)
    support_write = "sq"  # open the reply field to write to support
    history = "hs"  # hs[:<page>]  the person's chat history with support (0: newest)
    back = "bb"  # one step back on a person's screens (the start screen at the first step)
    support_end = "sx"  # end the support chat: its messages are cleared from the person's chat
    support_seen = "sv"  # sv:<conversation id>  the admin marks it seen
    lang = "lg"  # lg[:<code>]  (the languages; with a code: speak it from now on)
    close = "x"  # delete this message (QR photos, files)
    new_count = "nc"  # ask the admin how many users to make
    bandwidth = "bw"  # bw[:<period>[:r]]  the server's traffic as a chart (24h, 7d, 15d, 30d; r: in place)
    chats = "cl"  # cl[:<page>]  the admin's conversations with people
    chat = "cv"  # cv:<conversation id>[:<page>]  one conversation (0: its newest page)
    broadcast = "bc"  # bc  write a message to all users; bc:go  send it; bc:x  drop it
    admin_settings = "as"  # the admin's settings: language, backup, sound
    silent = "sl"  # sl:<1|0>  the bot's messages to this chat without (or with) a sound
    advanced = "av"  # av:<switch>:<1|0>  the owner turns Advanced (or a feature inside it) on or off
    nodes = "nd"  # the panel's servers (Advanced)
    domains = "dm"  # the panel's domains: DNS and certificates (Advanced)
    morning = "mr"  # mr:<1|0>  the admin's morning report on or off (Advanced)
    bulk = "bu"  # bu[:<filter>[:<action>:<value>[:1]]]  one action on many users (Advanced)
    admins = "ad"  # ad[:<page>]  the admin's sub-admins and agents (Advanced)
    admin_card = "ac"  # ac:<admin id>[:<action>:<value>]  one of them (Advanced)
    agent_new = "an"  # ask the name of a new agent (Advanced)
    apply = "ap"  # ap[:ask|go]  apply the configs (Advanced, super admins)
    cfgtest = "ct"  # ct[:go]  the config test: the last result, or a new one (Advanced, super admins)
    lock = "lk"  # lk[:<action>:<1|0>]  which actions need the admin's biometrics (Advanced)
    cfgfile = "cf"  # cf[:<format>]  the user's configs as a file (Advanced)
    reseller_bot = "rb"  # the agent's own bot (Advanced, its own switch)
    open_help = "oh"  # oh[:check]  how to set the bot's "Open" button in @BotFather (the owner)
    update = "up"  # up[:<server id>[:go]]  update the panel of this server or of a node (Advanced, super admins)
    support_later = "rl"  # rl:<conversation id>  the admin reads it later: the notice goes, the message stays unread


def cb(kind: Cb, *args: object) -> str:
    data = ":".join([kind.value, *(str(a) for a in args)])
    assert len(data.encode()) <= 64, data
    return data


class Style(StrEnum):
    """A button's colour (Bot API 9.4), as on Apple's platforms: the screen's main action blue, a positive one
    (renew, approve, create) green, a destructive one (delete, disable) red; the rest keeps the client's own look."""

    primary = "primary"
    success = "success"
    danger = "danger"


#: The colours actually sent. Telegram draws "primary" as blue text on a light blue fill in some themes, which is
#: hard to read, and a bot cannot choose the text colour: those buttons are plain (a selected item gets a ✓).
#: Blue too: buttons inside a rich message draw it well (white on blue); rich.classic() takes it off a classic
#: keyboard, where it is blue text on blue
DRAWN_STYLES = {Style.success, Style.danger, Style.primary}
SELECTED = "✓ "


def _decorated(text: str, style: Style | None) -> dict[str, Any]:
    """A button's label, colour and animated icon (its leading emoji, when icons are on and a set has it)."""
    from .icons import split

    icon, label = split(text)
    fields: dict[str, Any] = {"text": label}
    if icon:
        fields["icon_custom_emoji_id"] = icon
    if style in DRAWN_STYLES:
        fields["style"] = style.value
    return fields


def btn(text: str, kind: Cb, *args: object, style: Style | None = None) -> types.InlineKeyboardButton:
    return types.InlineKeyboardButton(callback_data=cb(kind, *args), **_decorated(text, style))


def off_btn(text: str, style: Style | None = None, *, otherwise: types.InlineKeyboardButton | None = None) -> types.InlineKeyboardButton | None:
    """A button that does nothing, greyed out by Telegram: the page shown, the choice already made, an offer used.
    Advanced mode only: without it, ``otherwise`` (the button as it was), or nothing."""
    from . import advanced

    if not advanced.is_on():
        return otherwise
    return types.InlineKeyboardButton(disabled=types.DisabledButton(), **_decorated(text, style))


#: Telegram takes smart dates up to about 3 years ahead (5 years: RICH_MESSAGE_DATE_INVALID); later ones stay text
SMART_DATE_AHEAD = datetime.timedelta(days=3 * 365)


def tg_time(moment: datetime.datetime | datetime.date | None, fmt: str, text: str) -> str:
    """A date or time each person sees in their own language and time zone (Telegram's date_time entity). ``fmt``:
    r relative ("2 hours ago"), or any of w (weekday), d / D (short / long date), t / T (short / long time). ``text``
    is what an older app shows. A day alone is set at noon, so no time zone moves it to the day before or after."""
    from . import advanced

    if moment is None or not advanced.is_on():  # Advanced mode only
        return h(text)
    if not isinstance(moment, datetime.datetime):
        moment = datetime.datetime.combine(moment, datetime.time(12))
    if moment > datetime.datetime.now() + SMART_DATE_AHEAD:  # Telegram refuses a date that far (a 10-year package)
        return h(text)
    return f'<tg-time unix="{int(moment.timestamp())}" format="{fmt}">{h(text)}</tg-time>'


def ago_html(when: datetime.datetime | None, lang: str) -> str:
    """``ago`` as a smart date ("2 hours ago" in the person's language), when there is a real moment."""
    text = ago(when, lang)
    return tg_time(when, "r", text) if when and when.year >= 1971 else h(text)


def url_btn(text: str, url: str, style: Style | None = None) -> types.InlineKeyboardButton:
    return types.InlineKeyboardButton(url=url, **_decorated(text, style))


#: Telegram copies at most this many characters with a copy button.
COPY_MAX = 256


def copy_btn(text: str, value: str, style: Style | None = None) -> types.InlineKeyboardButton | None:
    """A button that copies ``value`` to the clipboard (Bot API 7.11); None when it is too long to copy."""
    if not value or len(value) > COPY_MAX:
        return None
    return types.InlineKeyboardButton(copy_text=types.CopyTextButton(value), **_decorated(text, style))


def is_domain_name(host: str) -> bool:
    """A real name (not an IP, not a bare word): what Telegram Mini Apps and certificates need."""
    import ipaddress

    host = host.strip("[]")
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        return "." in host and "*" not in host


def can_open_as_app(url: str | None) -> TypeGuard[str]:
    from urllib.parse import urlsplit

    return url is not None and url.startswith("https://") and is_domain_name(urlsplit(url).hostname or "")


def app_btn(text: str, url: str, style: Style | None = None) -> types.InlineKeyboardButton:
    """Opens ``url`` inside Telegram as a Mini App (callers check ``can_open_as_app``: Telegram refuses the whole
    message otherwise)."""
    return types.InlineKeyboardButton(web_app=types.WebAppInfo(url=url), **_decorated(text, style))


def app_row(text: str, url: str | None, style: Style | None = None) -> list[types.InlineKeyboardButton]:
    """A Mini App button for ``url``, or nothing when it cannot be one (pages open only as Mini Apps)."""
    return [app_btn(text, url, style)] if can_open_as_app(url) else []


def keyboard(*rows: Sequence[types.InlineKeyboardButton | None]) -> types.InlineKeyboardMarkup:
    """Rows of buttons; a button left out (None) and a row left empty are dropped."""
    kept = [[b for b in r if b is not None] for r in rows if r]
    return types.InlineKeyboardMarkup(keyboard=[r for r in kept if r])


# --------------------------------------------------------------------------- chat state


class ChatState:
    """Small per-chat memory shared by all workers (what the next text message means, the list being browsed)."""

    TTL = 3600

    def __init__(self, chat_id: int):
        from .resellers import state_prefix

        self._key = f"tgbot:state:{state_prefix()}{chat_id}"

    def load(self) -> dict[str, Any]:
        raw = redis_client.get(self._key)
        try:
            return json.loads(raw) if raw else {}
        except ValueError:
            return {}

    def update(self, **values: Any) -> None:
        state = self.load() | values
        redis_client.set(self._key, json.dumps({k: v for k, v in state.items() if v is not None}), ex=self.TTL)

    def get(self, key: str, default: Any = None) -> Any:
        return self.load().get(key, default)


# --------------------------------------------------------------------------- screens

NO_PREVIEW = types.LinkPreviewOptions(is_disabled=True)


@dataclass(slots=True)
class Screen:
    text: str
    markup: types.InlineKeyboardMarkup | None = None
    #: Shown as a photo card: this QR code with ``text`` as its caption (at most 1024 characters).
    qr: str | None = None


#: The label of the button that opens the person's page (the menu button by the message box and the cards):
#: the brand, the same in every language.
BRAND = "Hiddify"

#: Telegram's confetti message effect (private chats only).
EFFECT_CONFETTI = "5046509860389126442"


def celebrate(send: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """``send(...)`` with confetti; again without it when Telegram refuses the effect (a group, an old client...)."""
    try:
        return send(*args, message_effect_id=EFFECT_CONFETTI, **kwargs)
    except ApiTelegramException as e:
        if "effect" not in str(e).lower():
            raise
        logger.info(f"tgbot: message effect refused: {e}")
        return send(*args, **kwargs)


def show_picture(ctx: "Ctx", png: bytes, text: str, markup: types.InlineKeyboardMarkup | None, *, in_place: bool, name: str = "chart.png") -> tuple[int, bool] | None:
    """A picture (a chart) with its text and buttons: one rich message (soft buttons inside). ``in_place``: it takes
    the place of the message pressed (a screen, or the picture itself to refresh); else a new message. Returns the
    new message's id and whether it is a classic photo, or None when the message pressed was changed."""
    from . import rich

    as_dict = markup.to_dict() if markup else None
    if in_place and ctx.message_id:
        try:
            if not ctx.on_photo and rich.edit_card(ctx.chat_id, ctx.message_id, text, as_dict, png):
                if ctx.person or ctx.admin is not None:
                    ctx.state.update(upanel=ctx.message_id, upanel_photo=False)
                return None
            if ctx.on_photo:  # an older classic picture: its photo changes
                bot.edit_message_media(types.InputMediaPhoto(png, caption=text, parse_mode="HTML"), ctx.chat_id, ctx.message_id, reply_markup=markup)
                return None
        except ApiTelegramException as e:
            if "not modified" in str(e):
                return None
            logger.debug(f"tgbot: picture not changed in place: {e}")
    raw = rich.send_card(ctx.chat_id, text, as_dict, png)
    if raw is not None:
        return int(raw["message_id"]), False
    sent = bot.send_photo(ctx.chat_id, (name, png), caption=text, reply_markup=markup)
    return sent.message_id, True


def chat_action(chat_id: int, action: str = "typing") -> None:
    """"typing…" / "sending a photo…" in the chat's title while something takes a moment. Never raises."""
    try:
        bot.send_chat_action(chat_id, action)
    except Exception as e:
        logger.debug(f"tgbot: chat action not shown: {e}")


def send_card(chat_id: int, screen: Screen, *, festive: bool = False) -> types.Message:
    """A new message for ``screen``: a QR photo with a caption when it has one (and QR codes can be drawn).
    ``festive``: with confetti (a new account, an account on again)."""
    from .qr import render

    send = (lambda fn, *a, **k: celebrate(fn, *a, **k)) if festive else (lambda fn, *a, **k: fn(*a, **k))
    png = render(screen.qr) if screen.qr else None
    if png is not None:
        from . import rich

        # One rich message: the QR on top, the text, the soft buttons inside; the classic photo if it cannot be
        raw = rich.send_card(chat_id, screen.text, screen.markup.to_dict() if screen.markup else None, png, effect=EFFECT_CONFETTI if festive else None)
        if raw is not None:
            return types.Message.de_json(raw)
        return send(bot.send_photo, chat_id, ("qr.png", png), caption=screen.text, reply_markup=screen.markup)
    return send(bot.send_message, chat_id, screen.text, reply_markup=screen.markup, link_preview_options=NO_PREVIEW)


@dataclass(slots=True)
class Ctx:
    """Who is talking and where their panel message is. ``show`` edits that message, or sends a new one."""

    chat_id: int
    lang: str
    admin: AdminUser | None = None
    user: User | None = None
    message_id: int | None = None
    call_id: str | None = None
    #: The message being edited is a photo card: only its caption can change.
    on_photo: bool = False
    _answered: bool = field(default=False, repr=False)

    @property
    def state(self) -> ChatState:
        return ChatState(self.chat_id)

    def tr(self, key: T, /, **values: object) -> str:
        return t(key, self.lang, **values)

    def show(self, screen: Screen) -> None:
        """Edit the message in place: a photo's caption, or a text. Only a text screen pressed from a photo card (like
        "manage") becomes a new message, since a photo cannot turn into text."""
        person = self.person
        if self.message_id and screen.qr and not self.on_photo:
            # A card over a text (or rich) screen: one rich message, its QR inside, in place
            from .qr import render
            from . import rich

            png = render(screen.qr)
            try:
                if png is not None and rich.edit_card(self.chat_id, self.message_id, screen.text, screen.markup.to_dict() if screen.markup else None, png):
                    self.state.update(panel=self.message_id)
                    if person or self.admin is not None:
                        self.state.update(upanel=self.message_id, upanel_photo=False)
                    return
            except ApiTelegramException as e:
                if "message is not modified" in str(e):
                    return
        # A classic card is a photo: from a text screen it comes as a new message (the old screen goes, below)
        if self.message_id and not (self.on_photo and not screen.qr) and not (person and screen.qr and not self.on_photo):
            try:
                if self.on_photo:
                    bot.edit_message_caption(screen.text, self.chat_id, self.message_id, reply_markup=screen.markup)
                else:
                    bot.edit_message_text(screen.text, self.chat_id, self.message_id, reply_markup=screen.markup, link_preview_options=NO_PREVIEW)
                    self.state.update(panel=self.message_id)
                if person or self.admin is not None:
                    self.state.update(upanel=self.message_id, upanel_photo=self.on_photo)
                return
            except ApiTelegramException as e:
                if "message is not modified" in str(e):
                    return
                # Too old to edit, or deleted: send a fresh one instead.
                logger.debug(f"tgbot: cannot edit {self.message_id}: {e}")
        sent = send_card(self.chat_id, screen)
        self.message_id = sent.message_id
        self.on_photo = bool(sent.photo)
        if not self.on_photo:
            self.state.update(panel=sent.message_id)
        if person or self.admin is not None:  # one screen at a time: the one before it goes
            self.replace_panel(sent.message_id, self.on_photo)

    @property
    def person(self) -> bool:
        """Someone with an account (not an admin): their chat keeps one screen at a time."""
        return self.user is not None and self.admin is None

    def replace_panel(self, message_id: int, photo: bool) -> None:
        """``message_id`` is now the person's screen: the one before it goes, so the chat does not fill up."""
        old = self.state.get("upanel")
        if old and int(old) != int(message_id):
            try:
                bot.delete_message(self.chat_id, int(old))
            except Exception:
                pass
        self.state.update(upanel=int(message_id), upanel_photo=bool(photo))

    def on_panel(self) -> None:
        """Act on the person's current screen (a key of the keyboard was pressed, not a button on a message)."""
        self.message_id = self.state.get("upanel")
        self.on_photo = bool(self.state.get("upanel_photo"))

    def toast(self, text: str | None = "", alert: bool = False) -> None:
        if self.call_id and not self._answered:
            self._answered = True
            try:
                bot.answer_callback_query(self.call_id, text=(text or "")[:200] or None, show_alert=alert, cache_time=0)
            except ApiTelegramException:
                pass


def background(fn: Callable[[], None]) -> None:
    """Run ``fn`` after the webhook has answered (long sends would make Telegram resend the update)."""
    import threading

    from flask import current_app

    app = current_app._get_current_object()  # ty: ignore[unresolved-attribute]

    import contextvars

    context = contextvars.copy_context()  # an agent's bot stays the sender in the thread (resellers.current)

    def run() -> None:
        with app.app_context():
            try:
                fn()
            except Exception:
                logger.exception("tgbot: background job failed")

    threading.Thread(target=lambda: context.run(run), daemon=True, name="tgbot-send").start()


def with_retry(call: Callable[[], Any], attempts: int = 5) -> Any:
    """One Telegram call, waiting out flood limits (429 retry_after)."""
    import time

    for attempt in range(attempts):
        try:
            return call()
        except ApiTelegramException as e:
            if e.error_code != 429 or attempt == attempts - 1:
                raise
            time.sleep(float((e.result_json or {}).get("parameters", {}).get("retry_after", 1)) + 0.5)


def lang_of(account: AdminUser | User | None, *, admin: bool, telegram: str | None = None) -> str:
    """The language to talk in: the one chosen for the account (in the panel or the bot), else the person's own
    Telegram language when the bot speaks it, else the panel's default."""
    from .texts import supported

    lang = getattr(account, "lang", None) if account else None
    chosen = str(getattr(lang, "value", lang) or "")
    return chosen or supported(telegram) or str(hconfig(ConfigEnum.admin_lang if admin else ConfigEnum.lang) or "en")


# --------------------------------------------------------------------------- routing

Handler = Callable[[Ctx, list[str]], None]


@dataclass(frozen=True, slots=True)
class Route:
    handler: Handler
    admin: bool  # needs a linked admin; otherwise a linked user
    anyone: bool = False  # also someone the bot does not know yet (the free test offer)


ROUTES: dict[Cb, Route] = {}


def route(kind: Cb, *, admin: bool, anyone: bool = False) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        ROUTES[kind] = Route(fn, admin, anyone)
        return fn

    return register


# --------------------------------------------------------------------------- formatting

GB = 1024**3


def h(value: object) -> str:
    return escape(str(value or ""))


def fmt_gb(value_gb: float, lang: str) -> str:
    if value_gb >= 1000:
        return f"{value_gb / 1024:.2f} TB"
    if value_gb >= 100:
        return f"{value_gb:.0f} {t(T.gb, lang)}"
    if value_gb >= 10 or value_gb == int(value_gb):
        return f"{value_gb:.1f}".removesuffix(".0") + f" {t(T.gb, lang)}"
    return f"{value_gb:.2f} {t(T.gb, lang)}"


def fmt_data(value_gb: float, lang: str) -> str:
    """Like ``fmt_gb``, with megabytes under one gigabyte (a 500 MB test package)."""
    if value_gb < 1:
        return f"{round(value_gb * 1024)} {t(T.mb, lang)}"
    return fmt_gb(value_gb, lang)


def fmt_bytes(value: int, lang: str) -> str:
    return fmt_gb((value or 0) / GB, lang)


def bar(ratio: float, width: int = 10) -> str:
    ratio = min(max(ratio, 0.0), 1.0)
    filled = round(ratio * width)
    return "▰" * filled + "▱" * (width - filled)


def level_dot(ratio: float) -> str:
    return "🟢" if ratio < 0.6 else "🟡" if ratio < 0.85 else "🔴"


def ago(when: datetime.datetime | None, lang: str) -> str:
    if not when or when.year < 1971:
        return t(T.never, lang)
    seconds = (datetime.datetime.now() - when).total_seconds()
    if seconds < 300:
        return t(T.online_now, lang)
    if seconds < 3600:
        return t(T.ago_minutes, lang, n=int(seconds // 60))
    if seconds < 86400:
        return t(T.ago_hours, lang, n=int(seconds // 3600))
    return t(T.ago_days, lang, n=int(seconds // 86400))


def duration(seconds: int, lang: str) -> str:
    days, rest = divmod(max(int(seconds), 0), 86400)
    hours, rest = divmod(rest, 3600)
    if days:
        return f"{days}{t(T.unit_d, lang)} {hours}{t(T.unit_h, lang)}"
    return f"{hours}{t(T.unit_h, lang)} {rest // 60}{t(T.unit_m, lang)}"


RULE = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄"


def redis_take(key: str, client=None):
    """The value at ``key``, read and deleted in one step (a MULTI/EXEC: two presses at once cannot both get it;
    GETDEL needs Redis 6.2, Ubuntu 22.04 has 6.0)."""
    if client is None:
        from hiddifypanel.cache import redis_client as client

    pipe = client.pipeline()
    pipe.get(key)
    pipe.delete(key)
    raw, _ = pipe.execute()
    return raw
