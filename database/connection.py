"""Database connection management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

_engine = None
_SessionLocal = None


def get_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        db_url = os.getenv('DATABASE_URL', 'sqlite:///hydrorisk.db')
        # SQLite needs check_same_thread=False for Streamlit
        connect_args = {}
        if db_url.startswith('sqlite'):
            connect_args = {'check_same_thread': False}
        _engine = create_engine(db_url, connect_args=connect_args)
        Base.metadata.create_all(_engine)
    return _engine


def get_session():
    """Get a new database session."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()
