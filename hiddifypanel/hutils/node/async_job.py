"""Long calls between panels as jobs: the call that starts one answers at once (HTTP 202 and a job id), the caller asks
for the result every few seconds.

A registration can take a minute on a big panel, and every web server or CDN between the panels (Cloudflare gives up
after ~100 s, others after ~60 s) cuts a request that waits that long: "504 Gateway Time-out". Short requests are not cut.

Results are kept in Redis for a few minutes. Callers that do not send ``ASYNC_HEADER`` (older panels) are answered the old way.
"""

from __future__ import annotations

import contextvars
import json
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, NotRequired, TypedDict, cast

import redis
from apiflask.exceptions import HTTPError
from flask import current_app, request
from loguru import logger

from hiddifypanel import g
from hiddifypanel.cache import redis_client
from hiddifypanel.models.admin import AdminUser
from hiddifypanel.models.child import Child
from hiddifypanel.models.user import User

from .api_client import NodeApiClient, NodeApiErrorSchema

type Json = None | bool | int | float | str | list[Json] | dict[str, Json]
type JsonObject = dict[str, Json]

ASYNC_HEADER = "X-Async-Job"
TTL = 900  # the result waits this long for whoever started the job
POLL_SECONDS = 2.0


class JobError(TypedDict):
    status: int
    message: str
    detail: JsonObject


class JobState(TypedDict):
    state: Literal["running", "done", "failed"]
    result: NotRequired[JsonObject]
    error: NotRequired[JobError]


def wants_job() -> bool:
    """The caller of this request asked for a job (older panels do not, and wait for the answer)."""
    return bool(request.headers.get(ASYNC_HEADER) == "1")


@dataclass(frozen=True)
class _Context:
    """What the request knew about who is asking, to be picked up again in the job's thread by id (database objects of the
    request cannot be used from another thread)."""

    child_id: int
    account_uuid: str
    account_is_admin: bool
    node_id: int | None
    proxy_path: str | None


def _capture() -> _Context:
    child = getattr(g, "child", None)
    account = getattr(g, "account", None)
    node = getattr(g, "node", None)
    return _Context(
        child_id=int(child.id) if child is not None else 0,
        account_uuid=str(account.uuid) if account is not None and getattr(account, "uuid", None) else "",
        account_is_admin=isinstance(account, AdminUser),
        node_id=int(node.id) if node is not None else None,
        proxy_path=getattr(g, "proxy_path", None),
    )


def _restore(ctx: _Context) -> None:
    # setattr: the request's `g` is typed for what a request always has; a job's may lack some of it
    setattr(g, "child", Child.by_id(ctx.child_id))  # noqa: B010
    setattr(g, "proxy_path", ctx.proxy_path)  # noqa: B010
    setattr(g, "node", Child.by_id(ctx.node_id) if ctx.node_id is not None else None)  # noqa: B010
    if ctx.account_uuid:
        setattr(g, "account", (AdminUser if ctx.account_is_admin else User).by_uuid(ctx.account_uuid))  # noqa: B010


def _key(job: str) -> str:
    return f"nodejob:{job}"


# The state of a job is kept in this process first, and in Redis too (for another process of the panel to answer).
# Applying a registration restarts Redis and the database on the panel: the state must not depend on Redis being there.
_memory: dict[str, tuple[float, JobState]] = {}
_fetched: dict[str, float] = {}
_lock = threading.Lock()
#: The job that the code running now belongs to (in the job's thread), so what it schedules can wait for its result to be read.
_current_job: contextvars.ContextVar[str] = contextvars.ContextVar("node_job", default="")


def _save(client: redis.Redis[bytes], job: str, state: JobState) -> None:
    now = time.monotonic()
    with _lock:
        _memory[job] = (now + TTL, state)
        for old in [k for k, (until, _) in _memory.items() if until < now]:
            _memory.pop(old, None)
            _fetched.pop(old, None)
    try:
        client.set(_key(job), json.dumps(state), ex=TTL)
    except redis.RedisError:
        logger.warning("a node job could not be saved in Redis (it is kept in this process)")


def start(work: Callable[[], JsonObject]) -> str:
    """Run ``work`` in the background (as the caller of this request); its answer, or the error it raised, is the job's result.
    Returns the job id."""
    job = uuid.uuid4().hex
    app = current_app._get_current_object()
    ctx = _capture()
    client = redis_client
    _save(client, job, {"state": "running"})

    def run() -> None:
        _current_job.set(job)
        with app.app_context():
            try:
                _restore(ctx)
                _save(client, job, {"state": "done", "result": work()})
            except HTTPError as e:  # abort(...) inside the work: the same answer the caller would have got
                detail = e.detail if isinstance(e.detail, dict) else {}
                _save(client, job, {"state": "failed", "error": {"status": e.status_code, "message": str(e.message), "detail": cast(JsonObject, detail)}})
            except Exception as e:  # noqa: BLE001
                logger.exception("a job of a node call failed")
                _save(client, job, {"state": "failed", "error": {"status": 500, "message": str(e) or type(e).__name__, "detail": {}}})

    threading.Thread(target=run, daemon=True).start()
    return job


def read(job: str) -> JobState | None:
    """The state of a job; ``None`` when there is none (never was, or the result expired). Reading a finished job marks it as fetched."""
    with _lock:
        entry = _memory.get(job)
    state: JobState | None = entry[1] if entry else None
    if state is None:
        try:
            raw = redis_client.get(_key(job))
        except redis.RedisError:
            raw = None
        state = cast(JobState, json.loads(raw)) if raw is not None else None
    if state is not None and state["state"] != "running":
        with _lock:
            _fetched[job] = time.monotonic()
    return state


def after_fetched(action: Callable[[], None], *, grace: float = 3.0, give_up: float = 90.0, fallback_delay: float = 5.0) -> None:
    """Run ``action`` in a moment, but not before whoever asked has read the result of the job this code belongs to (plus ``grace``
    seconds), and at the latest after ``give_up`` seconds. Used for what restarts the panel's services (and with them Redis and the
    database): that must not take the result away before it is read. Outside a job it simply waits ``fallback_delay``."""
    job = _current_job.get()

    def run() -> None:
        if not job:
            time.sleep(fallback_delay)
        else:
            deadline = time.monotonic() + give_up
            while time.monotonic() < deadline:
                with _lock:
                    if job in _fetched:
                        break
                time.sleep(0.5)
            time.sleep(grace)
        action()

    threading.Thread(target=run, daemon=True).start()


#: A poll that fails this many times in a row ends the wait (the other panel restarted: its job is gone with it).
MAX_POLL_FAILURES = 5


def wait(client: NodeApiClient, job_path: str, timeout: float) -> JobState | NodeApiErrorSchema:
    """Ask for the result of a job on another panel every ``POLL_SECONDS`` until it is done or failed, at most ``timeout`` seconds."""
    deadline = time.monotonic() + timeout
    failures = 0
    last: NodeApiErrorSchema | None = None
    while time.monotonic() < deadline:
        res = client.get(job_path, dict)
        if isinstance(res, NodeApiErrorSchema):
            last = res
            failures += 1
            if res.code == 404 or failures >= MAX_POLL_FAILURES:
                return res
        else:
            failures = 0
            if res.get("state") in ("done", "failed"):
                return cast(JobState, res)
        time.sleep(POLL_SECONDS)
    return last or NodeApiErrorSchema(msg=f"no result within {timeout:.0f}s", code=0, reason="ReadTimeout")


def failed_as_error(state: JobState) -> NodeApiErrorSchema:
    """A failed job as the error the same call would have given without a job (HTTP status and the JSON of its answer)."""
    error = state.get("error") or {"status": 500, "message": "failed", "detail": {}}
    body = json.dumps({"message": error["message"], "detail": error["detail"]})
    return NodeApiErrorSchema(msg=f"HTTP {error['status']} | body={body}", code=error["status"], reason="Job failed")
