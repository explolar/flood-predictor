"""Structured logging setup with optional Sentry integration."""

import logging
import os
import sys


def setup_logging(level=None):
    """Configure structured logging. Optionally sends errors to Sentry."""
    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(numeric_level)

    # Clear existing handlers
    root.handlers.clear()

    # Console handler with structured format
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Optional Sentry integration
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=sentry_dsn,
                traces_sample_rate=float(os.getenv("SENTRY_TRACES_RATE", "0.1")),
                environment=os.getenv("SENTRY_ENV", "production"),
            )
            logging.getLogger(__name__).info("Sentry initialized")
        except ImportError:
            logging.getLogger(__name__).warning("sentry-sdk not installed, skipping Sentry")

    # Suppress noisy third-party loggers
    for name in ("urllib3", "google.auth", "ee", "matplotlib"):
        logging.getLogger(name).setLevel(logging.WARNING)

    return root


def get_logger(name):
    """Get a named logger."""
    return logging.getLogger(name)
