"""
Caching abstraction that works in both Streamlit and FastAPI contexts.
Use @cache_data(ttl=3600) instead of @st.cache_data(ttl=3600).
"""

import functools

try:
    import streamlit as st
    _HAS_STREAMLIT = True
except ImportError:
    _HAS_STREAMLIT = False


def cache_data(ttl=3600, show_spinner=False):
    """Drop-in replacement for @st.cache_data that falls back to lru_cache."""
    if _HAS_STREAMLIT:
        return st.cache_data(show_spinner=show_spinner, ttl=ttl)
    else:
        return functools.lru_cache(maxsize=128)


def cache_resource():
    """Drop-in replacement for @st.cache_resource."""
    if _HAS_STREAMLIT:
        return st.cache_resource
    else:
        return functools.lru_cache(maxsize=1)
