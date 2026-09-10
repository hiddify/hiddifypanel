import os
from pickle import dumps, loads
from typing import TYPE_CHECKING, Protocol

import redis
from loguru import logger
from redis_cache import RedisCache, chunks, compact_dump

redis_client = redis.from_url(os.environ["REDIS_URI_MAIN"])
# print(os.environ["REDIS_URI_MAIN"])


class CustomRedisCache(RedisCache):
    def __init__(self, redis_client, prefix="rc", serializer=compact_dump, deserializer=loads, key_serializer=None, support_cluster=True, exception_handler=None):
        super().__init__(redis_client, prefix, serializer, deserializer, key_serializer, support_cluster, exception_handler)
        self.cached_functions = set()

    def cache(self, ttl=0, limit=0, namespace=None, exception_handler=None):
        res = super().cache(ttl, limit, namespace, exception_handler)
        self.cached_functions.add(res)
        return res

    def invalidate_all_cached_functions(self):
        try:
            for f in self.cached_functions:
                f.invalidate_all()
            logger.trace("Invalidating all cached functions")
            chunks_gen = chunks(f"{self.prefix}*", 5000)
            for keys in chunks_gen:
                self.client.delete(*keys)
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
