"""The server's traffic as a picture (a key of the admin's keyboard): the admin picks the last 24 hours, 7, 15 or 30
days, and gets a sharp chart (bars per hour or day, split by node, the average and the peak) with the numbers, and
the change from the period before, in the caption."""

from __future__ import annotations

import datetime
import io
import math
from dataclasses import dataclass, field

from loguru import logger
from PIL import Image, ImageDraw, ImageFont
from telebot import types

from hiddifypanel.models import AdminUser

from . import bot
from .chart import _FONTS
from .texts import T
from .ui import SELECTED, btn, Cb, chat_action, Ctx, fmt_bytes, keyboard, off_btn, route, Screen, show_picture, tg_time

#: period → (how many slots, hours or days)
PERIODS: dict[str, tuple[int, str]] = {"h24": (24, "h"), "d7": (7, "d"), "d15": (15, "d"), "d30": (30, "d")}
_PERIOD_TEXT = {"h24": T.bw_h24, "d7": T.bw_d7, "d15": T.bw_d15, "d30": T.bw_d30}
_PERIOD_TITLE = {"h24": "LAST 24 HOURS", "d7": "LAST 7 DAYS", "d15": "LAST 15 DAYS", "d30": "LAST 30 DAYS"}

S = 2  # drawn twice as big, then scaled down: smooth edges
W, H = 1600, 1000
BG = (242, 242, 247)
CARD = (255, 255, 255)
TEXT = (28, 28, 30)
MUTED = (142, 142, 147)
GRID = (229, 229, 234)
AVG = (255, 159, 10)
UP, DOWN = (52, 199, 89), (255, 59, 48)
#: one colour per node (the first is this server)
PALETTE = [(10, 132, 255), (191, 90, 242), (48, 176, 199), (255, 149, 0), (255, 55, 95), (94, 92, 230), (52, 199, 89)]


@dataclass
class Slot:
    when: datetime.datetime
    parts: dict[int, int] = field(default_factory=dict)  # node id → bytes

    @property
    def total(self) -> int:
        return sum(self.parts.values())


@dataclass
class Series:
    period: str
    slots: list[Slot]  # this period, oldest first
    previous: int  # the period before, in total
    nodes: dict[int, str]  # node id → name, in drawing order
    complete: bool = True  # every slot could be known (hours are kept only since the bot started counting them)


def collect(admin: AdminUser, period: str, now: datetime.datetime | None = None) -> Series:
    count, unit = PERIODS[period]
    now = now or datetime.datetime.now()
    if unit == "h":
        from hiddifypanel.hutils import hourly_usage

        hours = hourly_usage.last_hours(admin.recursive_sub_admins_ids(), count * 2, now)
        before, current = hours[:count], hours[count:]
        return Series(period, [Slot(when, {0: n}) for when, n in current], sum(n for _, n in before), {0: ""}, complete=any(n for _, n in hours))
    from hiddifypanel.models import DailyUsage

    stats = DailyUsage.get_dashboard_stats(admin_id=admin.id, series_days=count * 2)
    names = {int(n.id): n.name for n in stats.nodes}
    points = stats.series[-count * 2 :]
    before, current = points[:-count], points[-count:]
    slots = []
    for p in current:
        parts = {int(cid): int(c.usage or 0) for cid, c in (p.by_child or {}).items()} or {0: int(p.usage or 0)}
        slots.append(Slot(datetime.datetime.fromisoformat(str(p.date)), parts))
    used_nodes = [cid for cid in names if any(s.parts.get(cid) for s in slots)] or [0]
    return Series(period, slots, sum(int(p.usage or 0) for p in before), {cid: names.get(cid, "") for cid in used_nodes})


# --------------------------------------------------------------------------- the picture


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(_FONTS / ("Vazir-Bold.ttf" if bold else "Vazir-Medium.ttf")), size * S)
    except OSError:
        return ImageFont.load_default()


def short(n: float) -> str:
    """Bytes for the picture: 1.2 GB, 350 MB, 12 KB."""
    for unit, size in (("TB", 1024**4), ("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)):
        if n >= size:
            v = n / size
            return f"{v:.1f} {unit}" if v < 100 else f"{v:.0f} {unit}"
    return f"{n:.0f} B"


def _ascii(name: str, node_id: int) -> str:
    """A node's name on the picture (its font draws Latin letters only)."""
    return name if name and name.isascii() else ("This server" if node_id == 0 else f"Node {node_id}")


def _x_label(series: Series, i: int) -> str | None:
    slot, n = series.slots[i], len(series.slots)
    if PERIODS[series.period][1] == "h":
        return slot.when.strftime("%H:%M") if (n - 1 - i) % 3 == 0 else None
    every = {7: 1, 15: 2, 30: 5}.get(n, 1)
    if (n - 1 - i) % every:
        return None
    return slot.when.strftime("%a %d") if n == 7 else slot.when.strftime("%d %b")


def change(series: Series) -> float | None:
    """The change from the period before, in percent; None when there was nothing before."""
    total = sum(s.total for s in series.slots)
    return (total - series.previous) / series.previous * 100 if series.previous else None


def render(series: Series) -> bytes:
    img = Image.new("RGB", (W * S, H * S), BG)
    d = ImageDraw.Draw(img)
    p = lambda v: v * S  # noqa: E731
    d.rounded_rectangle((p(28), p(28), p(W - 28), p(H - 28)), radius=p(40), fill=CARD)

    totals = [s.total for s in series.slots]
    total = sum(totals)
    peak_i = max(range(len(totals)), key=totals.__getitem__) if totals else -1
    unit = PERIODS[series.period][1]
    # Head: what, how much, then the average, the peak and the change
    d.text((p(80), p(70)), f"BANDWIDTH · {_PERIOD_TITLE[series.period]}", font=_font(26, True), fill=MUTED)
    d.text((p(76), p(108)), short(total), font=_font(76, True), fill=TEXT)
    chips = []
    if totals:
        chips.append((f"Avg {short(total / len(totals))}/{'hour' if unit == 'h' else 'day'}", MUTED))
        if totals[peak_i]:
            when = series.slots[peak_i].when.strftime("%H:%M" if unit == "h" else "%d %b")
            chips.append((f"Peak {short(totals[peak_i])} · {when}", MUTED))
    pct = change(series)
    if pct is not None:
        chips.append((f"{'▲' if pct >= 0 else '▼'} {abs(pct):.0f}% vs previous", UP if pct >= 0 else DOWN))
    x = W - 80
    for text, colour in reversed(chips):  # right-aligned pills
        f = _font(24, True)
        w = d.textlength(text, font=f) / S + 44
        d.rounded_rectangle((p(x - w), p(96), p(x), p(146)), radius=p(25), fill=BG)
        d.text((p(x - w + 22), p(106)), text, font=f, fill=colour if colour != MUTED else TEXT)
        x -= w + 14

    left, right, top, bottom = 80, W - 170, 230, H - 150
    height = bottom - top
    peak = max(totals) if totals and max(totals) > 0 else 1
    # A round top for the axis: 1, 1.5, 2, 2.5 … × 10^n bytes
    mag = 10 ** math.floor(math.log10(peak)) if peak > 0 else 1
    nice = next(m * mag for m in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10) if m * mag >= peak)
    for k in range(5):
        y = bottom - height * k / 4
        d.line((p(left), p(y), p(right), p(y)), fill=GRID, width=p(2))
        if k:
            d.text((p(right + 18), p(y - 16)), short(nice * k / 4), font=_font(22), fill=MUTED)

    n = max(len(series.slots), 1)
    slot_w = (right - left) / n
    bar_w = max(slot_w * (0.62 if n <= 15 else 0.7), 6)
    colours = {cid: PALETTE[i % len(PALETTE)] for i, cid in enumerate(series.nodes)}
    for i, s in enumerate(series.slots):
        x0 = left + slot_w * i + (slot_w - bar_w) / 2
        x1 = x0 + bar_w
        if s.total <= 0:
            d.rounded_rectangle((p(x0), p(bottom - 6), p(x1), p(bottom)), radius=p(3), fill=GRID)
        else:
            y = bottom
            order = [cid for cid in series.nodes if s.parts.get(cid)] or list(s.parts)
            full_top = bottom - max(height * s.total / nice, 8)
            # the whole bar rounded on top, the nodes stacked inside it (drawn on a piece the size of the bar)
            box = (int(p(x0)), int(p(full_top)), int(p(x1)), int(p(bottom)))
            bw_, bh_ = max(box[2] - box[0], 1), max(box[3] - box[1], 1)
            mask = Image.new("L", (bw_, bh_), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw_ - 1, bh_ - 1), radius=int(p(min(bar_w / 2, 12))), fill=255)
            piece = Image.new("RGB", (bw_, bh_), CARD)
            pd = ImageDraw.Draw(piece)
            for cid in order:
                h_part = height * s.parts.get(cid, 0) / nice
                pd.rectangle((0, int(p(y - h_part)) - box[1], bw_, int(p(y)) - box[1]), fill=colours.get(cid, PALETTE[0]))
                y -= h_part
            img.paste(piece, box[:2], mask)
            if i == peak_i:
                label = short(s.total)
                f = _font(20, True)
                w = d.textlength(label, font=f) / S
                d.text((p((x0 + x1) / 2 - w / 2), p(full_top - 32)), label, font=f, fill=TEXT)
        if (label := _x_label(series, i)) is not None:
            f = _font(20)
            w = d.textlength(label, font=f) / S
            d.text((p((x0 + x1) / 2 - w / 2), p(bottom + 16)), label, font=f, fill=TEXT if i == n - 1 else MUTED)

    if total:  # the average, dashed
        avg = total / n
        y = bottom - height * avg / nice
        xx = left
        while xx < right:
            d.line((p(xx), p(y), p(min(xx + 14, right)), p(y)), fill=AVG, width=p(3))
            xx += 24
        d.text((p(right + 18), p(y - 16)), "avg", font=_font(22, True), fill=AVG)

    if len(series.nodes) > 1:  # the legend: a dot and a name per node
        xx = left
        for cid, name in series.nodes.items():
            label = _ascii(name, cid)
            d.ellipse((p(xx), p(H - 92), p(xx + 18), p(H - 74)), fill=colours[cid])
            d.text((p(xx + 28), p(H - 98)), label, font=_font(22), fill=TEXT)
            xx += 28 + d.textlength(label, font=_font(22)) / S + 40

    out = io.BytesIO()
    img.resize((W, H), Image.LANCZOS).save(out, format="PNG", optimize=True)
    return out.getvalue()


# --------------------------------------------------------------------------- the screens


def caption(ctx: Ctx, series: Series) -> str:
    totals = [s.total for s in series.slots]
    total = sum(totals)
    hours = PERIODS[series.period][1] == "h"
    lines = [f"📈 <b>{ctx.tr(T.bw_title)}</b>  ·  {ctx.tr(_PERIOD_TEXT[series.period])}", ""]
    if not total:
        lines.append(f"<i>{ctx.tr(T.bw_empty)}</i>")
        if hours:
            lines.append(f"<i>{ctx.tr(T.bw_hours_note)}</i>")
        return "\n".join(lines)
    peak_i = max(range(len(totals)), key=totals.__getitem__)
    peak_at = series.slots[peak_i].when
    when = tg_time(peak_at, "t", peak_at.strftime("%H:%M")) if hours else tg_time(peak_at.date(), "D", peak_at.strftime("%Y-%m-%d"))
    lines += [
        f"📦 {ctx.tr(T.chart_total)}: <b>{fmt_bytes(total, ctx.lang)}</b>",
        f"〰️ {ctx.tr(T.bw_avg_hour if hours else T.chart_avg)}: <b>{fmt_bytes(total / len(totals), ctx.lang)}</b>",
        f"🔝 {ctx.tr(T.chart_peak)}: <b>{fmt_bytes(totals[peak_i], ctx.lang)}</b> ({when})",
    ]
    pct = change(series)
    if pct is not None:
        lines.append(f"{'📈' if pct >= 0 else '📉'} {ctx.tr(T.bw_change)}: <b>{'+' if pct >= 0 else '−'}{abs(pct):.0f}%</b>")
    if len(series.nodes) > 1:
        lines.append("")
        for cid, name in series.nodes.items():
            used = sum(s.parts.get(cid, 0) for s in series.slots)
            lines.append(f"🖥 {name or ctx.tr(T.st_server)}: {fmt_bytes(used, ctx.lang)}")
    if hours and not series.complete:
        lines += ["", f"<i>{ctx.tr(T.bw_hours_note)}</i>"]
    return "\n".join(lines)


def _markup(ctx: Ctx, period: str) -> types.InlineKeyboardMarkup:
    tabs = [
        off_btn(SELECTED + ctx.tr(_PERIOD_TEXT[key]), otherwise=btn(SELECTED + ctx.tr(_PERIOD_TEXT[key]), Cb.bandwidth, key, "r")) if key == period else btn(ctx.tr(_PERIOD_TEXT[key]), Cb.bandwidth, key, "r")
        for key in PERIODS
    ]
    return keyboard(tabs[:2], tabs[2:], [btn(ctx.tr(T.refresh), Cb.bandwidth, period, "r"), btn(ctx.tr(T.back), Cb.back)])


def pick_screen(ctx: Ctx) -> Screen:
    tabs = [btn(ctx.tr(_PERIOD_TEXT[key]), Cb.bandwidth, key) for key in PERIODS]
    return Screen(f"📈 <b>{ctx.tr(T.bw_title)}</b>\n\n{ctx.tr(T.bw_pick)}", keyboard(tabs[:2], tabs[2:], [btn(ctx.tr(T.back), Cb.back)]))


@route(Cb.bandwidth, admin=True)
def show_bandwidth(ctx: Ctx, args: list[str]) -> None:
    admin = ctx.admin
    assert admin
    period = args[0] if args and args[0] in PERIODS else ""
    if not period:
        ctx.show(pick_screen(ctx))
        return ctx.toast()
    ctx.toast(ctx.tr(T.bw_drawing))
    chat_action(ctx.chat_id, "upload_photo")
    series = collect(admin, period)
    png, text, markup = render(series), caption(ctx, series), _markup(ctx, period)
    # The chart takes the place of the screen pressed (the period question, or itself for another period)
    sent = show_picture(ctx, png, text, markup, in_place=True, name="bandwidth.png")
    if sent is not None:
        ctx.replace_panel(*sent)  # a new message: the one before it goes
