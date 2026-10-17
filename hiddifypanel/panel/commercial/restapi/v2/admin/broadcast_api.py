"""Messages to users over the Telegram bot (the admin's "Send message" page)."""

from __future__ import annotations

from apiflask import abort
from flask import current_app, request
from flask.views import MethodView

from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.hutils.telegram_html import CAPTION_LIMIT, TEXT_LIMIT, MessageFormat, to_telegram_html, visible_length
from hiddifypanel.models import ConfigEnum, Role, hconfig
from hiddifypanel.panel import broadcast

ROLES = {Role.super_admin, Role.admin, Role.agent}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # Telegram's limit for a photo
IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _bot_ready() -> bool:
    from hiddifypanel.panel.commercial.restapi.v1.tgbot import bot

    return bool(hconfig(ConfigEnum.telegram_bot_token)) and bool(bot)


def _bot_username() -> str:
    from hiddifypanel.panel.commercial.restapi.v1.tgbot import bot

    return str(bot.username or "") if _bot_ready() else ""


def _ids(raw: object) -> list[int]:
    parts = raw if isinstance(raw, list) else str(raw or "").split(",")
    return sorted({int(p) for p in parts if str(p).strip().isdigit()})


def _format(raw: object) -> MessageFormat:
    try:
        return MessageFormat(str(raw or "plain"))
    except ValueError:
        abort(400, "Unknown message format")


class BroadcastApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self):
        """Send message: is the bot ready, and how many users each audience reaches (``?ids=`` for selected users)"""
        selected = _ids(request.args.get("ids"))
        return {
            "bot": _bot_ready(),
            "bot_username": _bot_username(),
            "counts": {**broadcast.audience_counts(g.account), "selected": len(broadcast.reachable_ids(g.account, selected))},
            "limits": {"text": TEXT_LIMIT, "caption": CAPTION_LIMIT, "image_bytes": MAX_IMAGE_BYTES},
        }

    def post(self):
        """Send message: send it in the background (multipart: text, format, audience, ids, add_usage, image)"""
        if not _bot_ready():
            abort(400, "The Telegram bot is not set up")
        form = request.form
        fmt = _format(form.get("format"))
        html = to_telegram_html(form.get("text") or "", fmt)
        image = request.files.get("image")
        image_bytes: bytes | None = None
        image_name = "image.jpg"
        if image and image.filename:
            ext = IMAGE_TYPES.get(image.mimetype or "")
            if not ext:
                abort(400, "The image must be JPEG, PNG or WebP")
            image_bytes = image.read(MAX_IMAGE_BYTES + 1)
            if len(image_bytes) > MAX_IMAGE_BYTES:
                abort(400, "The image is larger than 10 MB")
            image_name = f"image.{ext}"
        if not html and image_bytes is None:
            abort(400, "Write a message or add an image")
        if visible_length(html) > TEXT_LIMIT:
            abort(400, f"The message is longer than {TEXT_LIMIT} characters")
        try:
            audience = broadcast.Audience(form.get("audience") or "")
        except ValueError:
            abort(400, "Choose who gets the message")
        users = broadcast.recipients(g.account, audience, _ids(form.get("ids")))
        if not users:
            abort(400, "No user in this audience can get messages (they need to start the bot)")
        message = broadcast.Message(html=html, image=image_bytes, image_name=image_name, add_usage=form.get("add_usage", "true") != "false")
        job = broadcast.start(current_app._get_current_object(), g.account, users, message)  # type: ignore[attr-defined]
        return job.to_dict()


class BroadcastRecipientsApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self):
        """Send message: the users an audience reaches (``?audience=``, ``?ids=`` for selected users), to see and pick"""
        try:
            audience = broadcast.Audience(request.args.get("audience") or "all")
        except ValueError:
            abort(400, "Unknown audience")
        users = broadcast.recipients(g.account, audience, _ids(request.args.get("ids")))
        return {
            "users": [
                {
                    "id": u.id,
                    "name": u.name or "",
                    "active": bool(u.is_active),
                    "last_online": u.last_online.isoformat() if u.last_online and u.last_online.year > 2000 else None,  # datetime.min: never
                    "telegram_id": str(u.telegram_id),
                }
                for u in sorted(users, key=lambda u: (u.name or "").lower())
            ]
        }


class BroadcastPreviewApi(MethodView):
    decorators = [login_required(ROLES)]

    def post(self):
        """Send message: the text as Telegram will show it (its HTML), and its length"""
        data = request.get_json(silent=True) or {}
        html = to_telegram_html(str(data.get("text") or ""), _format(data.get("format")))
        return {"html": html, "length": visible_length(html)}


class BroadcastJobApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self, job_id: str):
        """Send message: how far a sending got"""
        job = broadcast.get_job(job_id)
        if job is None or (job.admin_id != g.account.id and g.account.mode != "super_admin"):
            abort(404, "Not found")
        return job.to_dict()
