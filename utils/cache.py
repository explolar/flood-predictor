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


def _make_hashable(v):
    """Convert unhashable types (list, dict) to hashable equivalents for cache keys."""
    if isinstance(v, list):
        return tuple(_make_hashable(i) for i in v)
    if isinstance(v, dict):
        return tuple(sorted((k, _make_hashable(val)) for k, val in v.items()))
    return v


def _hashable_key(*args, **kwargs):
    """Cache key function that handles lists and dicts."""
    return tuple(_make_hashable(a) for a in args) + tuple((k, _make_hashable(v)) for k, v in sorted(kwargs.items()))


def cache_data(ttl=3600, show_spinner=False):
    """TTL-aware cache decorator. Evicts entries after `ttl` seconds."""
    if _HAS_CACHETOOLS:
        _cache = TTLCache(maxsize=512, ttl=ttl)

        def decorator(func):
            @cached(cache=_cache, key=_hashable_key)
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
