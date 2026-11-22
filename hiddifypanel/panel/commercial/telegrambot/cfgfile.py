"""Advanced mode: a user downloads their configs as a file, right in the chat (sing-box, Clash or the plain links),
for apps that import a file rather than a link. The file is the user's own subscription, fetched from the panel the
way an app would."""

from __future__ import annotations

import io
import re

import requests
from loguru import logger
from telebot import types

from . import accounts, advanced, bot
from .texts import T
from .ui import RULE, Cb, Ctx, Screen, btn, h, keyboard, route

#: format → (the subscription's path under the user page, file extension)
FORMATS = {"singbox": ("singbox/", "json"), "clash": ("clash/", "yaml"), "links": ("sub/", "txt")}
#: The panel answers known apps only, each in its own form: the file is fetched as that app
_AGENT = {"singbox": "SFA/1.11.0 (Android)", "clash": "ClashMeta/1.18", "links": "v2rayNG/1.9"}
_LABEL = {"singbox": "sing-box (JSON)", "clash": "Clash (YAML)", "links": "V2Ray / Xray (TXT)"}
MAX_BYTES = 8 * 1024 * 1024


def _is_ip(host: str) -> bool:
    return bool(re.fullmatch(r"[\d.]+|\[?[0-9a-fA-F:]+\]?", host or ""))


def fetch(home: str, path: str, agent: str) -> bytes:
    host = home.split("/")[2] if home.count("/") >= 2 else ""
    res = requests.get(home + path, timeout=20, verify=not _is_ip(host), headers={"User-Agent": agent})
    res.raise_for_status()
    if len(res.content) > MAX_BYTES:
        raise ValueError("too big")
    return res.content


def choose_screen(ctx: Ctx) -> Screen:
    rows = [[btn(_LABEL[f], Cb.cfgfile, f)] for f in FORMATS]
    rows.append([btn(ctx.tr(T.back), Cb.me)])
    return Screen(f"📄 <b>{ctx.tr(T.cf_title)}</b>\n{RULE}\n{ctx.tr(T.cf_pick)}", keyboard(*rows))


@route(Cb.cfgfile, admin=False)
def send_file(ctx: Ctx, args: list[str]) -> None:
    """cf → the formats · cf:<format> → the file."""
    user = ctx.user
    if not advanced.is_on() or user is None:
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    if not args or args[0] not in FORMATS:
        ctx.toast()
        return ctx.show(choose_screen(ctx))
    path, ext = FORMATS[args[0]]
    ctx.toast(ctx.tr(T.cf_working))
    try:
        content = fetch(accounts.links(user).home, path, _AGENT[args[0]])
    except Exception as e:
        logger.warning(f"tgbot: config file {args[0]} not made: {e}")
        return ctx.toast(ctx.tr(T.error_generic), alert=True)
    name = re.sub(r"[^\w.-]+", "_", user.name or "hiddify")[:40] or "hiddify"
    caption = f"📄 <b>{h(_LABEL[args[0]])}</b>\n<i>{ctx.tr(T.cf_hint)}</i>"
    bot.send_document(ctx.chat_id, types.InputFile(io.BytesIO(content), file_name=f"{name}-{args[0]}.{ext}"), caption=caption, parse_mode="HTML")


def home_rows(ctx: Ctx) -> list[list]:
    """The user's card keys to the Mini App features (Advanced): the config file and the emoji status."""
    from .miniapp import status_button

    if not advanced.is_on() or ctx.user is None:
        return []
    from .guard import join_row

    return [[btn(ctx.tr(T.cf_title), Cb.cfgfile), status_button(ctx)], join_row(ctx.lang, ctx.user)]
