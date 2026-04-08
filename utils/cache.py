"""
Caching with TTL support using cachetools.
Falls back to a custom dict-based TTL cache if cachetools is not installed.
"""

import functools
import time

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
    try:
        hash(v)
        return v
    except TypeError:
        return str(v)


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
        # Fallback: dict-based cache with TTL tracking (no lru_cache)
        _store: dict = {}  # key -> (value, expiry_timestamp)

        def _evict_expired():
            now = time.monotonic()
            expired = [k for k, (_, exp) in _store.items() if now >= exp]
            for k in expired:
                del _store[k]

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                _evict_expired()
                key = _hashable_key(*args, **kwargs)
                entry = _store.get(key)
                if entry is not None:
                    value, expiry = entry
                    if time.monotonic() < expiry:
                        return value
                    del _store[key]
                # Enforce maxsize
                if len(_store) >= 256:
                    _store.pop(next(iter(_store)))
                result = func(*args, **kwargs)
                _store[key] = (result, time.monotonic() + ttl)
                return result

            return wrapper

        return decorator


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
        _store: dict = {}  # key -> (value, expiry_timestamp)

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                key = _hashable_key(*args, **kwargs)
                entry = _store.get(key)
                if entry is not None:
                    value, expiry = entry
                    if time.monotonic() < expiry:
                        return value
                _store.clear()
                result = func(*args, **kwargs)
                _store[key] = (result, time.monotonic() + 86400)
                return result

            return wrapper

        return decorator
