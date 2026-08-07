"""LangGraph agent workflow for complaint processing.

Two workflows wired to Groq:
  1. extract_workflow  - auto-populates the complaint form from free text
  2. assess_workflow   - Copilot risk assessment (+ completeness, summary,
                         duplicates, root cause, CAPA in one graph)

Built with langgraph StateGraph so the traversal is visible in /docs and
traceable in the UI copilot panel.
"""
import logging
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.ai.llm import extract_json, llm_call

logger = logging.getLogger("agent")

EXTRACT_SYSTEM = (
    "You are an AI intake assistant for a pharmaceutical manufacturing company. "
    "Extract structured complaint data from the customer's free-text message. "
    "Return STRICT JSON (no markdown, no commentary) with any of these keys that "
    "you can determine: complainant_name, complainant_email, complainant_phone, "
    "complainant_company, product_name, batch_lot_number, dosage_form, strength, "
    "expiry_date, category, severity, quantity_affected. Use empty strings for "
    "unknown fields. Category must be one of: Product Quality, Packaging, "
    "Labeling, Adverse Event, Contamination, Potency, Stability, Dissolution, "
    "Delivery / Logistics, Service, Other."
)

RISK_SYSTEM = (
    "You are a senior pharmaceutical QA risk assessor. Classify the risk of the "
    "given customer complaint per GMP / pharmacovigilance principles. Return "
    "STRICT JSON only with keys: risk_level (one of Low, Medium, High, Critical), "
    "risk_score (0.0-1.0), rationale (2-4 sentences), category, severity."
)

COMPLETENESS_SYSTEM = (
    "You are a pharma complaint intake quality checker. Review the complaint "
    "draft and return STRICT JSON only: {\"complete\": bool, \"missing_fields\": [\"field_name\", ...]}."
)

SUMMARY_SYSTEM = (
    "You are a pharma complaint analyst. Write a concise 2-3 sentence executive "
    "summary of the complaint for a QA supervisor."
)

ROOTCAUSE_SYSTEM = (
    "You are a pharmaceutical quality investigator. Based on the complaint, "
    "suggest likely root causes and a CAPA (Corrective and Preventive Action) "
    "plan. Return STRICT JSON only with keys root_cause and capa."
)


class ComplaintState(TypedDict, total=False):
    description: str
    category: str | None
    product_name: str | None
    batch_lot_number: str | None
    severity: str | None
    raw_text: str
    extracted_fields: dict[str, Any]
    completeness: dict[str, Any]
    risk: dict[str, Any]
    summary: str
    root_cause: dict[str, Any]
    result: dict[str, Any]


# --------------------------------------------------------------------------
# Workflow 1: form auto-population (extraction)
# --------------------------------------------------------------------------
def _extract_node(state: ComplaintState) -> dict:
    raw = state.get("raw_text") or state.get("description") or ""
    response = llm_call(EXTRACT_SYSTEM, raw)
    data = extract_json(response) or {}
    fields = {k: ("" if v is None else v) for k, v in data.items() if k != "extracted"}
    if not fields.get("description"):
        fields["description"] = raw
    return {"extracted_fields": fields}


def _extract_final(state: ComplaintState) -> dict:
    return {"result": {"fields": state.get("extracted_fields", {}), "raw_text": state.get("raw_text", "")}}


def build_extract_workflow():
    g = StateGraph(ComplaintState)
    g.add_node("extract", _extract_node)
    g.add_node("finalize", _extract_final)
    g.add_edge(START, "extract")
    g.add_edge("extract", "finalize")
    g.add_edge("finalize", END)
    return g.compile()


# --------------------------------------------------------------------------
# Workflow 2: Copilot risk assessment (risk + completeness + summary +
#              root cause + CAPA in a single graph run)
# --------------------------------------------------------------------------
def _assess_risk_node(state: ComplaintState) -> dict:
    desc = state.get("description", "")
    prompt = (
        f"Complaint description: {desc}\n"
        f"Category: {state.get('category') or 'unknown'}\n"
        f"Product: {state.get('product_name') or 'unknown'}\n"
        f"Batch/Lot: {state.get('batch_lot_number') or 'unknown'}\n"
        f"Severity: {state.get('severity') or 'unknown'}"
    )
    response = llm_call(RISK_SYSTEM, prompt, heavy=True)
    data = extract_json(response) or {}
    risk = {
        "risk_level": data.get("risk_level") or "Low",
        "risk_score": float(data.get("risk_score") or 0.2),
        "rationale": data.get("rationale") or "No rationale provided.",
        "category": data.get("category"),
        "severity": data.get("severity"),
    }
    return {"risk": risk}


def _assess_completeness_node(state: ComplaintState) -> dict:
    draft = (
        f"complainant_name: {state.get('extracted_fields', {}).get('complainant_name') or ''}\n"
        f"product_name: {state.get('extracted_fields', {}).get('product_name') or ''}\n"
        f"batch_lot_number: {state.get('extracted_fields', {}).get('batch_lot_number') or ''}\n"
        f"category: {state.get('category') or state.get('extracted_fields', {}).get('category') or ''}\n"
        f"description: {state.get('description') or ''}"
    )
    response = llm_call(COMPLETENESS_SYSTEM, draft)
    data = extract_json(response) or {}
    return {"completeness": data or {"complete": True, "missing_fields": []}}


def _assess_summary_node(state: ComplaintState) -> dict:
    desc = state.get("description", "")[:2000]
    response = llm_call(SUMMARY_SYSTEM, desc)
    return {"summary": response.strip()}


def _assess_rootcause_node(state: ComplaintState) -> dict:
    desc = state.get("description", "")
    response = llm_call(ROOTCAUSE_SYSTEM, desc, heavy=True)
    data = extract_json(response) or {}
    return {"root_cause": data}


def _assess_final(state: ComplaintState) -> dict:
    risk = state.get("risk", {})
    dup = state.get("duplicate", {})
    return {
        "result": {
            "risk_level": risk.get("risk_level", "Low"),
            "risk_score": risk.get("risk_score", 0.2),
            "rationale": risk.get("rationale", ""),
            "category": risk.get("category"),
            "severity": risk.get("severity"),
            "completeness": state.get("completeness", {}),
            "summary": state.get("summary", ""),
            "root_cause_suggestion": state.get("root_cause", {}).get("root_cause"),
            "capa_recommendation": state.get("root_cause", {}).get("capa"),
            "duplicate_of": dup.get("complaint_id"),
            "duplicate_score": dup.get("score"),
        }
    }


def build_assess_workflow():
    g = StateGraph(ComplaintState)
    g.add_node("assess_risk", _assess_risk_node)
    g.add_node("check_completeness", _assess_completeness_node)
    g.add_node("gen_summary", _assess_summary_node)
    g.add_node("gen_root_cause", _assess_rootcause_node)
    g.add_node("finalize", _assess_final)
    g.add_edge(START, "assess_risk")
    g.add_edge("assess_risk", "check_completeness")
    g.add_edge("check_completeness", "gen_summary")
    g.add_edge("gen_summary", "gen_root_cause")
    g.add_edge("gen_root_cause", "finalize")
    g.add_edge("finalize", END)
    return g.compile()


_extract_workflow = None
_assess_workflow = None


def get_extract_workflow():
    global _extract_workflow
    if _extract_workflow is None:
        _extract_workflow = build_extract_workflow()
    return _extract_workflow


def get_assess_workflow():
    global _assess_workflow
    if _assess_workflow is None:
        _assess_workflow = build_assess_workflow()
    return _assess_workflow


# --------------------------------------------------------------------------
# Duplicate detection (deterministic TF-scoring against existing complaints)
# --------------------------------------------------------------------------
def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def find_duplicates(description: str, batch_lot: str | None, existing: list[dict]) -> list[dict]:
    """Score similarity against existing complaints. Returns top matches > 0.4."""
    desc_tokens = _tokenize(description)
    matches: list[dict] = []
    for row in existing:
        other_tokens = _tokenize(row.get("description") or "")
        if not desc_tokens or not other_tokens:
            continue
        inter = len(desc_tokens & other_tokens)
        union = len(desc_tokens | other_tokens)
        sim = inter / union if union else 0.0
        if batch_lot and row.get("batch_lot_number") and batch_lot.strip().upper() == row.get("batch_lot_number", "").strip().upper():
            sim = max(sim, 0.75)
        if sim >= 0.4:
            matches.append({
                "complaint_id": row["id"],
                "complaint_number": row.get("complaint_number", ""),
                "score": round(sim, 2),
                "reason": f"Description shares {round(sim * 100):.0f}% similarity with complaint {row.get('complaint_number', row['id'])}.",
            })
    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches[:3]
