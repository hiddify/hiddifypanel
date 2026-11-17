"""A user's last 30 days of traffic as a picture (Apple Health style bars), with the words in the caption so every
language reads right. Sent as its own message under the account card, for the user and for their admin."""

from __future__ import annotations

import datetime
import io
from pathlib import Path

from loguru import logger
from PIL import Image, ImageDraw, ImageFont
from telebot import types

from hiddifypanel.models import User
from hiddifypanel.models.usage import UserDailyUsage

from . import bot
from .texts import T
from .ui import Cb, Ctx, Style, btn, chat_action, fmt_bytes, h, keyboard, route, show_picture

DAYS = 30
W, H = 1200, 675
PAD_L, PAD_R, PAD_T, PAD_B = 70, 150, 140, 90
BG = (247, 247, 250)
CARD = (255, 255, 255)
BLUE = (10, 132, 255)
BLUE_SOFT = (122, 184, 255)
GRID = (229, 229, 234)
TEXT = (28, 28, 30)
MUTED = (142, 142, 147)
AVG = (255, 159, 10)
_FONTS = Path(__file__).resolve().parents[3] / "static" / "fonts"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(_FONTS / ("Vazir-Bold.ttf" if bold else "Vazir-Medium.ttf")), size)
    except OSError:
        return ImageFont.load_default()


def _short(n: float) -> str:
    """Bytes as a short number for the axis: 1.2 GB, 350 MB."""
    gb = n / 1024**3
    if gb >= 1:
        return f"{gb:.1f} GB" if gb < 100 else f"{gb:.0f} GB"
    return f"{n / 1024**2:.0f} MB"


def render(days: list[tuple[datetime.date, int]]) -> bytes:
    """The bars of ``days`` (oldest first) as a PNG."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((24, 24, W - 24, H - 24), radius=36, fill=CARD)

    values = [v for _, v in days]
    total = sum(values)
    top = max(values) if values and max(values) > 0 else 1
    step = top / 2
    left, right, upper, lower = PAD_L, W - PAD_R, PAD_T, H - PAD_B
    height = lower - upper

    # Total, big
    d.text((PAD_L, 52), _short(total), font=_font(54, bold=True), fill=TEXT)

    for i in range(3):  # 0, half, top
        y = lower - height * i / 2
        d.line((left, y, right, y), fill=GRID, width=2)
        if i:
            d.text((right + 14, y - 16), _short(step * i), font=_font(24), fill=MUTED)

    n = max(len(days), 1)
    slot = (right - left) / n
    bar_w = max(slot * 0.62, 4)
    for i, (day, v) in enumerate(days):
        x0 = left + slot * i + (slot - bar_w) / 2
        x1 = x0 + bar_w
        today = i == n - 1
        if v <= 0:
            d.rounded_rectangle((x0, lower - 6, x1, lower), radius=3, fill=GRID)
        else:
            y0 = lower - max(height * v / top, 8)
            d.rounded_rectangle((x0, y0, x1, lower), radius=min(bar_w / 2, 10), fill=BLUE if today else BLUE_SOFT)
        if i % 7 == (n - 1) % 7:  # a day number every week, ending today
            label = str(day.day)
            w = d.textlength(label, font=_font(24))
            d.text(((x0 + x1) / 2 - w / 2, lower + 16), label, font=_font(24), fill=TEXT if today else MUTED)

    active = [v for v in values if v > 0]
    if active:
        avg = total / len(values)
        y = lower - height * avg / top
        x = left
        while x < right:  # dashed
            d.line((x, y, min(x + 14, right), y), fill=AVG, width=3)
            x += 24
        d.text((right + 14, y - 16), _short(avg), font=_font(24, bold=True), fill=AVG)

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def caption(lang_ctx: Ctx, user: User, days: list[tuple[datetime.date, int]]) -> str:
    tr = lang_ctx.tr
    values = [v for _, v in days]
    total = sum(values)
    lines = [f"📊 <b>{tr(T.chart_title)}</b>  ·  {h(user.name)}", ""]
    if total <= 0:
        lines.append(f"<i>{tr(T.chart_empty)}</i>")
        return "\n".join(lines)
    busiest_day, busiest = max(days, key=lambda x: x[1])
    lines += [
        f"{tr(T.chart_total)}: <b>{fmt_bytes(total, lang_ctx.lang)}</b>",
        f"{tr(T.chart_avg)}: <b>{fmt_bytes(total / len(values), lang_ctx.lang)}</b>",
        f"{tr(T.chart_peak)}: <b>{fmt_bytes(busiest, lang_ctx.lang)}</b> ({busiest_day.isoformat()})",
        f"{tr(T.chart_today)}: <b>{fmt_bytes(values[-1], lang_ctx.lang)}</b>",
    ]
    return "\n".join(lines)


def _target(ctx: Ctx, args: list[str]) -> User | None:
    """The user's own chart, or (for an admin) the chart of one of their users."""
    if ctx.user and not ctx.admin:
        return ctx.user
    if ctx.admin and args and args[0].isdigit():
        from . import accounts

        return accounts.get_visible(ctx.admin, int(args[0]))
    return None


@route(Cb.chart, admin=False, anyone=True)
def show_chart(ctx: Ctx, args: list[str]) -> None:
    user = _target(ctx, args)
    if user is None:
        return ctx.toast(ctx.tr(T.not_allowed), alert=True)
    days = UserDailyUsage.last_days(user.id, DAYS)
    text = caption(ctx, user, days)
    key = [str(user.id)] if ctx.admin else []
    # A person's chart is their screen (Back); an admin's is a message of its own (Close)
    last = btn(ctx.tr(T.back), Cb.back) if ctx.person else btn(ctx.tr(T.close), Cb.close)
    markup = keyboard([btn(ctx.tr(T.refresh), Cb.chart, *key, "r"), last])
    ctx.toast()
    chat_action(ctx.chat_id, "upload_photo")
    png = render(days)
    # A person's chart takes the place of their screen; an admin's opens as a message of its own, refreshed in place
    sent = show_picture(ctx, png, text, markup, in_place=ctx.person or args[-1:] == ["r"], name="usage.png")
    if sent is not None and ctx.person:
        ctx.replace_panel(*sent)

