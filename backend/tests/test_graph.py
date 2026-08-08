"""Direct LangGraph workflow tests using the rule-based mock LLM.

Reuses the patterns from test_agent.py but asserts concrete deterministic
values from the mock, so the tests are stable offline.
"""
import pytest

import app.ai.graph as graph

CONTAMINATION_TEXT = (
    "Customer reports 6 tablets in batch PAR-2024-1187 have black specks on the "
    "surface and a strong burnt odor, suggesting contamination. Dispensed from "
    "a sealed blister pack."
)


# ---------------------------------------------------------------- extract graph
def test_extract_workflow_populates_fields():
    g = graph.build_extract_workflow()
    state = g.invoke({"raw_text": CONTAMINATION_TEXT, "description": CONTAMINATION_TEXT})
    fields = state["extracted_fields"]
    assert fields["batch_lot_number"] == "PAR-2024-1187"
    assert fields["category"] == "Contamination"
    assert "description" in fields  # always present
    assert state["result"]["fields"] == fields


def test_extract_workflow_empty_input():
    g = graph.build_extract_workflow()
    state = g.invoke({"raw_text": "", "description": ""})
    fields = state["extracted_fields"]
    assert fields["description"] == ""
    assert fields["severity"] == "Medium"  # mock default severity for unknown text


# ---------------------------------------------------------------- assess graph
def test_assess_workflow_runs_full_pipeline():
    g = graph.build_assess_workflow()
    state = g.invoke({"description": CONTAMINATION_TEXT, "raw_text": CONTAMINATION_TEXT})
    result = state["result"]
    assert result["risk_level"] == "High"
    assert result["risk_score"] == 0.85
    assert "contamination" in result["rationale"].lower()
    assert isinstance(result["category"], str) and result["category"]
    assert result["completeness"].get("complete") is True
    assert result["summary"].startswith("Customer reports")  # "Summary: " prefix cleaned
    assert "deviation" in result["root_cause_suggestion"].lower()
    assert "investigation" in result["capa_recommendation"].lower()


def test_assess_workflow_critical_risk():
    g = graph.build_assess_workflow()
    state = g.invoke(
        {
            "description": (
                "Patient had a serious adverse event: severe rash and face swelling, "
                "visited the emergency room."
            ),
            "raw_text": "ignored",
        }
    )
    assert state["result"]["risk_level"] == "Critical"


# ---------------------------------------------------------------- summary prefix cleaning
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Complaint Summary:** Customer reports black specks.", "Customer reports black specks."),
        ("Complaint Summary: Customer reports black specks.", "Customer reports black specks."),
        ("Here's a concise summary: Customer reports black specks.", "Customer reports black specks."),
        ("**Summary:** Customer reports black specks.", "Customer reports black specks."),
        ("Summary: Customer reports black specks.", "Customer reports black specks."),
        ("Executive Summary: Customer reports black specks.", "Customer reports black specks."),
        ("Customer reports black specks.", "Customer reports black specks."),  # no prefix -> unchanged
    ],
)
def test_assess_summary_node_strips_prefixes(monkeypatch, raw, expected):
    monkeypatch.setattr(graph, "llm_call", lambda *a, **k: raw)
    state = graph._assess_summary_node({"description": "ignored"})
    assert state["summary"] == expected


def test_assess_summary_node_strips_leading_quotes(monkeypatch):
    monkeypatch.setattr(graph, "llm_call", lambda *a, **k: '"Customer reports black specks."')
    state = graph._assess_summary_node({"description": "ignored"})
    assert state["summary"] == 'Customer reports black specks."'


def test_assess_summary_node_cleans_whitespace(monkeypatch):
    monkeypatch.setattr(graph, "llm_call", lambda *a, **k: "   \n  Complaint Summary:**   spaced out text.  ")
    state = graph._assess_summary_node({"description": "ignored"})
    assert state["summary"] == "spaced out text."


# ---------------------------------------------------------------- workflow singletons
def test_workflow_singletons():
    assert graph.get_extract_workflow() is graph.get_extract_workflow()
    assert graph.get_assess_workflow() is graph.get_assess_workflow()


# ---------------------------------------------------------------- duplicate detection
def test_find_duplicates_identical_description():
    rows = [
        {"id": "a1", "complaint_number": "CMP-A-1",
         "description": "Customer reports black specks on tablets.", "batch_lot_number": "PAR-1"}
    ]
    out = graph.find_duplicates("Customer reports black specks on tablets.", "PAR-1", rows)
    assert len(out) == 1
    assert out[0]["complaint_id"] == "a1"
    assert out[0]["score"] == 1.0
    assert "CMP-A-1" in out[0]["reason"]


def test_find_duplicates_batch_match_floor():
    rows = [
        {"id": "a1", "complaint_number": "CMP-A-1",
         "description": "Totally unrelated complaint about shipping delays.", "batch_lot_number": "PAR-1"}
    ]
    out = graph.find_duplicates("Customer reports black specks on tablets.", "PAR-1", rows)
    assert len(out) == 1
    assert out[0]["score"] == 0.75  # batch match floor


def test_find_duplicates_below_threshold():
    rows = [
        {"id": "a1", "complaint_number": "CMP-A-1",
         "description": "Totally unrelated complaint about shipping delays.", "batch_lot_number": "PAR-1"}
    ]
    assert graph.find_duplicates("Customer reports black specks on tablets.", None, rows) == []


def test_find_duplicates_handles_empty_inputs():
    assert graph.find_duplicates("", None, []) == []
    assert graph.find_duplicates("Some text", None, []) == []
    rows = [{"id": "a1", "complaint_number": "CMP-A-1", "description": "", "batch_lot_number": None}]
    assert graph.find_duplicates("Some text", None, rows) == []


def test_find_duplicates_returns_top_three():
    rows = [
        {"id": f"c{i}", "complaint_number": f"CMP-{i}", "description": f"Black specks on tablets batch {i}.", "batch_lot_number": None}
        for i in range(6)
    ]
    out = graph.find_duplicates("Black specks on tablets.", None, rows)
    assert len(out) == 3
    assert out[0]["score"] >= out[1]["score"] >= out[2]["score"]
