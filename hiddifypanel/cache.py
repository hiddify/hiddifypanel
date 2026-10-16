import os
from collections.abc import Iterable
from enum import StrEnum
from pickle import dumps, loads
from typing import TYPE_CHECKING, Protocol

import redis
from loguru import logger
from redis_cache import RedisCache, compact_dump

redis_client = redis.from_url(os.environ["REDIS_URI_MAIN"])
# print(os.environ["REDIS_URI_MAIN"])


class CacheMode(StrEnum):
    """What a cached function's result is built from. A change of that data clears only the functions with its mode
    (``cache.invalidate(CacheMode.users)``); see models/cache_events.py for what is cleared on commit."""

    users = "users"
    domains = "domains"
    settings = "settings"
    proxies = "proxies"  # custom proxies and their client cores
    templates = "templates"  # proxy templates and base configs
    nodes = "nodes"  # childs / parent-node links
    server_ips = "server_ips"


#: Functions that do not say what they are built from: cleared by any change except users' (the behaviour before modes).
DEFAULT_MODES = frozenset(CacheMode) - {CacheMode.users}
#: Built from nothing the panel changes (DNS answers, server IPs, core versions): only their TTL (or a forced clear) ends them.
STATIC = frozenset()


class CustomRedisCache(RedisCache):
    def __init__(self, redis_client, prefix="rc", serializer=compact_dump, deserializer=loads, key_serializer=None, support_cluster=True, exception_handler=None):
        super().__init__(redis_client, prefix, serializer, deserializer, key_serializer, support_cluster, exception_handler)
        #: cached function (redis_cache CacheDecorator) -> the modes whose changes clear it
        self.function_modes: dict = {}

    @property
    def cached_functions(self):
        return set(self.function_modes)

    def cache(self, ttl=0, limit=0, namespace=None, exception_handler=None, modes: Iterable[CacheMode] | None = None):
        """``modes``: what the result is built from (default: everything but users; ``STATIC``: nothing the panel changes)."""
        res = super().cache(ttl, limit, namespace, exception_handler)
        self.function_modes[res] = DEFAULT_MODES if modes is None else frozenset(CacheMode(m) for m in modes)
        return res

    def _key_prefix(self, fn) -> bytes:
        # Every function's keys are "{prefix:namespace}:..." (redis_cache, cluster mode) or "prefix:namespace:...".
        return f"{fn.get_full_prefix()}:".encode()

    def _delete_matching(self, pattern: str, *, only: tuple[bytes, ...] | None = None, keep: tuple[bytes, ...] = ()) -> None:
        # One SCAN with a large COUNT: redis_cache's invalidate_all scans the whole keyspace 10 keys at a time, once per
        # cached function (~40 ms each with the login sessions in the same database).
        batch: list = []
        for key in self.client.scan_iter(match=pattern, count=1000):
            if (only is not None and not key.startswith(only)) or (keep and key.startswith(keep)):
                continue
            batch.append(key)
            if len(batch) >= 500:
                self.client.delete(*batch)
                batch.clear()
        if batch:
            self.client.delete(*batch)

    def functions_for(self, *modes: CacheMode | str) -> list:
        wanted = {CacheMode(m) for m in modes}
        return [fn for fn, fn_modes in self.function_modes.items() if fn_modes & wanted and fn.namespace]

    def invalidate(self, *modes: CacheMode | str) -> bool:
        """Clear the functions built from any of ``modes`` (e.g. ``cache.invalidate(CacheMode.users)``)."""
        try:
            prefixes = tuple(self._key_prefix(fn) for fn in self.functions_for(*modes))
            if prefixes:
                self._delete_matching(f"{{{self.prefix}:*", only=prefixes)
                self._delete_matching(f"{self.prefix}:*", only=prefixes)
            if CacheMode.templates in modes:
                from hiddifypanel.proxy_v3.jinja_download import invalidate_download_cache

                invalidate_download_cache()
            logger.trace(f"Invalidated cached functions of {sorted(map(str, modes))}: {len(prefixes)}")
            return True
        except Exception as err:
            with logger.contextualize(error=err):
                logger.error(f"Failed to invalidate cached functions of {sorted(map(str, modes))}")
            return False

    def invalidate_all_cached_functions(self):
        """Clear every cached function except the STATIC ones (DNS answers, server IPs, core versions)."""
        try:
            logger.trace("Invalidating all cached functions")
            keep = tuple(self._key_prefix(fn) for fn, fn_modes in self.function_modes.items() if not fn_modes and fn.namespace)
            self._delete_matching(f"{{{self.prefix}:*", keep=keep)
            self._delete_matching(f"{self.prefix}*", keep=keep)
            from hiddifypanel.proxy_v3.jinja_download import invalidate_download_cache

            invalidate_download_cache()
            logger.trace("Successfully invalidated all cached functions")
            return True
        except Exception as err:
            with logger.contextualize(error=err):
                logger.error("Failed to invalidate all cached functions")
            return False


if TYPE_CHECKING:
    from collections.abc import Callable
    from functools import wraps
    from typing import Any, ParamSpec, TypeVar

    P = ParamSpec("P")
    R = TypeVar("R")

    class CachedCallable(Protocol[P, R]):
        """A callable that also exposes cache-invalidation."""

        def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...

        def invalidate(self, *args: Any, **kwargs: Any) -> None: ...
        def invalidate_all_cached_functions(self): ...
        def invalidate_all(self): ...

    class Cache:
        def cache(self, *decorator_args: Any, **decorator_kwargs: Any) -> Callable[[Callable[P, R]], CachedCallable[P, R]]:
            def decorator(func: Callable[P, R]) -> CachedCallable[P, R]:
                @wraps(func)
                def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                    # Use decorator_args/decorator_kwargs here
                    # Implement your caching logic...
                    return func(*args, **kwargs)

                return wrapper

            return decorator

        def invalidate_all_cached_functions(self): ...

        def invalidate(self, *args: Any, **kwargs: Any) -> None: ...

    cache = Cache()

    # (name: str, times: int = 1) -> str
else:
    cache = CustomRedisCache(redis_client=redis_client, prefix="h", serializer=dumps, deserializer=loads)
