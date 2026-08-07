"""AI endpoints wired to the LangGraph workflows (form autofill + copilot assessment)."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.graph import (
    build_assess_workflow,
    build_extract_workflow,
    find_duplicates,
)
from app.crud import get_complaint, list_for_duplicate_check
from app.database import get_db
from app.schemas.complaint import (
    AIAnalysisResponse,
    CompletenessReport,
    DuplicateMatch,
    ExtractRequest,
    ExtractResponse,
    RiskAssessmentRequest,
    RiskAssessmentResponse,
)

router = APIRouter(prefix="/api/ai", tags=["ai agent"])
logger = logging.getLogger("ai_api")


@router.post("/extract", response_model=ExtractResponse)
def extract_fields(payload: ExtractRequest):
    """LangGraph workflow 1: auto-populate the complaint form from free text."""
    graph = build_extract_workflow()
    state = graph.invoke({"raw_text": payload.text, "description": payload.text})
    fields = state.get("extracted_fields", {}) or state.get("result", {}).get("fields", {})
    return ExtractResponse(fields=fields, raw_text=payload.text)


@router.post("/assess", response_model=RiskAssessmentResponse)
def assess_risk(payload: RiskAssessmentRequest, db: Session = Depends(get_db)):
    """LangGraph workflow 2: Copilot risk assessment (risk + completeness +
    summary + root cause + CAPA + duplicate check in one graph run)."""
    graph = build_assess_workflow()
    state = graph.invoke(
        {
            "description": payload.description,
            "category": payload.category,
            "product_name": payload.product_name,
            "batch_lot_number": payload.batch_lot_number,
            "severity": payload.severity,
            "raw_text": payload.description,
        }
    )
    result = state.get("result", {})

    # Duplicate detection against stored complaints (deterministic stage)
    duplicates = find_duplicates(
        payload.description,
        payload.batch_lot_number,
        list_for_duplicate_check(db),
    )
    top = duplicates[0] if duplicates else None

    return RiskAssessmentResponse(
        risk_level=result.get("risk_level", "Low"),
        risk_score=result.get("risk_score", 0.2),
        rationale=result.get("rationale", ""),
        category=result.get("category"),
        severity=result.get("severity"),
        duplicate_of=top["complaint_id"] if top else None,
        duplicate_score=top["score"] if top else None,
        summary=result.get("summary"),
        root_cause_suggestion=result.get("root_cause_suggestion"),
        capa_recommendation=result.get("capa_recommendation"),
    )


@router.post("/completeness", response_model=CompletenessReport)
def check_completeness(payload: ExtractRequest):
    """Completeness checker: flags missing required fields before submit."""
    text = payload.text.lower()
    missing: list[str] = []
    required = [
        ("complainant_name", ["name", "i am", "customer"]),
        ("description", ["problem", "issue", "complaint"]),
    ]
    for field, hints in required:
        if not any(h in text for h in hints):
            missing.append(field)
    optional = [
        ("batch_lot_number", ["batch", "lot"]),
        ("product_name", ["product", "tablet", "capsule", "syrup", "mg"]),
    ]
    for field, hints in optional:
        if not any(h in text for h in hints):
            missing.append(field)
    return CompletenessReport(
        complete=not missing,
        missing_fields=missing,
        message="All required fields present." if not missing else f"Missing fields: {', '.join(missing)}",
    )


@router.get("/duplicates/{complaint_id}", response_model=list[DuplicateMatch])
def find_duplicate_complaints(complaint_id: str, db: Session = Depends(get_db)):
    """Duplicate complaint detection for an existing complaint."""
    complaint = get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    others = [r for r in list_for_duplicate_check(db) if r["id"] != complaint_id]
    return find_duplicates(complaint.description, complaint.batch_lot_number, others)


@router.post("/analyze", response_model=AIAnalysisResponse)
def analyze_existing(complaint_id: str, db: Session = Depends(get_db)):
    """Full AI analysis of an existing complaint, persisted to the record."""
    complaint = get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    graph = build_assess_workflow()
    state = graph.invoke(
        {
            "description": complaint.description,
            "category": complaint.category,
            "product_name": complaint.product_name,
            "batch_lot_number": complaint.batch_lot_number,
            "severity": complaint.severity,
            "raw_text": complaint.description,
        }
    )
    result = state.get("result", {})
    duplicates = find_duplicates(
        complaint.description,
        complaint.batch_lot_number,
        [r for r in list_for_duplicate_check(db) if r["id"] != complaint_id],
    )
    top = duplicates[0] if duplicates else None

    complaint.risk_level = result.get("risk_level")
    complaint.risk_score = result.get("risk_score")
    complaint.risk_rationale = result.get("rationale")
    complaint.ai_summary = result.get("summary")
    complaint.root_cause_suggestion = result.get("root_cause_suggestion")
    complaint.capa_recommendation = result.get("capa_recommendation")
    if top:
        complaint.duplicate_of = top["complaint_id"]
        complaint.duplicate_score = top["score"]
    db.commit()
    db.refresh(complaint)

    return AIAnalysisResponse(
        complaint_id=complaint.id,
        complaint_number=complaint.complaint_number,
        risk_level=complaint.risk_level or "Low",
        risk_score=complaint.risk_score or 0.2,
        rationale=complaint.risk_rationale or "",
        category=complaint.category,
        severity=complaint.severity,
        summary=complaint.ai_summary,
        root_cause_suggestion=complaint.root_cause_suggestion,
        capa_recommendation=complaint.capa_recommendation,
        duplicate_of=complaint.duplicate_of,
        duplicate_score=complaint.duplicate_score,
    )
