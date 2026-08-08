"""Configuration tests: settings load, CORS parsing, groq_configured flag.

Note: env vars are manipulated with monkeypatch so the real key in backend/.env
is never read (and never printed).
"""
import pytest

from app.config import Settings, get_settings


def test_settings_loads_defaults(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.delenv("DATABASE_URL", raising=False)  # conftest sets sqlite otherwise
    s = Settings()
    assert s.app_name == "AIVOA Pharma Complaint System"
    assert s.app_version == "1.0.0"
    assert s.groq_model == "llama-3.1-8b-instant"
    assert s.groq_heavy_model == "llama-3.3-70b-versatile"
    assert s.database_url.startswith("postgresql")


def test_cors_origin_list_parsing(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    s = Settings(cors_origins="http://localhost:3000,http://127.0.0.1:3000")
    assert s.cors_origin_list == ["http://localhost:3000", "http://127.0.0.1:3000"]


def test_cors_origin_list_drops_empty_segments():
    s = Settings(cors_origins="a, b,,c,   ")
    assert s.cors_origin_list == ["a", "b", "c"]


def test_groq_configured_false_when_key_empty(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    assert Settings().groq_configured is False


def test_groq_configured_true_when_key_set(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_dummy_not_a_real_key")
    s = Settings()
    assert s.groq_configured is True
    # sanity: the value round-trips (never printed/logged in tests)
    assert s.groq_api_key == "gsk_test_dummy_not_a_real_key"


def test_get_settings_is_cached():
    assert get_settings() is get_settings()


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Test App Name")
    monkeypatch.setenv("GROQ_API_KEY", "")
    assert Settings().app_name == "Test App Name"
