import time
import sqlite3
from functools import wraps
from sqlalchemy import create_engine, pool, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path
import os
from .config import DATABASE_URL, DATABASE_TYPE

# ── Engine ────────────────────────────────────────────────────────────────────
if DATABASE_TYPE == "postgresql":
    engine = create_engine(
        DATABASE_URL,
        poolclass=pool.QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,
    )
else:  # SQLite
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 60,          # Python-level wait up to 60s
        },
        echo=False,
        pool_pre_ping=True,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_wal(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA journal_mode=WAL")
        dbapi_connection.execute("PRAGMA synchronous=NORMAL")
        dbapi_connection.execute("PRAGMA busy_timeout=60000")   # 60s SQLite-level

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── Retry helper ──────────────────────────────────────────────────────────────
class RetrySession:
    """Thin wrapper around a SQLAlchemy session that retries commits on SQLite lock."""

    _MAX_RETRIES = 6
    _RETRY_DELAY = 2.0   # seconds between attempts

    def __init__(self, session):
        self._session = session

    def commit(self):
        for attempt in range(1, self._MAX_RETRIES + 1):
            try:
                self._session.commit()
                return
            except Exception as exc:
                if "database is locked" in str(exc).lower() and attempt < self._MAX_RETRIES:
                    print(f"⚠️  DB locked (attempt {attempt}/{self._MAX_RETRIES}), retrying in {self._RETRY_DELAY}s…")
                    self._session.rollback()
                    time.sleep(self._RETRY_DELAY)
                else:
                    raise

    def __getattr__(self, name):
        return getattr(self._session, name)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._session.close()


def get_db():
    """FastAPI dependency — yields a RetrySession that auto-retries on SQLite lock."""
    raw = SessionLocal()
    db = RetrySession(raw)
    try:
        yield db
    finally:
        raw.close()


def init_db():
    """Initialize database tables. Imports all models so every table is created."""
    from app.models import (
        LegalDocument,
        UserPreference,
        DetectedRight,
        SLCitation,
        RightsViolation,
        UserAccount,
        Bookmark,
        SearchHistory,
        ProcessingLog,
        CaseSimilarity,
        DocumentVersion,
        AuditLog,
        LegalEntity,
        DocumentChunk,
        RAGJob,
    )
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database initialized using {DATABASE_TYPE.upper()}")
