"""The admin's settings (a key of their keyboard): the bot's language, the panel backup (the owner only) and the
sound of the bot's messages."""

from __future__ import annotations

from hiddifypanel.database import db
from hiddifypanel.models import AdminMode

from . import advanced, silence
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
    from .servers import settings_lines, settings_rows

    if more := settings_lines(ctx):  # the morning report (Advanced)
        lines += ["", *more]
        rows += settings_rows(ctx)
    if admin.mode == AdminMode.super_admin:
        rows.append([btn(ctx.tr(T.btn_backup), Cb.backup)])
        lines += ["", *_advanced_lines(ctx)]
        rows += _advanced_rows(ctx)
        from .accounts import panel_app_url

        if url := panel_app_url():  # the bot's "Open" button (BotFather only: Telegram has no API for it)
            lines += ["", f"🚀 <b>{ctx.tr(T.as_main_app)}</b>", f"<i>{ctx.tr(T.as_main_app_how)}</i>", f"<code>{h(url)}</code>"]
    rows.append([btn(ctx.tr(T.back), Cb.back)])
    return Screen("\n".join(lines), keyboard(*rows))


def _state(ctx: Ctx, on: bool) -> str:
    return ctx.tr(T.on if on else T.off)


def _advanced_lines(ctx: Ctx) -> list[str]:
    """Advanced mode and, when it is on, the features with their own switch."""
    on = advanced.is_on()
    lines = [f"🧪 <b>{ctx.tr(T.adv_title)}</b>: <b>{_state(ctx, on)}</b>", f"<i>{ctx.tr(T.adv_hint)}</i>"]
    if on:
        lines += [
            "",
            f"🤖 {ctx.tr(T.adv_resellers)}: <b>{_state(ctx, advanced.feature(advanced.RESELLER_BOTS))}</b>",
            f"<i>{ctx.tr(T.adv_resellers_hint)}</i>",
            f"🚪 {ctx.tr(T.adv_guard)}: <b>{_state(ctx, advanced.feature(advanced.SUBSCRIBERS_GROUP))}</b>",
            f"<i>{ctx.tr(T.adv_guard_hint)}</i>",
        ]
    return lines


def _switch(ctx: Ctx, key: str, label: T) -> list:
    on = advanced.is_on() if key == advanced.ADVANCED else advanced.feature(key)
    text = f"{ctx.tr(label)}: {ctx.tr(T.turn_off if on else T.turn_on)}"
    return [btn(text, Cb.advanced, key, 0 if on else 1, style=None if on else Style.success)]


def _advanced_rows(ctx: Ctx) -> list[list]:
    rows = [_switch(ctx, advanced.ADVANCED, T.adv_title)]
    if advanced.is_on():
        rows += [_switch(ctx, advanced.RESELLER_BOTS, T.adv_resellers), _switch(ctx, advanced.SUBSCRIBERS_GROUP, T.adv_guard)]
    return rows


@route(Cb.advanced, admin=True)
def set_advanced(ctx: Ctx, args: list[str]) -> None:
    """The owner turns Advanced, or a feature inside it, on or off."""
    admin = ctx.admin
    assert admin
    key, value = (args + ["", ""])[:2]
    if admin.mode != AdminMode.super_admin or key not in advanced.SWITCHES or value not in ("0", "1"):
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    advanced.set_switch(key, value == "1")
    db.session.commit()
    ctx.toast(ctx.tr(T.adv_saved))
    ctx.show(settings_screen(ctx))


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
