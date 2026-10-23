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
    close = "x"  # delete this message (QR photos, files)


def cb(kind: Cb, *args: object) -> str:
    data = ":".join([kind.value, *(str(a) for a in args)])
    assert len(data.encode()) <= 64, data
    return data


def btn(text: str, kind: Cb, *args: object) -> types.InlineKeyboardButton:
    return types.InlineKeyboardButton(text=text, callback_data=cb(kind, *args))


def url_btn(text: str, url: str) -> types.InlineKeyboardButton:
    return types.InlineKeyboardButton(text=text, url=url)


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


def app_btn(text: str, url: str) -> types.InlineKeyboardButton:
    """Opens ``url`` inside Telegram as a Mini App (callers check ``can_open_as_app``: Telegram refuses the whole
    message otherwise)."""
    return types.InlineKeyboardButton(text=text, web_app=types.WebAppInfo(url=url))


def app_row(text: str, url: str | None) -> list[types.InlineKeyboardButton]:
    """A Mini App button for ``url``, or nothing when it cannot be one (pages open only as Mini Apps)."""
    return [app_btn(text, url)] if can_open_as_app(url) else []


def keyboard(*rows: Sequence[types.InlineKeyboardButton]) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(keyboard=[list(r) for r in rows if r])


# --------------------------------------------------------------------------- chat state


class ChatState:
    """Small per-chat memory shared by all workers (what the next text message means, the list being browsed)."""

    TTL = 3600

    def __init__(self, chat_id: int):
        self._key = f"tgbot:state:{chat_id}"

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


def send_card(chat_id: int, screen: Screen) -> types.Message:
    """A new message for ``screen``: a QR photo with a caption when it has one (and QR codes can be drawn)."""
    from .qr import render

    png = render(screen.qr) if screen.qr else None
    if png is not None:
        return bot.send_photo(chat_id, ("qr.png", png), caption=screen.text, reply_markup=screen.markup)
    return bot.send_message(chat_id, screen.text, reply_markup=screen.markup, link_preview_options=NO_PREVIEW)


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
        if self.message_id and not (self.on_photo and not screen.qr):
            try:
                if self.on_photo:
                    bot.edit_message_caption(screen.text, self.chat_id, self.message_id, reply_markup=screen.markup)
                else:
                    bot.edit_message_text(screen.text, self.chat_id, self.message_id, reply_markup=screen.markup, link_preview_options=NO_PREVIEW)
                    self.state.update(panel=self.message_id)
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

    def toast(self, text: str = "", alert: bool = False) -> None:
        if self.call_id and not self._answered:
            self._answered = True
            try:
                bot.answer_callback_query(self.call_id, text=text[:200] or None, show_alert=alert, cache_time=0)
            except ApiTelegramException:
                pass


def background(fn: Callable[[], None]) -> None:
    """Run ``fn`` after the webhook has answered (long sends would make Telegram resend the update)."""
    import threading

    from flask import current_app

    app = current_app._get_current_object()  # ty: ignore[unresolved-attribute]

    def run() -> None:
        with app.app_context():
            try:
                fn()
            except Exception:
                logger.exception("tgbot: background job failed")

    threading.Thread(target=run, daemon=True, name="tgbot-send").start()


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


def lang_of(account: AdminUser | User | None, *, admin: bool) -> str:
    fallback = hconfig(ConfigEnum.admin_lang if admin else ConfigEnum.lang) or "en"
    lang = getattr(account, "lang", None) if account else None
    return str(getattr(lang, "value", lang) or fallback)


# --------------------------------------------------------------------------- routing

Handler = Callable[[Ctx, list[str]], None]


@dataclass(frozen=True, slots=True)
class Route:
    handler: Handler
    admin: bool  # needs a linked admin; otherwise a linked user


ROUTES: dict[Cb, Route] = {}


def route(kind: Cb, *, admin: bool) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        ROUTES[kind] = Route(fn, admin)
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
