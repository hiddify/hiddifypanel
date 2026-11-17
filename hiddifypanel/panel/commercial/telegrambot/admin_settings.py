"""The admin's settings (a key of their keyboard): the bot's language, the panel backup (the owner only) and the
sound of the bot's messages."""

from __future__ import annotations

from hiddifypanel.database import db
from hiddifypanel.models import AdminMode

from . import silence
from .settings import LANGUAGES
from .texts import T
from .ui import Cb, Ctx, Screen, Style, btn, h, keyboard, route


def settings_screen(ctx: Ctx) -> Screen:
    admin = ctx.admin
    assert admin
    quiet = silence.is_silent(ctx.chat_id)
    lines = [
        f"⚙️ <b>{ctx.tr(T.settings_title)}</b>",
        "",
        f"🌐 {ctx.tr(T.language_title)}: <b>{LANGUAGES.get(ctx.lang, ctx.lang)}</b>",
        f"{'🔕' if quiet else '🔔'} {ctx.tr(T.as_sound)}: <b>{ctx.tr(T.as_sound_off if quiet else T.as_sound_on)}</b>",
        f"<i>{ctx.tr(T.as_sound_hint)}</i>",
    ]
    toggle = btn(ctx.tr(T.as_turn_sound_on if quiet else T.as_turn_sound_off), Cb.silent, 0 if quiet else 1, style=Style.success if quiet else None)
    rows = [[btn(ctx.tr(T.language), Cb.lang)], [toggle]]
    if admin.mode == AdminMode.super_admin:
        rows.append([btn(ctx.tr(T.btn_backup), Cb.backup)])
        from .accounts import panel_app_url

        if url := panel_app_url():  # the bot's "Open" button (BotFather only: Telegram has no API for it)
            lines += ["", f"🚀 <b>{ctx.tr(T.as_main_app)}</b>", f"<i>{ctx.tr(T.as_main_app_how)}</i>", f"<code>{h(url)}</code>"]
    rows.append([btn(ctx.tr(T.back), Cb.back)])
    return Screen("\n".join(lines), keyboard(*rows))


@route(Cb.admin_settings, admin=True)
def show_settings(ctx: Ctx, _args: list[str]) -> None:
    ctx.show(settings_screen(ctx))
    ctx.toast()


@route(Cb.silent, admin=True)
def set_sound(ctx: Ctx, args: list[str]) -> None:
    on = args[:1] == ["1"]
    silence.set_silent(ctx.chat_id, on)
    db.session.commit()
    ctx.toast(ctx.tr(T.as_now_silent if on else T.as_now_sound))
    ctx.show(settings_screen(ctx))
