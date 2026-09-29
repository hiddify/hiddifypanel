import re
import threading
from datetime import datetime

from flask_babel import gettext as _
from loguru import logger

# region private
from hiddifypanel import g, hutils
from hiddifypanel.cache import cache
from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, Child, ChildMode, ConfigEnum, Domain, UnsyncedUsage, UsageData, User, hconfig, set_hconfig
from hiddifypanel.panel import hiddify, usage

# import schmeas
from hiddifypanel.panel.commercial.restapi.v2.parent.schema import (
    ChildStatusInputSchema,
    ChildStatusOutputSchema,
    RegisterDataSchema,
    RegisterInputSchema,
    RegisterOutputSchema,
    SyncInputSchema,
    SyncOutputSchema,
    UsageInputOutputSchema,
    UsageResponseSchema,
)

from .api_client import NodeApiClient, NodeApiErrorSchema


def __get_register_data_for_api(name: str, mode: ChildMode) -> RegisterInputSchema:
    main_domains = Domain.get_domains()
    if not main_domains:
        raise ValueError(_("No main domains found, please add at least one domain with valid certificate"))
    base_url, uuid = hutils.flask.extract_parent_info_from_url(hiddify.get_account_panel_link(g.account, main_domains[0].domain))
    register_data = RegisterInputSchema(
        unique_id=hconfig(ConfigEnum.unique_id),
        name=name,
        mode=mode,
        node_base_url=base_url,
        panel_data=RegisterDataSchema(
            admin_users=[admin_user.to_schema() for admin_user in AdminUser.query.all()],
            users=[user.to_schema() for user in User.query.all()],
            domains=[domain.to_schema(for_parent=True) for domain in Domain.query.all()],
            # proxies=[proxy.to_schema() for proxy in Proxy.query.all()],
            # hconfigs=[*[u.to_schema() for u in StrConfig.query.all()], *[u.to_schema() for u in BoolConfig.query.all()]],
        ),
    )

    return register_data


def __get_sync_data_for_api() -> SyncInputSchema:
    # Only domains go up; users and admins come back down. Proxies and hconfigs stay on the node.
    return SyncInputSchema(domains=[domain.to_schema() for domain in Domain.query.all()])


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


def register_to_parent(name: str, apikey: str, mode: ChildMode = ChildMode.remote) -> tuple[bool, str]:
    # get parent link its format is "https://panel.hiddify.com/<admin_proxy_path>/"
    p_url = __get_parent_panel_url()
    if not p_url:
        logger.error("Parent url is empty")
        return False, "Parent url is empty"

    payload = __get_register_data_for_api(name, mode)
    res = NodeApiClient(p_url, apikey).put("/api/v2/parent/register/", payload, RegisterOutputSchema)
    if isinstance(res, NodeApiErrorSchema):
        logger.error(f"Error while registering to parent: {res.msg}")
        return False, res.msg

    if not res.parent_unique_id:
        return False, "Parent did not return its unique id"

    # The parent has already stored this node; a failure here must not surface as a 500
    # (and re-registering must work), so upsert the parent row and report errors.
    try:
        # TODO: change the bulk_register and such methods to accept models instead of dict
        AdminUser.bulk_register(res.admin_users, commit=False)
        User.bulk_register(res.users, commit=False)

        parent = Child.by_unique_id(res.parent_unique_id)
        if parent is None:
            db.session.add(Child(unique_id=res.parent_unique_id, name=res.parent_unique_id, mode=ChildMode.parent))
        else:
            parent.mode = ChildMode.parent

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception("Error while saving parent data after registering")
        return False, str(e)

    logger.success("Successfully registered to parent")
    cache.invalidate_all_cached_functions()
    return True, ""


def sync_with_parent() -> bool:
    # sync usage first

    p_url = __get_parent_panel_url()
    if not p_url:
        logger.error("Error while syncing with parent: Parent url is empty")
        return False
    payload = __get_sync_data_for_api()
    res = NodeApiClient(p_url).put("/api/v2/parent/sync/", payload, SyncOutputSchema)
    if isinstance(res, NodeApiErrorSchema):
        logger.error(f"Error while syncing with parent: {res.msg}")
        return False
    AdminUser.bulk_register(res.admin_users, commit=False, remove=True)
    User.bulk_register(res.users, commit=False, remove=True)
    db.session.commit()
    logger.success("Successfully synced with parent")
    cache.invalidate_all_cached_functions()
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
        UnsyncedUsage.add_usages(usages)
        usage.add_users_usage_new(usages, 0)
        return False

    for u in res.users:
        data = u.model_dump()
        User.add_or_update(commit=False, **data)
    db.session.commit()

    UnsyncedUsage.clear_all(commit=True)

    sync_time = hutils.convert.time_to_json(res.response_time)
    set_hconfig(ConfigEnum.last_users_sync, sync_time, commit=True)
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
            sync_with_parent()
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
