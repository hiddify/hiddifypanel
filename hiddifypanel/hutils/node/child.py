import socket
from datetime import datetime

from loguru import logger
from strenum import StrEnum

from hiddifypanel import hutils
from hiddifypanel.cache import cache
from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, BoolConfig, Child, ChildMode, ConfigEnum, Domain, Proxy, StrConfig, UnsyncedUsage, UsageData, User, hconfig, set_hconfig
from hiddifypanel.panel import usage

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

# region private


def __get_register_data_for_api(name: str, mode: ChildMode) -> RegisterInputSchema:

    register_data = RegisterInputSchema(
        unique_id=hconfig(ConfigEnum.unique_id),
        name=name,
        mode=mode,
        panel_data=RegisterDataSchema(
            admin_users=[admin_user.to_schema() for admin_user in AdminUser.query.all()],
            users=[user.to_schema() for user in User.query.all()],
            domains=[domain.to_schema() for domain in Domain.query.all()],
            proxies=[proxy.to_schema() for proxy in Proxy.query.all()],
            hconfigs=[*[u.to_schema() for u in StrConfig.query.all()], *[u.to_schema() for u in BoolConfig.query.all()]],
        ),
    )

    return register_data


class SyncFields(StrEnum):
    domains = "domains"
    proxies = "proxies"
    hconfigs = "hconfigs"


def __get_sync_data_for_api(*fields: SyncFields) -> SyncInputSchema:
    sync_data = SyncInputSchema()
    if len(fields) == 0:
        sync_data.domains = [domain.to_schema() for domain in Domain.query.all()]
        sync_data.proxies = [proxy.to_schema() for proxy in Proxy.query.all()]
        sync_data.hconfigs = [*[u.to_schema() for u in StrConfig.query.all()], *[u.to_schema() for u in BoolConfig.query.all()]]
    else:
        for f in fields:
            match f:
                case SyncFields.domains:
                    sync_data.domains = [domain.to_schema() for domain in Domain.query.all()]
                case SyncFields.proxies:
                    sync_data.proxies = [proxy.to_schema() for proxy in Proxy.query.all()]
                case SyncFields.hconfigs:
                    sync_data.hconfigs = [*[u.to_schema() for u in StrConfig.query.all()], *[u.to_schema() for u in BoolConfig.query.all()]]

    return sync_data


def __get_parent_panel_url() -> str:
    domain, proxy_path, uuid = hutils.flask.extract_parent_info_from_url(hconfig(ConfigEnum.parent_panel))
    if not domain or not proxy_path or not uuid:
        return ""
    url = "https://" + f"{domain}/{proxy_path.removesuffix('/')}"
    return url


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


def register_to_parent(name: str, apikey: str, mode: ChildMode = ChildMode.remote) -> bool:
    # get parent link its format is "https://panel.hiddify.com/<admin_proxy_path>/"
    p_url = __get_parent_panel_url()
    if not p_url:
        logger.error("Parent url is empty")
        return False

    payload = __get_register_data_for_api(name, mode)
    res = NodeApiClient(p_url, apikey).put("/api/v2/parent/register/", payload, RegisterOutputSchema)
    if isinstance(res, NodeApiErrorSchema):
        logger.error(f"Error while registering to parent: {res.msg}")
        return False

    # TODO: change the bulk_register and such methods to accept models instead of dict
    AdminUser.bulk_register(res.admin_users, commit=False)
    User.bulk_register(res.users, commit=False)

    # add new child as parent
    db.session.add(Child(unique_id=res.parent_unique_id, name=socket.gethostname() or res.parent_unique_id, mode=ChildMode.parent))

    db.session.commit()

    logger.success("Successfully registered to parent")
    cache.invalidate_all_cached_functions()
    return True


def sync_with_parent(*fields: SyncFields) -> bool:
    # sync usage first

    p_url = __get_parent_panel_url()
    if not p_url:
        logger.error("Error while syncing with parent: Parent url is empty")
        return False
    payload = __get_sync_data_for_api(*fields)
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
