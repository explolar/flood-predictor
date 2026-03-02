"""
Feature 23: Database ORM models.
Supports both SQLite (single-user) and PostgreSQL/PostGIS (multi-user).
"""

import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default='user')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    analyses = relationship('Analysis', back_populates='user')
    saved_aois = relationship('SavedAOI', back_populates='user')


class SavedAOI(Base):
    __tablename__ = 'saved_aois'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    name = Column(String(200), nullable=False)
    geojson = Column(Text, nullable=False)
    center_lat = Column(Float)
    center_lon = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship('User', back_populates='saved_aois')


class Analysis(Base):
    __tablename__ = 'analyses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    aoi_id = Column(Integer, ForeignKey('saved_aois.id'), nullable=True)
    analysis_type = Column(String(50), nullable=False)  # mca, sar, ml, drought
    parameters = Column(JSON)
    results_summary = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship('User', back_populates='analyses')
