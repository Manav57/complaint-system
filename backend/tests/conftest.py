"""Pytest fixtures for the PharmaCare backend.

Environment is forced BEFORE any app module is imported so every test runs in:
  - MOCK LLM mode  (GROQ_API_KEY forced empty - no network, no real key used)
  - SQLite test DB (isolated temp file under backend/tests/)

The real key in backend/.env is never read by tests: pydantic-settings gives
environment variables priority over the .env file, and we set them here.
"""
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
TESTS_DIR = Path(__file__).resolve().parent

os.environ["GROQ_API_KEY"] = ""  # force the rule-based mock LLM
os.environ["DATABASE_URL"] = "sqlite:///" + str(TESTS_DIR / "test_complaints.db").replace("\\", "/")

sys.path.insert(0, str(BACKEND_DIR))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_db():
    yield
    engine.dispose()
    try:
        (TESTS_DIR / "test_complaints.db").unlink(missing_ok=True)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def fresh_db():
    """Recreate the schema before every test -> full per-test isolation."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
