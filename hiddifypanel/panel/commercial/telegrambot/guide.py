"""The setup guide: one question (which device?), then only that device's steps with the Hiddify app: install it
from its store, copy the link with one tap, add it in the app, connect."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .texts import T
from .ui import BRAND, Cb, Ctx, Screen, Style, app_row, btn, copy_btn, h, keyboard, route, url_btn
from . import accounts

_RELEASES = "https://github.com/hiddify/hiddify-next/releases/latest/download"


class Device(StrEnum):
    ios = "i"
    android = "a"
    windows = "w"
    mac = "m"
    linux = "l"


@dataclass(frozen=True, slots=True)
class Install:
    label: T
    url: str


@dataclass(frozen=True, slots=True)
class DeviceGuide:
    name: T
    installs: tuple[Install, ...]
    #: The step that adds the copied link in the app (phones: the + at the top; desktops: New Profile)
    add_step: T


#: The same official downloads the user page offers (restapi/v2/user/apps_api.py).
GUIDES: dict[Device, DeviceGuide] = {
    Device.ios: DeviceGuide(T.dev_ios, (Install(T.get_app_store, "https://apps.apple.com/us/app/hiddify-proxy-vpn/id6596777532"),), T.guide_add_phone),
    Device.android: DeviceGuide(
        T.dev_android,
        (
            Install(T.get_google_play, "https://play.google.com/store/apps/details?id=app.hiddify.com"),
            Install(T.get_apk, f"{_RELEASES}/Hiddify-Android-universal.apk"),
        ),
        T.guide_add_phone,
    ),
    Device.windows: DeviceGuide(
        T.dev_windows,
        (Install(T.get_setup, f"{_RELEASES}/Hiddify-Windows-Setup-x64.exe"), Install(T.get_portable, f"{_RELEASES}/Hiddify-Windows-Portable-x64.zip")),
        T.guide_add_desktop,
    ),
    Device.mac: DeviceGuide(T.dev_mac, (Install(T.get_dmg, f"{_RELEASES}/Hiddify-MacOS.dmg"),), T.guide_add_desktop),
    Device.linux: DeviceGuide(T.dev_linux, (Install(T.get_appimage, f"{_RELEASES}/Hiddify-Linux-x64.AppImage"),), T.guide_add_desktop),
}


def devices_screen(ctx: Ctx) -> Screen:
    pick = [btn(ctx.tr(GUIDES[d].name), Cb.guide, d.value) for d in Device]
    return Screen(
        f"📱 <b>{ctx.tr(T.guide_title)}</b>\n\n{ctx.tr(T.guide_which)}",
        keyboard(pick[:2], pick[2:4], pick[4:], [btn(ctx.tr(T.back), Cb.back)]),
    )


def device_screen(ctx: Ctx, device: Device) -> Screen:
    user = ctx.user
    assert user
    guide = GUIDES[device]
    links = accounts.links(user)
    copy = copy_btn(ctx.tr(T.copy_link), links.sub, Style.primary)
    steps = [
        ctx.tr(T.guide_install),
        ctx.tr(T.guide_copy) if copy else ctx.tr(T.guide_copy_long),
        ctx.tr(guide.add_step),
        ctx.tr(T.guide_connect),
    ]
    text = "\n".join([f"📱 <b>{ctx.tr(guide.name)}</b>", "", *(f"{i}. {step}" for i, step in enumerate(steps, 1))])
    if not copy:  # too long for a copy button: the link to tap and hold
        text += f"\n\n<code>{h(links.sub)}</code>"
    installs = [url_btn(ctx.tr(i.label), i.url, Style.success if n == 0 else None) for n, i in enumerate(guide.installs)]
    rows = [installs]
    if copy:
        rows.append([copy])
    rows += [app_row(BRAND, links.home), [btn(ctx.tr(T.guide_other), Cb.guide), btn(ctx.tr(T.back), Cb.back)]]
    return Screen(text, keyboard(*rows))


@route(Cb.guide, admin=False)
def show_guide(ctx: Ctx, args: list[str]) -> None:
    try:
        device = Device(args[0]) if args else None
    except ValueError:
        device = None
    ctx.show(device_screen(ctx, device) if device else devices_screen(ctx))
    ctx.toast()
