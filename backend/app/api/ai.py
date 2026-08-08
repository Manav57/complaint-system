"""AI endpoints wired to the LangGraph workflows (form autofill + copilot assessment)."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.ai.graph import (
    build_amend_workflow,
    build_assess_workflow,
    build_extract_workflow,
    find_duplicates,
)
from app.ai.pdf import extract_pdf_text
from app.ai.session import (
    append_message,
    create_session,
    get_session,
    update_session_fields,
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
    SessionCreateResponse,
    SessionMessageResponse,
)

router = APIRouter(prefix="/api/ai", tags=["ai agent"])
logger = logging.getLogger("ai_api")

_MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB cap on PDF uploads

_FIELD_LABELS = {
    "complainant_name": "Complainant Name",
    "complainant_email": "Email",
    "complainant_phone": "Phone",
    "complainant_company": "Company",
    "product_name": "Product Name",
    "batch_lot_number": "Batch/Lot Number",
    "dosage_form": "Dosage Form",
    "strength": "Strength",
    "expiry_date": "Expiry Date",
    "category": "Category",
    "severity": "Severity",
    "quantity_affected": "Quantity Affected",
    "description": "Description",
}


def _field_label(key: str) -> str:
    return _FIELD_LABELS.get(key, key.replace("_", " ").title())


def _build_session_reply(changed: dict, *, first: bool) -> str:
    """Short natural-language reply for the chat bubble."""
    if first:
        if not changed:
            return (
                "Hmm, I couldn't extract any details from that message. Could you include "
                "the product, batch/lot number, and what the customer reported?"
            )
        names = ", ".join(_field_label(k) for k in changed)
        plural = "s" if len(changed) != 1 else ""
        return (
            f"Got it — I extracted {len(changed)} field{plural} ({names}) into the form. "
            "Send a follow-up to correct anything."
        )
    if not changed:
        return "Got it — no fields needed updating based on that message."
    bits = [f"{_field_label(k)} to {v}" for k, v in changed.items()]
    return "Got it, I've updated " + ", ".join(bits) + "."


@router.post("/extract", response_model=ExtractResponse)
def extract_fields(payload: ExtractRequest):
    """LangGraph workflow 1: auto-populate the complaint form from free text."""
    graph = build_extract_workflow()
    state = graph.invoke({"raw_text": payload.text, "description": payload.text})
    fields = state.get("extracted_fields", {}) or state.get("result", {}).get("fields", {})
    return ExtractResponse(fields=fields, raw_text=payload.text)


# --------------------------------------------------------------------------
# Conversational correction (in-memory sessions) + PDF upload
# --------------------------------------------------------------------------
@router.post("/session", response_model=SessionCreateResponse)
def create_ai_session():
    """Start a conversational intake session."""
    session = create_session()
    return SessionCreateResponse(
        session_id=session["session_id"],
        fields={},
        reply=(
            "Hi! I'm your intake assistant. Paste the customer's complaint message "
            "(or attach a PDF) and I'll extract the details into the form. "
            "You can follow up afterwards to correct anything."
        ),
    )


@router.post("/session/{session_id}/message", response_model=SessionMessageResponse)
async def send_session_message(session_id: str, request: Request):
    """Send a message to a session: ``{"text": ...}`` JSON body or a PDF file upload.

    First message -> LangGraph extract workflow (populates all fields).
    Follow-up    -> LangGraph amend workflow (changes ONLY the mentioned fields).
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    content_type = (request.headers.get("content-type") or "").lower()
    message: str | None = None

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        file = form.get("file")
        if file is not None:
            filename = (getattr(file, "filename", "") or "").lower()
            ctype = (getattr(file, "content_type", "") or "").lower()
            if filename and not filename.endswith(".pdf") and ctype and "pdf" not in ctype:
                raise HTTPException(status_code=400, detail="Only PDF attachments are supported.")
            content = await file.read(_MAX_PDF_BYTES + 1)
            if len(content) > _MAX_PDF_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"PDF is too large (max {_MAX_PDF_BYTES // (1024 * 1024)} MB).",
                )
            try:
                message = extract_pdf_text(content)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Could not read PDF: {e}") from e
        else:
            text_field = form.get("text")
            if text_field:
                message = str(text_field)
    else:
        try:
            body = await request.json()
        except Exception as e:
            raise HTTPException(status_code=400, detail="Provide a 'text' message or a PDF 'file'.") from e
        text = (body or {}).get("text")
        if text:
            message = str(text)

    if not message or not message.strip():
        raise HTTPException(status_code=400, detail="Provide a 'text' message or a PDF 'file'.")
    message = message.strip()

    current = dict(session["fields"])
    first = not current
    if first:
        graph = build_extract_workflow()
        state = graph.invoke({"raw_text": message, "description": message})
        changed = state.get("extracted_fields", {}) or state.get("result", {}).get("fields", {}) or {}
    else:
        graph = build_amend_workflow()
        state = graph.invoke({"extracted_fields": current, "raw_text": message, "description": message})
        changed = state.get("field_changes", {}) or state.get("result", {}).get("changes", {}) or {}

    session = update_session_fields(session_id, changed)
    reply = _build_session_reply(changed, first=first)
    append_message(session_id, "user", message)
    append_message(session_id, "assistant", reply)

    return SessionMessageResponse(
        session_id=session_id,
        fields=dict(session["fields"]),
        changed=changed,
        reply=reply,
    )


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
