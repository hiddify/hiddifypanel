"""The panel's app icons in any color (the admin panel's and the user page's).

Each is a glass tile in the color. The admin's has a white glass hexagon on it, in a ring of that color and with the
logo in that color; the user page's has the white logo.
Its lighting was measured once from the design and is kept in ``static/images/app-icon-parts`` as grey-level maps:
here every grey level becomes one color of the color's ramp (a deep shade, the color itself, lighter tints, white).
The stock icons (``DEFAULT``) are also in ``static/images`` as plain files; this module draws the other colors.
"""

from __future__ import annotations

import io
import math
import re
from functools import cache, lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage

RGB = tuple[int, int, int]

PARTS = Path(__file__).resolve().parents[1] / "static" / "images" / "app-icon-parts"
DEFAULT = "0A84FF"  # the stock icon (static/images/app-icon-admin-*.png)
BLACK = "15181E"  # the design's slate black: its tile has its own measured colors (black-lut.png)
MASTER = 512  # the parts' size
ANY_TILE = 440  # the tile inside the 192 / 512 icons: a margin and a soft shadow around it
# name -> (parts to use, size in px, cut to the tile's shape)
NAMES: dict[str, tuple[str, int, bool]] = {
    "apple-180": ("full", 180, False),  # iPhone: a full square, iOS cuts the shape out
    "192": ("any", 192, True),  # computers
    "512": ("any", 512, True),
    "maskable-512": ("mask", 512, False),  # Android: a full square with a smaller hexagon, launchers cut their own shape
    "tile-256": ("full", 256, True),  # the icon as a home screen shows it: the picture in the panel's own pages
}
KINDS = ("admin", "user")
# The stock icon's file (static/images) for each kind and name. The browser tab's icon is always the stock one.
STOCK = {
    kind: {
        "apple-180": f"app-icon-{kind}-apple-180.png",
        "192": f"app-icon-{kind}-192.png",
        "512": f"app-icon-{kind}-512.png",
        "maskable-512": f"app-icon-{kind}-maskable-512.png",
        "tile-256": f"favicon-{kind}-256.png",
    }
    for kind in KINDS
}
HEXAGON = (240, 242, 246)  # the white glass hexagon, about
MIN_CONTRAST = 1.9  # of the ring and the logo against the hexagon
MIN_LOGO_CONTRAST = 1.6  # of the user icon's white logo against its tile


def normalize(color: str | None) -> str | None:
    """``color`` as six upper-case hex digits, or None when it is not a color."""
    return color.upper() if color and re.fullmatch(r"[0-9a-fA-F]{6}", color) else None


@cache
def available() -> bool:
    """Whether icons can be drawn here (Pillow and the parts are present)."""
    try:
        import PIL  # noqa: F401
    except ImportError:
        return False
    return (PARTS / "full-tile.png").is_file() and (PARTS / "user-logo.png").is_file()


# --- color maths (OKLCH: lightness, chroma, hue) ---


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def _cbrt(v: float) -> float:
    return math.copysign(abs(v) ** (1 / 3), v)


def _rgb(color: str) -> RGB:
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def _to_oklch(rgb: RGB) -> tuple[float, float, float]:
    r, g, b = (_lin(v / 255) for v in rgb)
    l = _cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m = _cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s = _cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    a = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    bb = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def _linear(L: float, C: float, h: float) -> tuple[float, float, float]:
    a = C * math.cos(math.radians(h))
    b = C * math.sin(math.radians(h))
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def _from_oklch(L: float, C: float, h: float) -> RGB:
    """The sRGB color of an OKLCH color: chroma that sRGB cannot show is cut back, lightness and hue are kept."""
    L = min(max(L, 0.0), 1.0)

    def fits(c: float) -> bool:
        return all(-1e-4 <= v <= 1 + 1e-4 for v in _linear(L, c, h))

    if not fits(C):
        low, high = 0.0, C
        for _ in range(24):
            mid = (low + high) / 2
            if fits(mid):
                low = mid
            else:
                high = mid
        C = low
    r, g, b = (min(255, max(0, round(_gam(min(1.0, max(0.0, v))) * 255))) for v in _linear(L, C, h))
    return r, g, b


# Where each step of a ramp sits (0 = the darkest grey of the light map, 1 = white), as measured for the stock blue.
_SHADE_AT = ((0.0, 1.0), (0.04, 0.6), (0.074, 0.24))  # darker than the color, by this much of the full step
_TINT_AT = ((0.16, 0.125), (0.25, 0.30), (0.36, 0.45), (0.55, 0.66), (0.80, 0.88), (1.0, 1.0))  # mixed with white
# As a color gets darker its hue leans this way (hue -> degrees at the full step): yellows toward orange and limes
# toward green, so the lower part of a light color stays vivid instead of turning olive.
_HUE_LEAN = (
    (0, -2), (25, -3), (40, -6), (58, -10), (72, -14), (88, -14), (100, -12), (100.01, 8), (115, 8), (135, 4),
    (150, 3), (180, 5), (200, 6), (230, 4), (260, 1), (280, -2), (300, -3), (325, -2), (345, -2), (360, -2),
)  # fmt: skip
_BLUE_RAMP: tuple[tuple[float, RGB], ...] = (
    (0.00, (4, 92, 190)), (0.04, (6, 108, 216)), (0.074, (8, 122, 240)), (0.11, (10, 132, 255)), (0.16, (40, 148, 255)),
    (0.25, (82, 170, 255)), (0.36, (118, 190, 255)), (0.55, (170, 215, 255)), (0.80, (225, 240, 255)), (1.00, (255, 255, 255)),
)  # fmt: skip


def _lean(hue: float) -> float:
    for (h0, d0), (h1, d1) in zip(_HUE_LEAN, _HUE_LEAN[1:]):
        if hue <= h1:
            return d0 + (d1 - d0) * (hue - h0) / (h1 - h0) if h1 > h0 else d1
    return _HUE_LEAN[-1][1]


def _shade(rgb: RGB, k: float) -> RGB:
    """``rgb`` darker by ``k`` of a full step, as vivid as it can be there. Light colors darken less."""
    L, C, h = _to_oklch(rgb)
    step = 0.13 if L <= 0.70 else (0.07 if L >= 0.85 else 0.13 - (L - 0.70) / 0.15 * 0.06)
    return _from_oklch(L - step * k, C * (1 + 0.25 * k), (h + _lean(h) * k) % 360)


def _ramp(color: str) -> tuple[tuple[float, RGB], ...]:
    if color == DEFAULT:
        return _BLUE_RAMP
    base = _rgb(color)
    shades = tuple((at, _shade(base, k)) for at, k in _SHADE_AT)
    tints = tuple((at, (round(base[0] + (255 - base[0]) * w), round(base[1] + (255 - base[1]) * w), round(base[2] + (255 - base[2]) * w))) for at, w in _TINT_AT)
    return shades + ((0.11, base),) + tints


def _luminance(rgb: RGB) -> float:
    r, g, b = (_lin(v / 255) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ink(color: str) -> RGB:
    """The color of the ring and the logo on the white hexagon: ``color``, darkened only while it is too light to read there."""
    rgb = _rgb(color)
    L, C, h = _to_oklch(rgb)
    paper = _luminance(HEXAGON) + 0.05
    for i in range(1, 61):
        if paper / (_luminance(rgb) + 0.05) >= MIN_CONTRAST:
            break
        k = min(1.0, i / 13)
        rgb = _from_oklch(L - 0.01 * i, C * (1 + 0.25 * k), (h + _lean(h) * k) % 360)
    return rgb


def logo_ink(color: str) -> RGB:
    """The color of the user icon's logo: white, or a deep tone of ``color`` when white would not read on it."""
    rgb = _rgb(color)
    if 1.05 / (_luminance(rgb) + 0.05) >= MIN_LOGO_CONTRAST:
        return 255, 255, 255
    _, C, h = _to_oklch(rgb)
    return _from_oklch(0.3, min(C, 0.12), h)


# --- drawing ---


@cache
def _part(name: str) -> PILImage.Image:
    from PIL import Image

    with Image.open(PARTS / f"{name}.png") as im:
        return im.convert("RGB" if name == "black-lut" else ("RGBA" if name.endswith(("-body", "-shadow")) else "L"))


def _tables(color: str) -> list[list[int]]:
    """For each channel, the value of every grey level of the light map."""
    if color == BLACK:
        lut = _part("black-lut")
        return [[lut.getpixel((grey, 0))[c] for grey in range(256)] for c in range(3)]
    ramp = _ramp(color)
    tables: list[list[int]] = [[], [], []]
    for grey in range(256):
        at = min(max((grey - 12) / 243, 0.0), 1.0)
        for (a0, c0), (a1, c1) in zip(ramp, ramp[1:]):
            if at <= a1:
                f = (at - a0) / (a1 - a0)
                for c in range(3):
                    tables[c].append(int(c0[c] + (c1[c] - c0[c]) * f + 0.5))
                break
    return tables


def _compose(parts: str, color: str, kind: str) -> PILImage.Image:
    """The tile in ``color`` with the hexagon (admin) or the logo (user) on it, at the parts' size."""
    from PIL import Image

    grey = _part(f"{parts}-tile")
    im = Image.merge("RGB", [grey.point(table) for table in _tables(color)])
    if kind == "user":
        im.paste(logo_ink(color), None, _part("user-logo"))
        return im
    pen = ink(color)
    im.paste(pen, None, _part(f"{parts}-hex-ring"))
    body = _part(f"{parts}-hex-body")
    im.paste(body, None, body)
    im.paste(pen, None, _part(f"{parts}-hex-logo"))
    return im


def _resize(im: PILImage.Image, size: int) -> PILImage.Image:
    from PIL import Image

    if im.width == size:
        return im
    if im.mode == "RGBA":  # with the alpha multiplied in, so see-through edges do not bleed
        return im.convert("RGBa").resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")
    return im.resize((size, size), Image.Resampling.LANCZOS)


@lru_cache(maxsize=96)
def render(color: str, name: str, kind: str = "admin") -> bytes:
    """The PNG of the app icon ``name`` (a key of ``NAMES``) of ``kind`` in ``color`` (six upper-case hex digits)."""
    parts, size, cut = NAMES[name]
    if parts == "any":
        tile = _compose("full", color, kind)
        tile.putalpha(_part("full-alpha"))
        im = _part("any-shadow").copy()
        im.alpha_composite(_resize(tile, ANY_TILE), ((MASTER - ANY_TILE) // 2,) * 2)
    else:
        im = _compose(parts, color, kind)
        if cut:
            im.putalpha(_part("full-alpha"))
    im = _resize(im, size)
    out = io.BytesIO()
    im.save(out, "PNG", compress_level=6)
    return out.getvalue()
