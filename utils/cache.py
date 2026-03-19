"""
Caching with TTL support using cachetools.
Falls back to functools.lru_cache if cachetools is not installed.
"""

import functools

try:
    from cachetools import TTLCache, cached

    _HAS_CACHETOOLS = True
except ImportError:
    _HAS_CACHETOOLS = False


def cache_data(ttl=3600, show_spinner=False):
    """TTL-aware cache decorator. Evicts entries after `ttl` seconds."""
    if _HAS_CACHETOOLS:
        _cache = TTLCache(maxsize=512, ttl=ttl)

        def decorator(func):
            @cached(cache=_cache)
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator
    else:
        return functools.lru_cache(maxsize=256)


def cache_resource():
    """Singleton-cache decorator for expensive resources (e.g. EE init)."""
    if _HAS_CACHETOOLS:
        _cache = TTLCache(maxsize=1, ttl=86400)

        def decorator(func):
            @cached(cache=_cache)
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator
    else:
        return functools.lru_cache(maxsize=1)
