"""Tests for utility modules."""

import pytest


class TestLoggingConfig:
    def test_setup_logging(self):
        from utils.logging_config import setup_logging
        root = setup_logging(level="DEBUG")
        assert root is not None
        assert root.level == 10  # DEBUG

    def test_get_logger(self):
        from utils.logging_config import get_logger
        logger = get_logger("test.module")
        assert logger.name == "test.module"

    def test_setup_logging_default_level(self):
        from utils.logging_config import setup_logging
        root = setup_logging()
        assert root.level == 20  # INFO


class TestCacheModule:
    def test_cache_data_returns_decorator(self):
        from utils.cache import cache_data
        decorator = cache_data(ttl=600)
        assert callable(decorator)

    def test_cache_resource_returns_decorator(self):
        from utils.cache import cache_resource
        decorator = cache_resource()
        assert callable(decorator)
