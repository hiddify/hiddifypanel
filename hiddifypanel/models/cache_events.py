from __future__ import annotations

from sqlalchemy import event
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session, object_session

from hiddifypanel.cache import CacheMode

_FLAG = "invalidate_function_cache"
_NODE_TIME_KEYS = frozenset({"last_node_to_parent_time", "last_parent_to_node_time"})
_SERVER_IP_HEALTH_KEYS = frozenset({"health_status", "last_health_check", "last_health_error"})
#: Settings the panel itself writes all the time (usage checks, node sync): no config is built from them.
_BOOKKEEPING_SETTINGS = frozenset({"last_priodic_usage_check", "last_users_sync", "parent_sync_cursor"})


def _has_non_skipped_column_changes(obj, skip_keys: frozenset[str]) -> bool:
    state = sa_inspect(obj)
    for attr in state.mapper.column_attrs:
        if attr.key in skip_keys:
            continue
        if state.get_history(attr.key, True).has_changes():
            return True
    return False


def child_has_non_time_changes(obj) -> bool:
    """True when a Node/Child row changed fields other than heartbeat timestamps."""
    return _has_non_skipped_column_changes(obj, _NODE_TIME_KEYS)


#: User columns the usage updates write every minute: changing only these is not a user change.
_USER_USAGE_KEYS = frozenset({"current_usage", "last_online", "last_reset_time", "last_modified_time", "connected_devices"})


def changed_cache_modes(session: Session) -> set[CacheMode]:
    """The CacheModes whose data this session adds, deletes or changes (what to clear after the commit)."""
    from hiddifypanel.models.child import Child
    from hiddifypanel.models.config import BoolConfig, StrConfig
    from hiddifypanel.models.custom_proxy import CustomProxy, CustomProxyClientCore, ProxyTemplate
    from hiddifypanel.models.domain import Domain
    from hiddifypanel.models.proxy_base_config import ProxyBaseConfig
    from hiddifypanel.models.server_ip import ServerIp
    from hiddifypanel.models.user import User

    def mode_of(obj, *, dirty: bool) -> CacheMode | None:
        if isinstance(obj, Domain):
            return CacheMode.domains
        if isinstance(obj, (CustomProxy, CustomProxyClientCore)):
            return CacheMode.proxies
        if isinstance(obj, (ProxyTemplate, ProxyBaseConfig)):
            return CacheMode.templates
        if isinstance(obj, (BoolConfig, StrConfig)):
            return None if str(getattr(obj.key, "value", obj.key)) in _BOOKKEEPING_SETTINGS else CacheMode.settings
        if isinstance(obj, Child):
            return CacheMode.nodes if not dirty or child_has_non_time_changes(obj) else None
        if isinstance(obj, ServerIp):
            return CacheMode.server_ips if not dirty or _has_non_skipped_column_changes(obj, _SERVER_IP_HEALTH_KEYS) else None
        if isinstance(obj, User):
            return CacheMode.users if not dirty or _has_non_skipped_column_changes(obj, _USER_USAGE_KEYS) else None
        return None

    modes = {m for obj in (*session.new, *session.deleted) if (m := mode_of(obj, dirty=False))}
    modes |= {m for obj in session.dirty if (m := mode_of(obj, dirty=True))}
    return modes


def session_requires_cache_invalidation(session: Session) -> bool:
    """True when the session changes what the configs are built from (anything but users)."""
    return bool(changed_cache_modes(session) - {CacheMode.users})


def _flag(session: Session, modes: set[CacheMode]) -> None:
    if modes:
        session.info.setdefault(_FLAG, set()).update(modes)


def _flag_domain_links(target, *args, **kwargs) -> None:
    session = object_session(target)
    if session is not None:
        _flag(session, {CacheMode.domains})


def _register_collection_listeners() -> None:
    from hiddifypanel.models.domain import Domain

    for rel in (Domain.show_domains, Domain.custom_proxies):
        event.listen(rel, "append", _flag_domain_links)
        event.listen(rel, "remove", _flag_domain_links)
        event.listen(rel, "bulk_replace", _flag_domain_links)


@event.listens_for(Session, "before_flush")
def _flag_cache_invalidation(session: Session, flush_context, instances) -> None:
    _flag(session, changed_cache_modes(session))


@event.listens_for(Session, "after_commit")
def _invalidate_cache_after_commit(session: Session) -> None:
    modes = session.info.pop(_FLAG, None)
    if not modes:
        return
    from hiddifypanel.cache import cache

    cache.invalidate(*modes)
    if CacheMode.templates in modes:
        from hiddifypanel.proxy_v3.config_builder.jinja_render import clear_jinja_template_caches

        clear_jinja_template_caches()
    if modes - {CacheMode.users}:
        # On a node, the parent caches this node's rendered configs; tell it they changed.
        from hiddifypanel.hutils.node.child import schedule_notify_parent_config_changed

        schedule_notify_parent_config_changed()


@event.listens_for(Session, "after_rollback")
def _clear_cache_invalidation_flag(session: Session) -> None:
    session.info.pop(_FLAG, None)


_register_collection_listeners()
