"""Hiddify-style QR codes as PNG, matching the panels (admin_v2/src/shared/utils/hiddify-qr.ts): round dots, soft
rounded eyes, black on white, and the Hiddify logo in the middle with only the dots that would touch it removed."""

from __future__ import annotations

import io
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from PIL import Image as PILImage

LOGO_PATH = Path(__file__).resolve().parents[3] / "static" / "images" / "hiddify-qr-logo.png"
MODULE_PX = 14  # drawn large, then scaled down: smooth edges
QUIET_MODULES = 3
LOGO_RATIO = 0.25  # logo width / code width
LOGO_MARGIN = 0.6  # clear modules around the logo
DOT_RATIO = 0.75
EYE_RADIUS = 5 / 150  # corner radius / code size
OUTPUT_PX = 640


@cache
def _logo() -> PILImage.Image | None:
    from PIL import Image

    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
    except OSError:
        return None
    # The gray glyph turns black to match the code; its white outline stays white.
    r, g, b, a = logo.split()
    light = r.point(lambda v: max(0, round((v - 73) * 255 / (255 - 73))))
    return Image.merge("RGBA", (light, light, light, a))


def render(data: str) -> bytes | None:
    """The QR code for ``data`` as PNG bytes, or None when segno/Pillow are not installed."""
    try:
        import segno
    except ImportError:
        logger.warning("tgbot: install segno for QR codes")
        return None
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        # Without Pillow: a plain code (no dots, no logo) still scans.
        logger.warning("tgbot: install pillow for Hiddify-style QR codes")
        out = io.BytesIO()
        segno.make(data, error="m").save(out, kind="png", scale=16, border=3)
        return out.getvalue()

    matrix = [list(row) for row in segno.make(data, error="h", boost_error=False).matrix]
    n = len(matrix)
    code_px = n * MODULE_PX
    size = code_px + 2 * QUIET_MODULES * MODULE_PX
    origin = QUIET_MODULES * MODULE_PX
    image = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(image)

    logo = _logo()
    box: tuple[float, float, float, float] | None = None
    alpha = None
    if logo:
        lw = code_px * LOGO_RATIO
        lh = lw * logo.height / logo.width
        box = (origin + (code_px - lw) / 2, origin + (code_px - lh) / 2, lw, lh)
        alpha = logo.getchannel("A").resize((max(int(lw), 1), max(int(lh), 1)))

    def near_logo(cx: float, cy: float) -> bool:
        if not box or alpha is None:
            return False
        bx, by, bw, bh = box
        reach = MODULE_PX * (0.5 + LOGO_MARGIN)
        if not (bx - reach <= cx <= bx + bw + reach and by - reach <= cy <= by + bh + reach):
            return False
        for i in range(7):
            for j in range(7):
                px, py = cx - reach + 2 * reach * i / 6 - bx, cy - reach + 2 * reach * j / 6 - by
                if 0 <= px < alpha.width and 0 <= py < alpha.height and alpha.getpixel((int(px), int(py))) > 40:
                    return True
        return False

    def in_eye(x: int, y: int) -> bool:
        return (x < 7 and y < 7) or (x >= n - 7 and y < 7) or (x < 7 and y >= n - 7)

    dot = MODULE_PX * DOT_RATIO
    for y, row in enumerate(matrix):
        for x, on in enumerate(row):
            if not on or in_eye(x, y):
                continue
            cx, cy = origin + (x + 0.5) * MODULE_PX, origin + (y + 0.5) * MODULE_PX
            if near_logo(cx, cy):
                continue
            draw.ellipse((cx - dot / 2, cy - dot / 2, cx + dot / 2, cy + dot / 2), fill="black")

    radius = code_px * EYE_RADIUS
    for ex, ey in ((0, 0), (n - 7, 0), (0, n - 7)):
        x0, y0 = origin + ex * MODULE_PX, origin + ey * MODULE_PX
        outer = (x0, y0, x0 + 7 * MODULE_PX - 1, y0 + 7 * MODULE_PX - 1)
        draw.rounded_rectangle(outer, radius=radius * 1.4, fill="black")
        draw.rounded_rectangle((outer[0] + MODULE_PX, outer[1] + MODULE_PX, outer[2] - MODULE_PX, outer[3] - MODULE_PX), radius=radius, fill="white")
        draw.rounded_rectangle((outer[0] + 2 * MODULE_PX, outer[1] + 2 * MODULE_PX, outer[2] - 2 * MODULE_PX, outer[3] - 2 * MODULE_PX), radius=radius * 0.8, fill="black")

    if logo and box:
        bx, by, bw, bh = box
        image.paste(logo.resize((int(bw), int(bh)), Image.Resampling.LANCZOS), (int(bx), int(by)), logo.resize((int(bw), int(bh)), Image.Resampling.LANCZOS))

    out = io.BytesIO()
    image.resize((OUTPUT_PX, OUTPUT_PX), Image.Resampling.LANCZOS).save(out, format="PNG", optimize=True)
    return out.getvalue()
