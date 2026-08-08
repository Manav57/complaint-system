"""Tests for the Groq client wrapper: mock-mode behavior + JSON parsing.

These tests MUST run without GROQ_API_KEY (conftest forces it empty), so the
deterministic rule-based mock is exercised and no network call can happen.
"""
import json

import pytest

from app.ai.llm import (
    _is_model_rejection,
    _MODEL_FALLBACKS,
    extract_json,
    llm_call,
)
from app.ai.graph import EXTRACT_SYSTEM, RISK_SYSTEM, SUMMARY_SYSTEM
from app.config import get_settings


def test_mock_mode_is_active():
    assert get_settings().groq_configured is False


def test_llm_call_returns_mock_risk_json():
    out = llm_call(RISK_SYSTEM, "Patient had an adverse event and visited the emergency room.")
    data = json.loads(out)
    assert data["mock"] is True
    assert data["risk_level"] == "Critical"
    assert data["risk_score"] == 0.95


def test_llm_call_returns_mock_extract_json():
    text = (
        "I'm Dr. Jane Wilson from Lakeside Pharmacy. Paracetamol 500mg tablets "
        "batch PAR-2025-2210 with black specks, expiry 09/30/2027. "
        "jane.wilson@lakesidepharmacy.com"
    )
    out = llm_call(EXTRACT_SYSTEM, text)
    data = json.loads(out)
    assert data["product_name"] == "Paracetamol"
    assert data["batch_lot_number"] == "PAR-2025-2210"
    assert data["complainant_email"] == "jane.wilson@lakesidepharmacy.com"
    assert "Jane Wilson" in data["complainant_name"]
    assert data["strength"] == "500mg"
    assert data["expiry_date"] == "09/30/2027"


def test_llm_call_returns_mock_summary():
    out = llm_call(SUMMARY_SYSTEM, "Customer reports black specks on tablets.")
    assert out.startswith("Summary: Customer reports")
    assert "MOCK generated summary" in out


def test_llm_call_dispatch_mismatch_returns_marker():
    out = llm_call("Some unrelated system prompt", "Some user text")
    assert out == "MOCK: no handler matched."


# ---------------------------------------------------------------- model fallback
def test_is_model_rejection_detects_decommissioned_and_unknown_models():
    assert _is_model_rejection(Exception("The model `gemma2-9b-it` has been decommissioned and is no longer supported."))
    assert _is_model_rejection(Exception("The model `gemma-2-9b-it` does not exist or you do not have access to it."))
    assert _is_model_rejection(Exception("model_not_found"))
    assert not _is_model_rejection(Exception("rate limit exceeded"))
    assert not _is_model_rejection(Exception("connection refused"))


def test_model_fallbacks_map_spec_default_to_supported_model():
    assert _MODEL_FALLBACKS["gemma2-9b-it"] == "llama-3.1-8b-instant"


def test_llm_call_retries_with_fallback_model_on_rejection(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        "app.ai.llm.settings",
        SimpleNamespace(
            groq_configured=True,
            groq_api_key="gsk_test_dummy",
            groq_model="gemma2-9b-it",
            groq_heavy_model="llama-3.3-70b-versatile",
        ),
    )
    calls: list[str] = []

    def fake_load(model: str):
        calls.append(model)
        if model == "gemma2-9b-it":
            raise RuntimeError(
                "Error code: 400 - {'error': {'message': 'The model `gemma2-9b-it` has "
                "been decommissioned and is no longer supported.'}}"
            )

        class _Msg:
            content = '{"mock": false, "ok": true}'

        class _Client:
            def invoke(self, messages):
                return _Msg()

        return _Client()

    monkeypatch.setattr("app.ai.llm._load_client", fake_load)
    out = llm_call("extract structured fields", "some text")
    assert calls == ["gemma2-9b-it", "llama-3.1-8b-instant"]
    assert out == '{"mock": false, "ok": true}'


def test_llm_call_mocks_when_every_model_rejected(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        "app.ai.llm.settings",
        SimpleNamespace(
            groq_configured=True,
            groq_api_key="gsk_test_dummy",
            groq_model="gemma2-9b-it",
            groq_heavy_model="llama-3.3-70b-versatile",
        ),
    )

    def fake_load(model: str):
        raise RuntimeError(f"model `{model}` decommissioned")

    monkeypatch.setattr("app.ai.llm._load_client", fake_load)
    out = llm_call(RISK_SYSTEM, "Patient had an adverse event and visited the emergency room.")
    data = json.loads(out)
    assert data["mock"] is True
    assert data["risk_level"] == "Critical"


# ---------------------------------------------------------------- extract_json
def test_extract_json_plain_dict():
    assert extract_json('{"a": 1, "b": "x"}') == {"a": 1, "b": "x"}


def test_extract_json_markdown_fenced():
    raw = '```json\n{"risk_level": "High", "risk_score": 0.85}\n```'
    assert extract_json(raw) == {"risk_level": "High", "risk_score": 0.85}


def test_extract_json_embedded_in_prose():
    raw = 'Sure! Here is the analysis: {"risk_level": "Low", "risk_score": 0.2} hope that helps.'
    assert extract_json(raw) == {"risk_level": "Low", "risk_score": 0.2}


def test_extract_json_garbage_returns_none():
    assert extract_json("this is not json at all") is None
    assert extract_json("") is None


def test_extract_json_none_input():
    assert extract_json(None) is None


def test_extract_json_non_dict_json_returns_none():
    assert extract_json("[1, 2, 3]") is None
    assert extract_json('"just a string"') is None
