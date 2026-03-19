"""
Caching abstraction using functools.
Use @cache_data(ttl=3600) as a decorator for expensive computations.
"""

import functools


def cache_data(ttl=3600, show_spinner=False):
    """LRU-cache decorator. ttl and show_spinner kept for API compat."""
    return functools.lru_cache(maxsize=128)


def cache_resource():
    """Singleton-cache decorator for expensive resources."""
    return functools.lru_cache(maxsize=1)
