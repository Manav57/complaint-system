"""Tests for the Groq client wrapper: mock-mode behavior + JSON parsing.

These tests MUST run without GROQ_API_KEY (conftest forces it empty), so the
deterministic rule-based mock is exercised and no network call can happen.
"""
import json

import pytest

from app.ai.llm import extract_json, llm_call
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
