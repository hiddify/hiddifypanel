"""HTML an admin writes for the users' page (the support box, ``branding_freetext``): HTML5 layout and formatting with
inline styles, nothing that runs code or reaches outside the box.

The user page shows it as is, so it is cleaned when saved: no scripts, event handlers, forms, frames or ``<style>``
blocks (those would restyle the whole page); links and media only over http(s), mailto, tel and tg (Telegram);
``style`` keeps layout and text properties, without positioning (nothing may cover the rest of the page) or ``url()``
(no loading from elsewhere).
"""

from __future__ import annotations

import re

import tinycss2
from bleach import clean
from bleach.css_sanitizer import CSSSanitizer

TAGS = frozenset(
    {
        # text
        "a", "abbr", "acronym", "b", "bdi", "bdo", "big", "br", "cite", "code", "data", "del", "dfn", "em", "font", "i",
        "ins", "kbd", "mark", "q", "s", "samp", "small", "span", "strike", "strong", "sub", "sup", "time", "tt", "u",
        "var", "wbr", "ruby", "rp", "rt",
        # blocks
        "address", "article", "aside", "blockquote", "center", "details", "div", "figcaption", "figure", "footer",
        "h1", "h2", "h3", "h4", "h5", "h6", "header", "hgroup", "hr", "main", "nav", "p", "pre", "section", "summary",
        # lists and tables
        "dd", "dl", "dt", "li", "ol", "ul", "caption", "col", "colgroup", "table", "tbody", "td", "tfoot", "th", "thead", "tr",
        # media
        "audio", "img", "picture", "source", "track", "video",
    }
)

_COMMON = ["align", "class", "dir", "lang", "role", "style", "title", "valign", "width", "height", "bgcolor"]
ATTRIBUTES = {
    "*": _COMMON,
    "a": [*_COMMON, "href", "target", "rel", "name"],
    "font": [*_COMMON, "color", "face", "size"],
    "img": [*_COMMON, "src", "alt", "loading", "srcset", "sizes"],
    "video": [*_COMMON, "src", "poster", "controls", "autoplay", "loop", "muted", "playsinline", "preload"],
    "audio": [*_COMMON, "src", "controls", "autoplay", "loop", "muted", "preload"],
    "source": ["src", "srcset", "type", "media", "sizes"],
    "track": ["src", "kind", "srclang", "label", "default"],
    "table": [*_COMMON, "border", "cellpadding", "cellspacing"],
    "td": [*_COMMON, "colspan", "rowspan", "headers"],
    "th": [*_COMMON, "colspan", "rowspan", "headers", "scope"],
    "col": [*_COMMON, "span"],
    "colgroup": [*_COMMON, "span"],
    "ol": [*_COMMON, "start", "type", "reversed"],
    "ul": [*_COMMON, "type"],
    "li": [*_COMMON, "value"],
    "details": [*_COMMON, "open"],
    "time": [*_COMMON, "datetime"],
    "data": [*_COMMON, "value"],
    "blockquote": [*_COMMON, "cite"],
    "q": [*_COMMON, "cite"],
    "del": [*_COMMON, "cite", "datetime"],
    "ins": [*_COMMON, "cite", "datetime"],
}
PROTOCOLS = frozenset({"http", "https", "mailto", "tel", "tg"})
_SIDES = ("top", "right", "bottom", "left")
CSS_PROPERTIES = frozenset(
    {
        # colour and text
        "color", "background", "background-color", "background-image", "opacity", "font", "font-family", "font-size",
        "font-style", "font-variant", "font-weight", "line-height", "letter-spacing", "word-spacing", "text-align",
        "text-decoration", "text-decoration-color", "text-decoration-line", "text-decoration-style", "text-indent",
        "text-transform", "text-shadow", "text-overflow", "white-space", "word-break", "overflow-wrap", "direction",
        "unicode-bidi", "vertical-align", "list-style", "list-style-type", "list-style-position",
        # box
        "margin", "padding", "border", "border-width", "border-style", "border-color", "border-radius", "border-collapse",
        "border-spacing", "box-shadow", "box-sizing", "outline", "display", "width", "height", "min-width", "max-width",
        "min-height", "max-height", "overflow", "overflow-x", "overflow-y", "float", "clear", "object-fit", "aspect-ratio",
        "table-layout", "caption-side",
        *(f"{prop}-{side}" for prop in ("margin", "padding", "border") for side in _SIDES),
        *(f"border-{side}-{part}" for side in _SIDES for part in ("width", "style", "color")),
        *(f"border-{v}-{h}-radius" for v in ("top", "bottom") for h in ("left", "right")),
        # the same by writing direction (right-to-left pages): margin-inline-start, border-inline-start…
        *(f"{prop}-{axis}{end}" for prop in ("margin", "padding", "border") for axis in ("inline", "block") for end in ("", "-start", "-end")),
        *(f"border-{axis}-{end}-{part}" for axis in ("inline", "block") for end in ("start", "end") for part in ("width", "style", "color")),
        # flex and grid
        "flex", "flex-direction", "flex-wrap", "flex-flow", "flex-grow", "flex-shrink", "flex-basis", "order",
        "justify-content", "justify-items", "align-items", "align-self", "align-content", "place-items", "place-content",
        "gap", "row-gap", "column-gap", "grid-template-columns", "grid-template-rows", "grid-column", "grid-row",
    }
)


class _NoUrlCSS(CSSSanitizer):
    """bleach checks only the property names: also drop a declaration that loads something (``url()``,
    ``image-set()``…), so a ``background`` stays a colour or a gradient."""

    def sanitize_css(self, style: str) -> str:
        kept = []
        for token in tinycss2.parse_declaration_list(style, skip_comments=True, skip_whitespace=True):
            if token.type != "declaration" or token.lower_name not in self.allowed_css_properties:
                continue
            value = tinycss2.serialize(token.value).lower()
            if any(bad in value for bad in ("url(", "image(", "image-set(", "expression(", "\\")):
                continue
            kept.append(f"{token.name}: {tinycss2.serialize(token.value).strip()}{' !important' if token.important else ''}")
        return "; ".join(kept)


_CSS = _NoUrlCSS(allowed_css_properties=CSS_PROPERTIES)


# removed with what is inside them: bleach would keep a script's or a stylesheet's text as text
_CODE_ELEMENTS = re.compile(r"<(script|style|template|noscript|iframe|object|textarea|title)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL)


def clean_user_html(text: str | None) -> str:
    return clean(_CODE_ELEMENTS.sub("", text or ""), tags=TAGS, attributes=ATTRIBUTES, protocols=PROTOCOLS, css_sanitizer=_CSS, strip=True, strip_comments=True)
