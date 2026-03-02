"""CRUD operations for the database."""

import json
from .connection import get_session
from .models import Analysis, User, SavedAOI


def save_analysis(analysis_type, parameters, results_summary, user_id=None, aoi_id=None):
    """Save an analysis result to the database."""
    session = get_session()
    try:
        analysis = Analysis(
            user_id=user_id,
            aoi_id=aoi_id,
            analysis_type=analysis_type,
            parameters=parameters,
            results_summary=results_summary,
        )
        session.add(analysis)
        session.commit()
        return analysis.id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_recent_analyses(limit=20, user_id=None):
    """Get recent analyses, optionally filtered by user."""
    session = get_session()
    try:
        query = session.query(Analysis).order_by(Analysis.created_at.desc())
        if user_id:
            query = query.filter(Analysis.user_id == user_id)
        return query.limit(limit).all()
    finally:
        session.close()


def save_aoi(name, geojson, center_lat, center_lon, user_id=None):
    """Save an AOI for later reuse."""
    session = get_session()
    try:
        aoi = SavedAOI(
            user_id=user_id,
            name=name,
            geojson=geojson if isinstance(geojson, str) else json.dumps(geojson),
            center_lat=center_lat,
            center_lon=center_lon,
        )
        session.add(aoi)
        session.commit()
        return aoi.id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_saved_aois(user_id=None):
    """Get saved AOIs, optionally filtered by user."""
    session = get_session()
    try:
        query = session.query(SavedAOI).order_by(SavedAOI.created_at.desc())
        if user_id:
            query = query.filter(SavedAOI.user_id == user_id)
        return query.all()
    finally:
        session.close()


def create_user(username, email, password_hash, role='user'):
    """Create a new user."""
    session = get_session()
    try:
        user = User(username=username, email=email, password_hash=password_hash, role=role)
        session.add(user)
        session.commit()
        return user.id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_user_by_username(username):
    """Get user by username."""
    session = get_session()
    try:
        return session.query(User).filter(User.username == username).first()
    finally:
        session.close()
