"""Database engine, session and base.

Connection strategy:
  1. If DATABASE_URL is set to a real Postgres/MySQL URL, connect to it.
  2. If the initial connection fails at startup, log a clear warning and
     fall back to a local SQLite file (complaints.db) so the app still boots.
  3. If no DATABASE_URL is configured, use SQLite directly.
"""
import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

logger = logging.getLogger("database")

settings = get_settings()

_FALLBACK_SQLITE_URL = "sqlite:///./complaints.db"


def _make_engine(url: str):
    if url.startswith("sqlite"):
        eng = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(eng, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):  # pragma: no cover
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return eng
    return create_engine(url, pool_pre_ping=True, echo=False)


def _resolve_engine():
    configured = settings.database_url.strip() if settings.database_url else ""
    if not configured:
        logger.warning(
            "DATABASE_URL not set - falling back to local SQLite at %s", _FALLBACK_SQLITE_URL
        )
        return _make_engine(_FALLBACK_SQLITE_URL)

    engine = _make_engine(configured)
    try:
        with engine.connect():
            logger.info("Connected to configured database: %s", _redact(configured))
        return engine
    except Exception as e:
        logger.warning(
            "Configured database unreachable (%s) - falling back to local SQLite at %s. "
            "Error: %s",
            _redact(configured),
            _FALLBACK_SQLITE_URL,
            e,
        )
        return _make_engine(_FALLBACK_SQLITE_URL)


def _redact(url: str) -> str:
    """Hide credentials when logging a database URL."""
    try:
        from urllib.parse import urlsplit, urlunsplit

        parts = urlsplit(url)
        if parts.netloc and "@" in parts.netloc:
            return urlunsplit((parts.scheme, parts.netloc.split("@")[-1], parts.path, parts.query, parts.fragment))
    except Exception:
        pass
    return url


engine = _resolve_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
