from __future__ import annotations

from sqlalchemy import event, inspect as sa_inspect
from sqlalchemy.orm import Session, object_session

_FLAG = "invalidate_function_cache"
_NODE_TIME_KEYS = frozenset({"last_node_to_parent_time", "last_parent_to_node_time"})
_SERVER_IP_HEALTH_KEYS = frozenset({"health_status", "last_health_check", "last_health_error"})


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


def session_requires_cache_invalidation(session: Session) -> bool:
    from hiddifypanel.models.child import Child
    from hiddifypanel.models.custom_proxy import CustomProxy, CustomProxyClientCore, ProxyTemplate
    from hiddifypanel.models.domain import Domain
    from hiddifypanel.models.proxy_base_config import ProxyBaseConfig
    from hiddifypanel.models.server_ip import ServerIp

    always = (Domain, CustomProxy, CustomProxyClientCore, ProxyTemplate, ProxyBaseConfig)
    for obj in session.new:
        if isinstance(obj, always) or isinstance(obj, (Child, ServerIp)):
            return True
    for obj in session.deleted:
        if isinstance(obj, always) or isinstance(obj, (Child, ServerIp)):
            return True
    for obj in session.dirty:
        if isinstance(obj, always):
            return True
        if isinstance(obj, Child) and child_has_non_time_changes(obj):
            return True
        if isinstance(obj, ServerIp) and _has_non_skipped_column_changes(obj, _SERVER_IP_HEALTH_KEYS):
            return True
    return False


def _flag_session(target, *args, **kwargs) -> None:
    session = object_session(target)
    if session is not None:
        session.info[_FLAG] = True


def _register_collection_listeners() -> None:
    from hiddifypanel.models.domain import Domain

    for rel in (Domain.show_domains, Domain.custom_proxies):
        event.listen(rel, "append", _flag_session)
        event.listen(rel, "remove", _flag_session)
        event.listen(rel, "bulk_replace", _flag_session)


@event.listens_for(Session, "before_flush")
def _flag_cache_invalidation(session: Session, flush_context, instances) -> None:
    if session.info.get(_FLAG):
        return
    if session_requires_cache_invalidation(session):
        session.info[_FLAG] = True


@event.listens_for(Session, "after_commit")
def _invalidate_cache_after_commit(session: Session) -> None:
    if not session.info.pop(_FLAG, False):
        return
    from hiddifypanel.cache import cache
    from hiddifypanel.proxy_v3.config_builder.jinja_render import clear_jinja_template_caches

    cache.invalidate_all_cached_functions()
    clear_jinja_template_caches()


@event.listens_for(Session, "after_rollback")
def _clear_cache_invalidation_flag(session: Session) -> None:
    session.info.pop(_FLAG, None)


_register_collection_listeners()
