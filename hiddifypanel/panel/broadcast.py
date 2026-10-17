"""Sending a message to users over the Telegram bot: who gets it, and the sending itself (in the background, with its
progress in redis for the page).

Only users of the admin (and their sub-admins) who started the bot (a telegram id), never deleted ones.
"""

from __future__ import annotations

import datetime
import json
import threading
import time
import uuid as uuid_lib
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from flask import Flask
from loguru import logger
from sqlalchemy.orm import Query

from hiddifypanel.database import db
from hiddifypanel.hutils.telegram_html import CAPTION_LIMIT, visible_length
from hiddifypanel.models import AdminUser, User

JOB_TTL = 24 * 3600
_JOB_KEY = "hiddify:broadcast:job:"
SEND_INTERVAL = 0.05  # Telegram allows ~30 messages a second to different chats
MAX_ERRORS_KEPT = 50


class Audience(StrEnum):
    all = "all"
    active = "active"
    expired = "expired"
    offline_1h = "offline_1h"
    offline_1d = "offline_1d"
    offline_1w = "offline_1w"
    selected = "selected"


class JobState(StrEnum):
    running = "running"
    done = "done"
    failed = "failed"


@dataclass(slots=True)
class BroadcastJob:
    id: str
    admin_id: int
    total: int
    sent: int = 0
    failed: int = 0
    state: JobState = JobState.running
    started: float = field(default_factory=time.time)
    finished: float | None = None
    errors: list[dict[str, str]] = field(default_factory=list)  # {"name", "error"}, the first MAX_ERRORS_KEPT

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BroadcastJob:
        return cls(**{**data, "state": JobState(data.get("state", JobState.running))})


# ---------------------------------------------------------------------------------------------- recipients


def _reachable_users(admin: AdminUser) -> Query:
    """Users of ``admin`` and its sub-admins that can get a message: not deleted, with a telegram id."""
    return User.query.filter(
        User.added_by.in_(admin.recursive_sub_admins_ids()),
        User.deleted.isnot(True),
        User.telegram_id.isnot(None),
        User.telegram_id != 0,
    )


def _offline_since(delta: datetime.timedelta) -> Callable[[User], bool]:
    since = datetime.datetime.now() - delta
    return lambda u: bool(u.is_active) and (u.last_online is None or u.last_online < since)


_FILTERS: dict[Audience, Callable[[User], bool]] = {
    Audience.all: lambda u: True,
    Audience.active: lambda u: bool(u.is_active),
    Audience.expired: lambda u: not u.is_active,
}


def _filter(audience: Audience) -> Callable[[User], bool]:
    offline = {Audience.offline_1h: datetime.timedelta(hours=1), Audience.offline_1d: datetime.timedelta(days=1), Audience.offline_1w: datetime.timedelta(days=7)}
    if audience in offline:
        return _offline_since(offline[audience])
    return _FILTERS[audience]


def recipients(admin: AdminUser, audience: Audience, user_ids: list[int] | None = None) -> list[User]:
    query = _reachable_users(admin)
    if audience is Audience.selected:
        return query.filter(User.id.in_(user_ids or [])).all() if user_ids else []
    keep = _filter(audience)
    return [u for u in query.all() if keep(u)]


def audience_counts(admin: AdminUser) -> dict[str, int]:
    users = _reachable_users(admin).all()
    return {a.value: sum(1 for u in users if _filter(a)(u)) for a in Audience if a is not Audience.selected}


def reachable_ids(admin: AdminUser, user_ids: list[int]) -> list[int]:
    """Which of ``user_ids`` can get a message (for the "selected users" count)."""
    if not user_ids:
        return []
    return [uid for (uid,) in _reachable_users(admin).filter(User.id.in_(user_ids)).with_entities(User.id).all()]


# ---------------------------------------------------------------------------------------------- jobs


def _redis():
    from hiddifypanel.cache import redis_client

    return redis_client


def get_job(job_id: str) -> BroadcastJob | None:
    raw = _redis().get(_JOB_KEY + job_id)
    if not raw:
        return None
    try:
        return BroadcastJob.from_dict(json.loads(raw))
    except (ValueError, TypeError):
        return None


def _save(job: BroadcastJob) -> None:
    _redis().set(_JOB_KEY + job.id, json.dumps(job.to_dict()), ex=JOB_TTL)
    try:
        from hiddifypanel.live import changes

        changes.publish(["broadcast", f"broadcast:{job.id}"])
    except Exception as e:
        logger.debug(f"broadcast progress not published: {e}")


@dataclass(frozen=True, slots=True)
class Message:
    html: str  # Telegram HTML (hutils.telegram_html)
    image: bytes | None = None
    image_name: str = "image.jpg"
    add_usage: bool = True  # each user's usage and their buttons after the text (as the bot's own messages)


def _send_one(bot: Any, user: User, message: Message) -> None:
    from hiddifypanel.panel.commercial.telegrambot import Usage

    text = message.html
    keyboard = None
    if message.add_usage:
        keyboard = Usage.user_keyboard(user.uuid)
        text = f"{text}\n\n{Usage.get_usage_msg(user.uuid)}".strip()
    if message.image is not None:
        if visible_length(text) <= CAPTION_LIMIT:
            _with_retry(lambda: bot.send_photo(user.telegram_id, (message.image_name, message.image), caption=text or None, parse_mode="HTML", reply_markup=keyboard))
            return
        _with_retry(lambda: bot.send_photo(user.telegram_id, (message.image_name, message.image)))
    if text:
        _with_retry(lambda: bot.send_message(user.telegram_id, text, parse_mode="HTML", reply_markup=keyboard))


def _with_retry(call: Callable[[], Any]) -> None:
    """One retry after Telegram's "too many requests" (it says how long to wait)."""
    from telebot.apihelper import ApiTelegramException

    try:
        call()
    except ApiTelegramException as e:
        params = (e.result_json or {}).get("parameters") or {}
        if e.error_code != 429 or not params.get("retry_after"):
            raise
        time.sleep(min(float(params["retry_after"]), 30))
        call()


def start(app: Flask, admin: AdminUser, users: list[User], message: Message) -> BroadcastJob:
    """Send ``message`` to ``users`` in the background; the job (in redis) tells the page how far it got."""
    from hiddifypanel.panel.commercial.restapi.v1.tgbot import bot

    job = BroadcastJob(id=uuid_lib.uuid4().hex[:12], admin_id=admin.id, total=len(users))
    _save(job)
    user_ids = [u.id for u in users]

    def run() -> None:
        with app.app_context():
            try:
                for uid in user_ids:
                    user = db.session.get(User, uid)
                    if user is None:
                        job.failed += 1
                        continue
                    try:
                        _send_one(bot, user, message)
                        job.sent += 1
                    except Exception as e:
                        job.failed += 1
                        if len(job.errors) < MAX_ERRORS_KEPT:
                            job.errors.append({"name": user.name or str(user.id), "error": str(e)[:300]})
                        logger.info(f"broadcast {job.id}: not sent to user {user.id}: {e}")
                    _save(job)
                    time.sleep(SEND_INTERVAL)
                job.state = JobState.done
            except Exception as e:
                logger.exception(f"broadcast {job.id} stopped: {e}")
                job.state = JobState.failed
                job.errors.append({"name": "", "error": str(e)[:300]})
            finally:
                job.finished = time.time()
                _save(job)
                db.session.remove()

    threading.Thread(target=run, name=f"broadcast-{job.id}", daemon=True).start()
    return job
