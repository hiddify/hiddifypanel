"""The backup message, the same wherever it comes from (the daily backup, the panel's "send to Telegram", the bot's
Backup key): the file named by its date and time (2026.11.17_18.00.json), a tidy card (the panel, its version, the
date, the time, the size, the users) and the panel's links as buttons: green the secure ones, 🟠 those through a CDN,
red the not secure one (only if the others do not open)."""

from __future__ import annotations

import datetime
import html
import ipaddress
import re
from typing import IO

from loguru import logger
from telebot import types
from telebot.apihelper import ApiTelegramException

from .texts import T, t
from .ui import RULE, Style, fmt_bytes, keyboard, lang_of, url_btn

#: How the panel names its backup files on disk
DISK_NAME = "%Y_%m_%d__%H_%M_%S.json"


def when_of(disk_name: str) -> datetime.datetime:
    try:
        return datetime.datetime.strptime(disk_name.rsplit("/", 1)[-1], DISK_NAME)
    except ValueError:
        return datetime.datetime.now()


def file_name(when: datetime.datetime) -> str:
    """The name the admin sees: the day and the time, 2026.11.17_18.00.json."""
    return f"{when:%Y.%m.%d_%H.%M}.json"


def _panel_name() -> str:
    from hiddifypanel.models import ConfigEnum, hconfig

    return re.sub(r"<[^>]+>", "", hconfig(ConfigEnum.branding_title) or "").strip() or "Hiddify Manager"


def links(owner) -> list[tuple[str, str, str]]:
    """(kind, address, url) of every way into the panel: "secure" (the server's own address or domain), "cdn", and
    last "insecure" (plain http to the IPv4). IPv6 is left out: it does not open from most networks."""
    from hiddifypanel import hutils
    from hiddifypanel.models import Domain, DomainType
    from hiddifypanel.panel import hiddify

    out = []
    for d in Domain.get_domains():
        try:
            if ipaddress.ip_address(d.domain.strip("[]")).version == 6:
                continue
        except ValueError:
            pass
        kind = "cdn" if d.mode == DomainType.cdn else "secure"
        out.append((kind, d.domain, hiddify.get_account_panel_link(owner, d.domain)))
    out.sort(key=lambda x: x[0] == "cdn")  # the server's own first, then the CDNs
    ip = hutils.network.get_ip_str(4)
    if ip:
        out.append(("insecure", ip, hiddify.get_account_panel_link(owner, ip, is_https=False)))
    return out


def caption(lang: str, when: datetime.datetime, size: int | None) -> str:
    import hiddifypanel
    from hiddifypanel.models import User

    tr = lambda key, **kw: t(key, lang, **kw)  # noqa: E731
    facts = [
        f"🏷 {tr(T.bk_panel)}: <b>{html.escape(_panel_name())}</b>",
        f"🧩 {tr(T.bk_version)}: <code>v{html.escape(hiddifypanel.__version__)}</code>",
        f"📅 {tr(T.bk_date)}: <b>{when:%Y-%m-%d}</b>  ·  🕒 <b>{when:%H:%M}</b>",
    ]
    more = []
    if size:
        more.append(f"📦 {tr(T.bk_size)}: <b>{fmt_bytes(size, lang) if size >= 1024**3 else _kb(size)}</b>")
    try:
        more.append(f"👥 {tr(T.users_block)}: <b>{User.query.count()}</b>")
    except Exception as e:
        logger.debug(f"backup: users not counted: {e}")
    if more:
        facts.append("  ·  ".join(more))
    return "\n".join([f"💾 <b>{tr(T.bk_title)}</b>", RULE, "<blockquote>" + "\n".join(facts) + "</blockquote>", f"🔗 <i>{tr(T.bk_links)}</i>"])


def _kb(size: int) -> str:
    return f"{size / 1024**2:.1f} MB" if size >= 1024**2 else f"{size / 1024:.0f} KB"


def markup(lang: str, owner, *, plain_http: bool = True, tail: list | None = None) -> types.InlineKeyboardMarkup:
    rows = []
    for kind, address, url in links(owner)[:12]:
        if kind == "insecure":
            if plain_http:
                rows.append([url_btn(f"⚠️ {t(T.bk_insecure, lang)} · {address}", url, style=Style.danger)])
        elif kind == "cdn":
            rows.append([url_btn(f"🟠 CDN · {address}", url)])
        else:
            rows.append([url_btn(f"🔒 {address}", url, style=Style.success)])
    if tail:
        rows.append(tail)
    return keyboard(*rows)


def send(chat_id: int, document: IO[bytes], disk_name: str, account, *, size: int | None = None, tail: list | None = None):
    """The backup file and its card to ``chat_id``. If Telegram refuses a link button (a plain http address), it goes
    again without that one, and at worst without buttons. Raises what the last try raised."""
    from hiddifypanel.models import AdminUser

    from . import bot

    lang = lang_of(account, admin=True) if account is not None else "en"
    owner = AdminUser.get_super_admin()
    when = when_of(disk_name)
    text = caption(lang, when, size)
    tries = [lambda: markup(lang, owner, tail=tail), lambda: markup(lang, owner, plain_http=False, tail=tail), lambda: keyboard(tail) if tail else None]
    from . import rich

    error: Exception | None = None
    for build in tries:
        try:
            # One rich message: the file on top, the card, the links as soft buttons inside; else the classic document
            keys = build()
            try:
                sent = rich.send_document(chat_id, text, keys.to_dict() if keys else None, document, file_name(when))
                if sent is not None:
                    return types.Message.de_json(sent)
            except ApiTelegramException as e:
                if "button" in str(e).lower() or "url" in str(e).lower():
                    raise  # the next try has fewer buttons
                logger.info(f"backup: not as a rich message ({e}); the classic document")
            document.seek(0)
            return bot.send_document(chat_id, types.InputFile(document, file_name=file_name(when)), caption=text, parse_mode="HTML", reply_markup=keys)
        except ApiTelegramException as e:
            if "button" not in str(e).lower() and "url" not in str(e).lower():
                raise  # not about a link button: trying again would not help
            error = e
            logger.warning(f"backup: Telegram refused the message ({e}); trying with fewer buttons")
    assert error is not None
    raise error
