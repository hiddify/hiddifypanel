"""Buttons inside the message (Telegram's rich messages, Bot API 10.3+): soft, pill-shaped, tinted buttons, the
same look as a channel post's, instead of the solid inline keyboard under a bubble.

Every request goes through ``apihelper._make_request``: a text message (sendMessage / editMessageText) that carries
an inline keyboard is sent there as a rich message instead, its text turned into rich HTML and each keyboard row
into a row of buttons in the body. No screen has to know about it. If Telegram refuses the rich form, the request
goes as it was (the classic keyboard), so nothing is lost; refused sends turn rich messages off for an hour.

Photos (a user's card), copies of media and keyboards edited alone stay classic: those messages cannot be rich.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any

from loguru import logger

#: Turned off for a while after Telegram refused a rich send (a Bot API older than 10.3 on a self-hosted server…)
_OFF_KEY = "tgbot:rich:off"
_OFF_S = 3600

_BLOCKS = re.compile(r"(<blockquote(?: expandable)?>.*?</blockquote>|<pre>.*?</pre>)", re.S)
_PARAS = re.compile(r"\n[ \t]*\n+")


def body_html(text: str) -> str:
    """Telegram HTML (lines by \\n, quotes, code) as rich HTML: paragraphs, <br> for single line breaks."""
    out = []
    for part in _BLOCKS.split(text or ""):
        if not part:
            continue
        if part.startswith("<blockquote"):
            open_tag, inner = part[: part.index(">") + 1], part[part.index(">") + 1 : -len("</blockquote>")]
            out.append(f"{open_tag}{inner.strip(chr(10)).replace(chr(10), '<br>')}</blockquote>")
        elif part.startswith("<pre>"):
            inner = part[len("<pre>") : -len("</pre>")]
            out.append(part if inner.startswith("<code") else f"<pre><code>{inner}</code></pre>")
        else:
            for para in _PARAS.split(part.strip("\n")):
                if para.strip():
                    out.append("<p>" + para.strip("\n").replace("\n", "<br>") + "</p>")
    return "".join(out)


def _style(button: dict[str, Any]) -> str | None:
    """The button's colour; one without (Back, pages, filters) is the soft grey "link" style when it is a
    callback button, blue when it is a link."""
    style = button.get("style")
    if style in ("success", "danger", "primary"):
        return style
    if "disabled" in button:
        return None
    if "callback_data" in button:
        return "link"
    if "url" in button:
        return "primary"
    return None


def button_html(button: dict[str, Any]) -> str | None:
    """One inline keyboard button as a rich <tg-button>, or None for a kind rich buttons do not take."""
    label = html.escape(str(button.get("text") or ""), quote=False)
    attrs: list[tuple[str, str]]
    if "disabled" in button:  # greyed out, does nothing
        attrs = [("type", "disabled")]
    elif "callback_data" in button:
        attrs = [("type", "callback_data"), ("data", button["callback_data"])]
    elif "url" in button:
        attrs = [("type", "url"), ("url", button["url"])]
    elif "copy_text" in button:
        attrs = [("type", "copy_text"), ("text", (button["copy_text"] or {}).get("text", ""))]
    elif "web_app" in button:
        attrs = [("type", "web_app"), ("url", (button["web_app"] or {}).get("url", ""))]
    else:
        return None
    if style := _style(button):
        attrs.append(("style", style))
    return "<tg-button " + " ".join(f'{k}="{html.escape(str(v), quote=True)}"' for k, v in attrs) + f">{label}</tg-button>"


def rich_html(text: str, markup: dict[str, Any]) -> str | None:
    """The message as rich HTML with its keyboard inside, or None when a button cannot be rich (it then stays
    classic as a whole)."""
    rows = []
    for row in markup.get("inline_keyboard") or []:
        buttons = [button_html(b) for b in row]
        if not buttons or any(b is None for b in buttons) or len(buttons) > 8:
            return None
        rows.append("<tg-button-row>" + "".join(buttons) + "</tg-button-row>")
    return body_html(text) + "".join(rows)


def _markup(params: dict[str, Any]) -> dict[str, Any] | None:
    raw = params.get("reply_markup")
    if not raw:
        return None
    try:
        markup = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return None
    return markup if isinstance(markup, dict) and markup.get("inline_keyboard") else None


def classic(params: dict[str, Any]) -> dict[str, Any]:
    """A classic keyboard draws blue (primary) as blue text on blue: there it has no colour."""
    markup = _markup(params)
    if not markup:
        return params
    for row in markup["inline_keyboard"]:
        for b in row:
            if b.get("style") == "primary":
                b.pop("style")
    return {**params, "reply_markup": json.dumps(markup, ensure_ascii=False)}


def _off() -> bool:
    try:
        from hiddifypanel.cache import redis_client

        return bool(redis_client.get(_OFF_KEY))
    except Exception:
        return False


def _refuses_rich(error: object) -> bool:
    """Telegram does not know rich messages at all (an older self-hosted Bot API server): only then they go off for a
    while. A message refused for what it holds (a date too far, a button) just goes classic itself."""
    return getattr(error, "error_code", None) == 404 or "method not found" in str(error).lower()


def _turn_off(reason: object) -> None:
    logger.warning(f"tgbot: Telegram refused a rich message ({reason}); classic keyboards for an hour")
    try:
        from hiddifypanel.cache import redis_client

        redis_client.set(_OFF_KEY, "1", ex=_OFF_S)
    except Exception:
        pass


#: What a rich send keeps from a sendMessage / editMessageText request (the rest is the text's own, now inside)
_KEEP = ("chat_id", "message_id", "inline_message_id", "business_connection_id", "message_thread_id", "disable_notification", "protect_content", "reply_parameters", "message_effect_id")


# --------------------------------------------------------------------------- a card: its QR photo inside

_CARD = "card"


def _card(text: str, markup: dict[str, Any] | None) -> str | None:
    """The card's rich message: its photo (uploaded with the request as ``_CARD``) on top, then text and buttons."""
    page = rich_html(text, markup or {})
    if page is None:
        return None
    rich = {"html": f'<img src="tg://photo?id={_CARD}"/>' + page, "media": [{"id": _CARD, "media": {"type": "photo", "media": f"attach://{_CARD}"}}]}
    return json.dumps(rich, ensure_ascii=False)


def send_card(chat_id: int, text: str, markup: dict[str, Any] | None, png: bytes, *, effect: str | None = None) -> dict[str, Any] | None:
    """A card (a QR photo, its text and buttons) as one rich message; None when it cannot be rich (then the caller
    sends the classic photo). Raises what Telegram answers otherwise."""
    import io

    from telebot import apihelper

    from . import bot

    card = None if _off() else _card(text, markup)
    if card is None:
        return None
    params: dict[str, Any] = {"chat_id": chat_id, "rich_message": card}
    if effect:
        params["message_effect_id"] = effect
    try:
        sent = apihelper._make_request(bot.token, "sendRichMessage", "post", params, {_CARD: ("qr.png", io.BytesIO(png))})
        return sent if isinstance(sent, dict) and "message_id" in sent else None  # anything else: the classic photo
    except apihelper.ApiTelegramException as e:
        if effect and "effect" in str(e).lower():  # no confetti here: the card all the same
            return send_card(chat_id, text, markup, png)
        if _refuses_rich(e):
            _turn_off(e)
        else:
            logger.info(f"tgbot: this card went classic ({e})")
        return None


def edit_card(chat_id: int, message_id: int, text: str, markup: dict[str, Any] | None, png: bytes) -> bool:
    """The message becomes this card, in place (a rich message, or an older classic text). False when it cannot
    (a classic photo, too old…); raises "not modified" for the caller to ignore."""
    import io

    from telebot import apihelper

    from . import bot

    card = None if _off() else _card(text, markup)
    if card is None:
        return False
    try:
        apihelper._make_request(bot.token, "editMessageText", "post", {"chat_id": chat_id, "message_id": message_id, "rich_message": card}, {_CARD: ("qr.png", io.BytesIO(png))})
        return True
    except apihelper.ApiTelegramException as e:
        if "not modified" in str(e):
            raise
        logger.debug(f"tgbot: card not edited in place: {e}")
        return False


def send_document(chat_id: int, text: str, markup: dict[str, Any] | None, document, file_name: str) -> dict[str, Any] | None:
    """A file (a backup) with its text and buttons as one rich message, the file on top; None when it cannot be
    rich (the caller sends the classic document). Raises what Telegram answers about the buttons or the file."""
    from telebot import apihelper

    from . import bot

    page = None if _off() else rich_html(text, markup or {})
    if page is None:
        return None
    rich = {"html": '<tg-document src="tg://document?id=file"/>' + page, "media": [{"id": "file", "media": {"type": "document", "media": "attach://file"}}]}
    document.seek(0)
    sent = apihelper._make_request(bot.token, "sendRichMessage", "post", {"chat_id": chat_id, "rich_message": json.dumps(rich, ensure_ascii=False)}, {"file": (file_name, document)})
    return sent if isinstance(sent, dict) and "message_id" in sent else None


def install() -> None:
    from telebot import apihelper

    original = apihelper._make_request
    if getattr(original, "_hiddify_rich", False):
        return

    def rich_or_classic(token, method_name, method="get", params=None, files=None):
        if params and "rich_message" in params:  # made rich already (a card with its photo): as it is
            return original(token, method_name, method, params, files)
        if method_name not in ("sendMessage", "editMessageText"):
            if params and method_name in ("sendPhoto", "copyMessage", "editMessageCaption", "editMessageMedia", "editMessageReplyMarkup", "sendDocument"):
                params = classic(params)
            return original(token, method_name, method, params, files)
        markup = _markup(params or {})
        # A send is rich when it has buttons; an edit always tries rich (the message may be rich already, and a rich
        # message stays rich), and falls back to a classic edit for an older, classic one
        wanted = (markup is not None or method_name == "editMessageText") and not files and not _off()
        page = rich_html(str(params.get("text") or ""), markup or {}) if wanted else None
        if page is None:
            return original(token, method_name, method, classic(params) if params else params, files)
        rich = {k: v for k, v in params.items() if k in _KEEP}
        rich["rich_message"] = json.dumps({"html": page}, ensure_ascii=False)
        try:
            return original(token, "sendRichMessage" if method_name == "sendMessage" else "editMessageText", "post", rich, None)
        except apihelper.ApiTelegramException as e:
            if "not modified" in str(e):
                raise
            if method_name == "sendMessage" and _refuses_rich(e):
                _turn_off(e)
            elif method_name == "sendMessage":
                logger.info(f"tgbot: this message went classic ({e})")
            else:  # an older (classic) message cannot become rich in place: edit it as it is
                logger.debug(f"tgbot: rich edit refused ({e}); classic edit")
            return original(token, method_name, method, classic(params), files)

    rich_or_classic._hiddify_rich = True  # type: ignore[attr-defined]
    apihelper._make_request = rich_or_classic
