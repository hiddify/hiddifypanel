import json
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from flask_babel import gettext as _
from loguru import logger

# region private
from hiddifypanel import g, hutils
from hiddifypanel.cache import cache
from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, Child, ChildMode, ConfigEnum, Domain, UnsyncedUsage, UsageData, User, hconfig, set_hconfig
from hiddifypanel.panel import hiddify, usage
from hiddifypanel.panel.commercial.restapi.v2.admin.schema import UserSchema

# import schmeas
from hiddifypanel.panel.commercial.restapi.v2.parent.schema import (
    ChildStatusInputSchema,
    ChildStatusOutputSchema,
    PanelHostSchema,
    RegisterDataSchema,
    RegisterInputSchema,
    RegisterOutputSchema,
    RegisterUsersInputSchema,
    SyncInputSchema,
    SyncOutputSchema,
    UsageInputOutputSchema,
    UsageResponseSchema,
)

from . import async_job, endpoints, steplog, sync_status
from .sync_status import SyncKind, SyncSource
from .api_client import NodeApiClient, NodeApiErrorSchema


def __get_register_data_for_api(name: str, mode: ChildMode, *, uuids_only: bool = True) -> RegisterInputSchema:
    """What the node says about itself. With ``uuids_only`` its users are only listed by uuid: the parent says which it lacks, and only
    those are sent (a parent that cannot do that is sent all of them)."""
    main_domains = Domain.get_domains()
    if not main_domains:
        raise ValueError(_("No main domains found, please add at least one domain with valid certificate"))
    # The parent calls the node on this address first: a direct domain, else a relay one, else a CDN one (it knows the others from the domains below).
    base_url, uuid = hutils.flask.extract_parent_info_from_url(hiddify.get_account_panel_link(g.account, endpoints.best_own_host() or main_domains[0].domain))
    register_data = RegisterInputSchema(
        unique_id=hconfig(ConfigEnum.unique_id),
        name=name,
        mode=mode,
        node_base_url=base_url,
        panel_hosts=[PanelHostSchema(domain=h.domain, mode=h.mode) for h in endpoints.own_hosts()],
        user_uuids=[str(u.uuid) for u in User.query.filter(User.deleted.is_(False)).with_entities(User.uuid).all()] if uuids_only else None,
        ws_sync=True,
        panel_data=RegisterDataSchema(
            admin_users=[admin_user.to_schema() for admin_user in AdminUser.query.all()],
            users=[] if uuids_only else [user.to_schema() for user in User.query.all()],
            domains=[domain.to_schema(for_parent=True) for domain in Domain.query.all()],
            # proxies=[proxy.to_schema() for proxy in Proxy.query.all()],
            # hconfigs=[*[u.to_schema() for u in StrConfig.query.all()], *[u.to_schema() for u in BoolConfig.query.all()]],
        ),
    )

    return register_data


def __get_sync_data_for_api() -> SyncInputSchema:
    # Only domains go up; users and admins come back down. Proxies and hconfigs stay on the node.
    return SyncInputSchema(domains=[domain.to_schema() for domain in Domain.query.all()], panel_hosts=[PanelHostSchema(domain=h.domain, mode=h.mode) for h in endpoints.own_hosts()])


def _active_user_uuids() -> set[str]:
    """Users the proxy cores should accept (is_active covers enable, delete, expiry, usage limit)."""
    return {str(u.uuid) for u in User.query.filter(User.deleted.is_(False)).all() if u.is_active}


def _apply_users_if_changed(before: set[str]) -> None:
    """Users came from the parent: apply them to the proxy cores, like a local user change does.

    Only when the set of active users changed, so frequent usage syncs do not reload the cores.
    """
    after = _active_user_uuids()
    if after != before:
        logger.info(f"Users from parent changed ({len(after - before)} activated, {len(before - after)} deactivated): applying users")
        hiddify.quick_apply_users()


def _apply_outbounds(items) -> bool:
    """Outbounds are the parent's: copy them (with ids) so users' and admins' choices keep pointing at them.

    Returns whether they changed. ``None`` comes from an older parent that does not send them.
    """
    if items is None:
        return False
    from hiddifypanel.proxy_v3 import outbounds as ob

    return ob.import_rows(items)


def _apply_server_config() -> None:
    """New outbounds change the routing of the cores: regenerate the server configs."""
    from hiddifypanel.panel.run_commander import Command, commander

    logger.info("Outbounds from parent changed: applying configs")
    commander(Command.apply)


def __get_parent_panel_url() -> str:
    return hconfig(ConfigEnum.parent_panel)


def _parent_base_url() -> str:
    """``https://host/<proxy_path>/`` of the parent.

    ``parent_panel`` is stored either as that base URL (settings page) or as a
    full admin link with a uuid (Node admin); accept both.
    """
    raw = (__get_parent_panel_url() or "").strip()
    base_url, _uuid = hutils.flask.extract_parent_info_from_url(raw)
    if base_url:
        return base_url
    match = re.match(r"^https?://[^/]+/[^/]+/", raw if raw.endswith("/") else raw + "/")
    return match.group(0) if match else ""


def parent_panel_host() -> str:
    """Host (and port) of the parent panel this node is connected to, or ""."""
    base_url = _parent_base_url()
    if not base_url:
        return ""
    return base_url.split("://", 1)[-1].split("/", 1)[0]


def parent_admin_dashboard_url(account_uuid: str | None, *, v2: bool = True) -> str:
    """The parent's admin dashboard for *this* admin, or "" without a parent.

    ``parent_panel`` may embed the uuid of the admin who linked the node, so it
    is never handed out as-is: the link is rebuilt with the viewer's own uuid
    (admins are synced from the parent, so it is the same account there).
    """
    base_url = _parent_base_url()
    if not base_url or not account_uuid:
        return ""
    return f"{base_url}{account_uuid}/" + ("admin/v2/" if v2 else "admin/")


# endregion


def is_registered() -> bool:
    """Checks if the current parent registered as a child"""
    try:
        logger.debug("Checking if current panel is registered with parent")
        base_url = __get_parent_panel_url()
        if not base_url:
            return False
        payload = ChildStatusInputSchema(
            child_unique_id=hconfig(ConfigEnum.unique_id),
        )

        res = NodeApiClient(base_url).post("/api/v2/parent/status/", payload, ChildStatusOutputSchema)
        if isinstance(res, NodeApiErrorSchema):
            logger.error(f"Error while checking if current panel is registered with parent: {res.msg}")
            return False

        if res.existance:
            return True
        return False
    except Exception as e:
        logger.error("Error while checking if current panel is registered with parent")
        logger.exception(e)
        return False


#: The parent stores this node's users, admins and domains before it has the answer: that can take long on a big panel (it is a job:
#: every request is short, this is how long the node waits for the job).
REGISTER_TIMEOUT = 600
#: How long after the answer (when it is not a job) the new configs are applied: applying restarts the web servers, which cuts the
#: connection the answer travels on ("SSL: UNEXPECTED_EOF_WHILE_READING" on the other side).
APPLY_DELAY_SECONDS = 5


def _after_answer(action: Callable[[], None]) -> None:
    """Do ``action`` once the answer of this registration has been read (see ``async_job.after_fetched``)."""
    async_job.after_fetched(action, fallback_delay=APPLY_DELAY_SECONDS)


@dataclass(frozen=True)
class RegisterFailure:
    """Why this panel (the node) could not register with its parent. Always the node's side tells it."""

    step: str  # what the node was doing
    kind: Literal["no_parent_url", "no_domain", "parent_timeout", "parent_connection", "parent_rejected", "parent_bad_answer", "node_data"]
    reason: str  # the technical detail
    parent_host: str = ""

    def text(self) -> str:
        where = f" ({self.parent_host})" if self.parent_host else ""
        return f"{self.step}{where}: {self.reason}"


def _register_call(p_url: str, apikey: str, payload: RegisterInputSchema, headers: dict[str, str]) -> RegisterOutputSchema | NodeApiErrorSchema:
    """Send this node's data and get the parent's answer: as a job (the parent says 202 and a job id; short requests, nothing between
    the panels cuts them), or at once from a parent that is too old to know jobs."""
    # A parent that knows jobs answers at once; one that does not answers when it is done, so the first request may wait long
    # (and is not repeated: the first one may still be running).
    starter = NodeApiClient(p_url, apikey, max_retry=3, timeout=REGISTER_TIMEOUT, retry_on_timeout=False, extra_headers=headers)
    started = starter.put("/api/v2/parent/register/", payload, dict)
    if isinstance(started, NodeApiErrorSchema):
        return started
    job = started.get("job")
    if not isinstance(job, str):  # the old, one-request answer
        try:
            return RegisterOutputSchema.model_validate(started)
        except ValueError as e:
            return NodeApiErrorSchema(msg=f"Unexpected response: {e}", code=200, reason="bad_response")
    poller = NodeApiClient(p_url, apikey, max_retry=3, timeout=30, extra_headers=headers)
    state = async_job.wait(poller, f"/api/v2/parent/register-job/{job}/", REGISTER_TIMEOUT)
    if isinstance(state, NodeApiErrorSchema):
        return state
    if state["state"] == "failed":
        return async_job.failed_as_error(state)
    try:
        answer = RegisterOutputSchema.model_validate(state.get("result"))
    except ValueError as e:
        return NodeApiErrorSchema(msg=f"Unexpected response: {e}", code=200, reason="bad_response")
    if answer.users_total is None:  # the users are in the answer (a parent that does not page them)
        return answer
    users, failure = _read_users_pages(poller, f"/api/v2/parent/register-job/{job}/users/", answer.users_total)
    if failure is not None:
        return failure
    return answer.model_copy(update={"users": users})


#: Users of the parent are read in pages of this size: each response is small enough for any proxy or CDN in the way.
USERS_PAGE = 500


def _read_users_pages(client: NodeApiClient, path: str, total: int) -> tuple[list[UserSchema], NodeApiErrorSchema | None]:
    users: list[UserSchema] = []
    offset = 0
    while offset < total:
        page = client.get(f"{path}?offset={offset}&limit={USERS_PAGE}", dict)
        if isinstance(page, NodeApiErrorSchema):
            return users, page
        try:
            rows = page.get("users")
            got = [UserSchema.model_validate(u) for u in rows] if isinstance(rows, list) else []
        except ValueError as e:
            return users, NodeApiErrorSchema(msg=f"Unexpected response: {e}", code=200, reason="bad_response")
        if not got:  # fewer users than it said (some were removed meanwhile): that is all there is
            break
        users.extend(got)
        offset += len(got)
    return users, None


def _remember_parent_hosts(hosts: list[PanelHostSchema] | None) -> None:
    """The parent's domains came with its answer: kept, for the next time the one in use is down."""
    if hosts:
        endpoints.remember_parent_hosts(endpoints.PanelHost(h.domain, h.mode) for h in hosts)


def _send_register(payload: RegisterInputSchema, p_url: str, apikey: str, parent_host: str, reg: str, headers: dict[str, str]) -> RegisterOutputSchema | NodeApiErrorSchema:
    data = payload.panel_data
    with steplog.step(reg, "node", "send the data to the parent", parent=parent_host, admins=len(data.admin_users), users_in_call=len(data.users), user_uuids=len(payload.user_uuids or []), domains=len(data.domains), timeout=REGISTER_TIMEOUT):
        return _register_call(p_url, apikey, payload, headers)


#: Users go to the parent in chunks of this size: each request is short, and the parent stores them as they come.
USERS_CHUNK = 300


def _send_missing_users(p_url: str, apikey: str, uuids: list[str], parent_host: str, reg: str) -> RegisterFailure | None:
    """Send the node's users that the parent lacks (``None`` when all went)."""
    client = NodeApiClient(p_url, apikey, max_retry=3, timeout=120, retry_on_timeout=False, extra_headers={steplog.REG_HEADER: reg} if reg else None)
    step = "sending the users the parent did not have"
    with steplog.step(reg, "node", step, users=len(uuids), chunk=USERS_CHUNK, parent=parent_host):
        for i in range(0, len(uuids), USERS_CHUNK):
            chunk = User.query.filter(User.uuid.in_(uuids[i : i + USERS_CHUNK])).all()
            res = client.put("/api/v2/parent/register-users/", RegisterUsersInputSchema(users=[u.to_schema() for u in chunk]), dict)
            if isinstance(res, NodeApiErrorSchema):
                return _classify_parent_error(res, parent_host, step)
    return None


def _parent_error_message(res: NodeApiErrorSchema) -> str:
    """What the parent said when it refused: its own message when its answer is JSON, else the HTTP error."""
    _, _, body = res.msg.partition(" | body=")
    try:
        said = json.loads(body) if body else None
    except ValueError:
        said = None
    if isinstance(said, dict) and isinstance(said.get("message"), str) and said["message"]:
        return said["message"]
    return res.msg


def _classify_parent_error(res: NodeApiErrorSchema, parent_host: str, step: str = "sending this node's data to the parent") -> RegisterFailure:
    if res.reason == "ReadTimeout":
        return RegisterFailure(step, "parent_timeout", f"no answer within {REGISTER_TIMEOUT}s ({res.msg})", parent_host)
    if res.code == 0:  # no HTTP answer at all: ConnectTimeout, SSLError, ConnectionError...
        return RegisterFailure(step, "parent_connection", f"{res.reason or 'connection error'}: {res.msg}", parent_host)
    if res.reason == "bad_response" or res.msg == "Empty response":
        return RegisterFailure(step, "parent_bad_answer", res.msg, parent_host)
    return RegisterFailure(step, "parent_rejected", f"HTTP {res.code}: {_parent_error_message(res)}", parent_host)


def register_to_parent_detailed(name: str, apikey: str, mode: ChildMode = ChildMode.remote, *, defer_apply: bool = False, reg: str = "") -> RegisterFailure | None:
    """Register this panel with its parent; ``None`` when it worked. ``reg`` is the registration id of the log lines.

    ``defer_apply``: the caller answers a request next, so what needs a restart waits for that.
    """
    # get parent link its format is "https://panel.hiddify.com/<admin_proxy_path>/"
    p_url = __get_parent_panel_url()
    parent_host = steplog.host_of(p_url) if p_url else ""
    if not p_url:
        logger.error(f"[register {reg or '-'} node] the parent address is empty")
        return RegisterFailure("reading the parent address", "no_parent_url", "Parent url is empty")

    with steplog.step(reg, "node", "collect this node's data"):
        try:
            payload = __get_register_data_for_api(name, mode)
        except ValueError as e:  # no main domain
            return RegisterFailure("collecting this node's data", "no_domain", str(e))
    headers = {async_job.ASYNC_HEADER: "1", **({steplog.REG_HEADER: reg} if reg else {})}
    res = _send_register(payload, p_url, apikey, parent_host, reg, headers)
    if isinstance(res, NodeApiErrorSchema):
        failure = _classify_parent_error(res, parent_host)
        logger.error(f"[register {reg or '-'} node] the parent {parent_host} did not accept it: {failure.kind}: {failure.reason}")
        return failure
    if res.missing_user_uuids is None and payload.user_uuids:
        # An older parent does not know the list of uuids: it takes the users in the register call, as it always did.
        logger.info(f"[register {reg or '-'} node] the parent {parent_host} is an older version: sending it all the users in the register call")
        with steplog.step(reg, "node", "collect this node's data"):
            payload = __get_register_data_for_api(name, mode, uuids_only=False)
        res = _send_register(payload, p_url, apikey, parent_host, reg, headers)
        if isinstance(res, NodeApiErrorSchema):
            failure = _classify_parent_error(res, parent_host)
            logger.error(f"[register {reg or '-'} node] the parent {parent_host} did not accept it: {failure.kind}: {failure.reason}")
            return failure
    missing_users = res.missing_user_uuids or []
    _remember_parent_hosts(res.parent_hosts)

    if not res.parent_unique_id:
        return RegisterFailure("reading the parent's answer", "parent_bad_answer", "the parent did not return its unique id", parent_host)

    # The parent has already stored this node; a failure here must not surface as a 500
    # (and re-registering must work), so upsert the parent row and report errors.
    active_before = _active_user_uuids()
    try:
        with steplog.step(reg, "node", "save what the parent sent", admins=len(res.admin_users), users=len(res.users)):
            # TODO: change the bulk_register and such methods to accept models instead of dict
            outbounds_changed = _apply_outbounds(res.outbounds)
            AdminUser.bulk_register(res.admin_users, commit=False)
            User.bulk_register(res.users, commit=False)

            parent = Child.by_unique_id(res.parent_unique_id)
            if parent is None:
                db.session.add(Child(unique_id=res.parent_unique_id, name=res.parent_unique_id, mode=ChildMode.parent))
            else:
                parent.mode = ChildMode.parent

            db.session.commit()
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        logger.exception(f"[register {reg or '-'} node] saving the parent's data failed")
        return RegisterFailure("saving the data the parent sent", "node_data", f"{type(e).__name__}: {e}", parent_host)

    if missing_users:  # only the users the parent did not have: not the ones it just sent here
        failure = _send_missing_users(p_url, apikey, missing_users, parent_host, reg)
        if failure is not None:
            logger.error(f"[register {reg or '-'} node] the parent {parent_host} did not take the node's own users: {failure.kind}: {failure.reason}")
            return failure
    sync_status.record(SyncKind.admins, SyncSource.register, len(res.admin_users))
    sync_status.record(SyncKind.users, SyncSource.register, len(res.users), via_ws=bool(res.users_via_ws), missing_sent=len(missing_users))
    sync_status.record(SyncKind.domains, SyncSource.register, len(payload.panel_data.domains), direction="sent")
    via_ws = ": its users come over the WebSocket" if res.users_via_ws else ""
    logger.success(f"[register {reg or '-'} node] registered with the parent {parent_host}{via_ws}")
    from . import sync_feed, ws_client

    sync_feed.reset_cursor()  # registering (again) starts the parent's change feed from the beginning
    ws_client.wake()
    cache.invalidate_all_cached_functions()
    if defer_apply:
        logger.info(f"[register {reg or '-'} node] applying users and configs in {APPLY_DELAY_SECONDS}s, after the answer has gone out")
        _after_answer(lambda: _apply_registered(active_before, outbounds_changed))
    else:
        _apply_registered(active_before, outbounds_changed)
    return None


def register_to_parent(name: str, apikey: str, mode: ChildMode = ChildMode.remote, *, defer_apply: bool = False) -> tuple[bool, str]:
    """``register_to_parent_detailed`` as ``(worked, message)``."""
    failure = register_to_parent_detailed(name, apikey, mode, defer_apply=defer_apply)
    return (True, "") if failure is None else (False, failure.text())


def _apply_registered(active_before: set[str], outbounds_changed: bool) -> None:
    _apply_users_if_changed(active_before)
    if outbounds_changed:
        _apply_server_config()


def sync_with_parent(pull_users: bool = True) -> bool:
    """Send this node's domains to the parent; with ``pull_users`` also take all its users/admins.

    ``pull_users=False`` is the cheap form used after local config changes: the parent only
    needs the domains (and drops its cache of this node's configs). Pulling and rewriting every
    user runs in the panel's own process and slows its requests down on panels with many users.
    """
    p_url = __get_parent_panel_url()
    if not p_url:
        logger.error("Error while syncing with parent: Parent url is empty")
        return False
    payload = __get_sync_data_for_api()
    path = "/api/v2/parent/sync/" if pull_users else "/api/v2/parent/sync/?users=0"
    res = NodeApiClient(p_url).put(path, payload, SyncOutputSchema)
    if isinstance(res, NodeApiErrorSchema):
        logger.error(f"Error while syncing with parent: {res.msg}")
        sync_status.record(SyncKind.domains, SyncSource.http_sync, ok=False, error=str(res.msg))
        return False
    _remember_parent_hosts(res.parent_hosts)
    sync_status.record(SyncKind.domains, SyncSource.http_sync, len(payload.domains), direction="sent")
    if not pull_users:
        # An older parent may still send the users; they are not needed for this call.
        logger.success("Sent domains to parent")
        return True
    active_before = _active_user_uuids()
    outbounds_changed = _apply_outbounds(res.outbounds)
    AdminUser.bulk_register(res.admin_users, commit=False, remove=True)
    User.bulk_register(res.users, commit=False, remove=True)
    db.session.commit()
    sync_status.record(SyncKind.admins, SyncSource.http_sync, len(res.admin_users))
    sync_status.record(SyncKind.users, SyncSource.http_sync, len(res.users))
    if res.outbounds is not None:
        sync_status.record(SyncKind.outbounds, SyncSource.http_sync, len(res.outbounds))
    logger.success("Successfully synced with parent")
    cache.invalidate_all_cached_functions()
    _apply_users_if_changed(active_before)
    if outbounds_changed:
        _apply_server_config()
    return True


def _send_to_parent(payload: UsageInputOutputSchema) -> UsageResponseSchema | NodeApiErrorSchema:
    p_url = __get_parent_panel_url()
    if not p_url:
        logger.error("Parent url is empty")
        return NodeApiErrorSchema(msg="Parent url is empty")
    client = NodeApiClient(p_url)
    res = client.put("/api/v2/parent/usage/", payload, UsageResponseSchema)
    return res


def sync_users_usage_with_parent(usages: list[UsageData]) -> bool:
    # Merge previously failed deltas so they are retried with this batch.
    pending = UnsyncedUsage.all_as_usage_data()
    merged: dict[str, UsageData] = {}
    for item in [*pending, *usages]:
        if not item.uuid:
            continue
        existing = merged.get(item.uuid)
        merged[item.uuid] = existing.add(item) if existing else item

    to_send = [u for u in merged.values() if u.usage > 0]

    last_sync = hconfig(ConfigEnum.last_users_sync)
    payload = UsageInputOutputSchema(
        usages=to_send,
        request_time=datetime.now(),
        last_users_sync=last_sync,
    )

    res = _send_to_parent(payload)
    if isinstance(res, NodeApiErrorSchema):
        logger.error(f"Error while syncing users usage with parent: {res.msg}")
        sync_status.record(SyncKind.usage, SyncSource.usage_report, len(to_send), ok=False, error=str(res.msg))
        UnsyncedUsage.add_usages(usages)
        usage.add_users_usage_new(usages, 0)
        return False

    active_before = _active_user_uuids()
    for u in res.users:
        data = u.model_dump()
        User.add_or_update(commit=False, **data)
    db.session.commit()
    _apply_users_if_changed(active_before)

    UnsyncedUsage.clear_all(commit=True)

    sync_time = hutils.convert.time_to_json(res.response_time)
    set_hconfig(ConfigEnum.last_users_sync, sync_time, commit=True)
    sync_status.record(SyncKind.usage, SyncSource.usage_report, len(to_send), users_back=len(res.users))
    logger.success(f"Successfully synced users usage with parent: {len(res.users)} users at {sync_time}")
    return True


# region notify parent about local config changes

_NOTIFY_PARENT_DELAY_SECONDS = 3.0
_notify_parent_lock = threading.Lock()
_notify_parent_timer: threading.Timer | None = None


def _notify_parent_now(app) -> None:
    global _notify_parent_timer
    with _notify_parent_lock:
        _notify_parent_timer = None
    with app.app_context():
        try:
            from . import shared

            if not shared.is_child() or not __get_parent_panel_url():
                return
            # The parent drops its cached copy of this node's configs on every sync.
            sync_with_parent(pull_users=False)
        except Exception:
            logger.exception("Error while notifying parent about config changes")


def schedule_notify_parent_config_changed() -> None:
    """Ask the parent (in the background) to refresh this node's configs.

    Safe to call from SQLAlchemy commit hooks: it emits no SQL here, and calls
    made within a few seconds of each other collapse into one sync.
    """
    global _notify_parent_timer
    from flask import current_app, has_app_context

    if not has_app_context():
        return
    app = current_app._get_current_object()  # type: ignore[attr-defined]
    with _notify_parent_lock:
        if _notify_parent_timer is not None:
            _notify_parent_timer.cancel()
        _notify_parent_timer = threading.Timer(_NOTIFY_PARENT_DELAY_SECONDS, _notify_parent_now, args=(app,))
        _notify_parent_timer.daemon = True
        _notify_parent_timer.start()


# endregion
