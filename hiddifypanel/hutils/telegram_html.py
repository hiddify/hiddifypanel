"""Messages for Telegram (``parse_mode="HTML"``): plain text, a small Markdown, or HTML → the HTML subset Telegram accepts.

Telegram refuses a whole message for one tag it does not know, so HTML is cut down to its tags (the rest keeps only its
text) and Markdown is turned into them. https://core.telegram.org/bots/api#html-style
"""

from __future__ import annotations

import html
import re
from enum import StrEnum
from html.parser import HTMLParser

TEXT_LIMIT = 4096  # characters of a message
CAPTION_LIMIT = 1024  # characters of a photo's caption

# Telegram's tags (and the attributes it reads)
_ALLOWED: dict[str, set[str]] = {
    "b": set(),
    "strong": set(),
    "i": set(),
    "em": set(),
    "u": set(),
    "ins": set(),
    "s": set(),
    "strike": set(),
    "del": set(),
    "a": {"href"},
    "code": {"class"},
    "pre": set(),
    "blockquote": {"expandable"},
    "tg-spoiler": set(),
    "span": {"class"},
}
_SAFE_URL = re.compile(r"^(https?://|tg://|mailto:)", re.IGNORECASE)
_BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"}


class MessageFormat(StrEnum):
    plain = "plain"
    markdown = "markdown"
    html = "html"


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.open: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self.out.append("\n")
            return
        if tag == "li":
            self.out.append("• ")
            return
        allowed = _ALLOWED.get(tag)
        if allowed is None:
            return
        kept: list[str] = []
        for name, value in attrs:
            if name not in allowed:
                continue
            value = value or ""
            if name == "href" and not _SAFE_URL.match(value):
                continue
            if tag == "span" and (name != "class" or value != "tg-spoiler"):
                continue
            if tag == "code" and name == "class" and not value.startswith("language-"):
                continue
            kept.append(f' {name}="{html.escape(value, quote=True)}"' if name != "expandable" else " expandable")
        if tag == "span" and not kept:
            return  # a span means nothing to Telegram but the spoiler
        if tag == "a" and not kept:
            return  # a link without a safe address: its text only
        self.out.append(f"<{tag}{''.join(kept)}>")
        self.open.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCK:
            self.out.append("\n")
        if tag in self.open:
            while self.open:  # close what is still open inside it (Telegram needs them nested)
                last = self.open.pop()
                self.out.append(f"</{last}>")
                if last == tag:
                    break

    def handle_data(self, data: str) -> None:
        self.out.append(html.escape(data, quote=False))

    def result(self) -> str:
        self.close()
        return "".join(self.out) + "".join(f"</{t}>" for t in reversed(self.open))


def sanitize_html(text: str) -> str:
    """HTML cut down to Telegram's tags; other tags keep only their text, scripts and styles are dropped."""
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", text or "")
    parser = _Sanitizer()
    parser.feed(text)
    return _tidy(parser.result())


_PLACEHOLDER = "\x00{}\x00"


def markdown_to_html(text: str) -> str:
    """A Markdown subset: **bold**, *italic* / _italic_, __underline__, ~~strike~~, ||spoiler||, `code`, ```code blocks```,
    [links](https://…), # headings (bold), > quotes, - lists (•)."""
    saved: list[str] = []

    def keep(fragment: str) -> str:
        saved.append(fragment)
        return _PLACEHOLDER.format(len(saved) - 1)

    def fence(m: re.Match[str]) -> str:
        lang = re.sub(r"[^\w+-]", "", m.group(1) or "")
        code = html.escape(m.group(2).strip("\n"), quote=False)
        attr = f' class="language-{lang}"' if lang else ""
        return keep(f"<pre><code{attr}>{code}</code></pre>")

    text = re.sub(r"```([^\n`]*)\n(.*?)```", fence, (text or "").replace("\r\n", "\n"), flags=re.DOTALL)
    text = re.sub(r"`([^`\n]+)`", lambda m: keep(f"<code>{html.escape(m.group(1), quote=False)}</code>"), text)

    def link(m: re.Match[str]) -> str:
        label, url = m.group(1), m.group(2).strip()
        if not _SAFE_URL.match(url):
            return m.group(0)
        return keep(f'<a href="{html.escape(url, quote=True)}">') + label + keep("</a>")

    text = re.sub(r"\[([^\]\n]+)\]\(([^)\s]+)\)", link, text)
    text = html.escape(text, quote=False)

    lines: list[str] = []
    quote: list[str] = []

    def flush_quote() -> None:
        if quote:
            lines.append("<blockquote>" + "\n".join(quote) + "</blockquote>")
            quote.clear()

    for line in text.split("\n"):
        if m := re.match(r"^&gt;\s?(.*)$", line):
            quote.append(m.group(1))
            continue
        flush_quote()
        if m := re.match(r"^#{1,6}\s+(.*)$", line):
            line = f"<b>{m.group(1)}</b>"
        elif m := re.match(r"^\s*[-*+]\s+(.*)$", line):
            line = f"• {m.group(1)}"
        lines.append(line)
    flush_quote()
    text = "\n".join(lines)

    inline = [
        (r"\*\*(.+?)\*\*", "b"),
        (r"__(.+?)__", "u"),
        (r"~~(.+?)~~", "s"),
        (r"\|\|(.+?)\|\|", "tg-spoiler"),
        (r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", "i"),
        (r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])", "i"),
    ]
    for pattern, tag in inline:
        text = re.sub(pattern, rf"<{tag}>\1</{tag}>", text)
    text = re.sub("\x00(\\d+)\x00", lambda m: saved[int(m.group(1))], text)
    return _tidy(text)


def to_telegram_html(text: str, fmt: MessageFormat | str) -> str:
    fmt = MessageFormat(fmt)
    if fmt is MessageFormat.markdown:
        return markdown_to_html(text)
    if fmt is MessageFormat.html:
        return sanitize_html(text)
    return _tidy(html.escape(text or "", quote=False))


def visible_length(telegram_html: str) -> int:
    """Characters Telegram counts toward its limits (the text without the tags)."""
    return len(html.unescape(re.sub(r"<[^>]+>", "", telegram_html or "")))


def _tidy(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip()
