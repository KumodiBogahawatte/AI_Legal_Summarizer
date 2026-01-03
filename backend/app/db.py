from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path
import os
from .config import DATABASE_URL, DATABASE_TYPE

# Create engine with appropriate settings for PostgreSQL or SQLite
if DATABASE_TYPE == "postgresql":
    engine = create_engine(
        DATABASE_URL,
        poolclass=pool.QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verify connections before using
        echo=False  # Set to True for SQL debugging
    )
else:  # SQLite
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    from app.models import (
        LegalDocument, 
        DetectedRight, 
        SLCitation, 
        RightsViolation, 
        UserPreference
    )
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database initialized using {DATABASE_TYPE.upper()}")