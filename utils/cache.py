"""
Caching with TTL support using distributed Redis or fallback cachetools.
"""

import functools
import time
import os
import pickle
import hashlib

try:
    from cachetools import TTLCache, cached
    _HAS_CACHETOOLS = True
except ImportError:
    _HAS_CACHETOOLS = False

try:
    import redis
    _REDIS_URL = os.environ.get("REDIS_URL")
    if _REDIS_URL:
        # decode_responses=False to keep bytes for pickle
        _redis = redis.from_url(_REDIS_URL, decode_responses=False)
        _HAS_REDIS = True
    else:
        _HAS_REDIS = False
except Exception:
    _HAS_REDIS = False


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
    """TTL-aware cache decorator. Uses Redis if available, else local cachetools."""
    if _HAS_REDIS:
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                key_tuple = _hashable_key(*args, **kwargs)
                key_str = f"{func.__module__}.{func.__name__}:" + hashlib.md5(pickle.dumps(key_tuple)).hexdigest()
                cached_val = _redis.get(key_str)
                if cached_val is not None:
                    try:
                        return pickle.loads(cached_val)
                    except pickle.PickleError:
                        pass
                
                result = func(*args, **kwargs)
                try:
                    # Cache None values for negative caching, but only briefly to avoid long-term poisoned cache 
                    # if the EE server has an intermittent outage.
                    store_ttl = ttl if result is not None else min(ttl, 60)
                    _redis.setex(key_str, store_ttl, pickle.dumps(result))
                except Exception:
                    pass
                return result
            return wrapper
        return decorator

    elif _HAS_CACHETOOLS:
        _cache = TTLCache(maxsize=512, ttl=ttl)

        def decorator(func):
            @cached(cache=_cache, key=_hashable_key)
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper
        return decorator
    else:
        # Fallback: dict-based cache with TTL tracking
        _store: dict = {}

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
        _store: dict = {}
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
