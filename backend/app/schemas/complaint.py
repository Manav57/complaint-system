"""Pydantic schemas for complaints and AI features."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------- Complaint CRUD ----------
class ComplaintBase(BaseModel):
    complainant_name: str = Field(..., min_length=1, max_length=200)
    complainant_email: str | None = None
    complainant_phone: str | None = None
    complainant_company: str | None = None
    complainant_address: str | None = None

    product_name: str | None = None
    product_ndc: str | None = None
    batch_lot_number: str | None = None
    manufacturing_date: str | None = None
    expiry_date: str | None = None
    dosage_form: str | None = None
    strength: str | None = None

    category: str | None = None
    severity: str | None = None
    description: str = Field(..., min_length=1)
    complaint_date: str | None = None
    quantity_affected: str | None = None
    submitted_via: str | None = None


class ComplaintCreate(ComplaintBase):
    pass


class ComplaintUpdate(BaseModel):
    status: str | None = None
    assigned_to: str | None = None
    notes: str | None = None
    root_cause: str | None = None
    severity: str | None = None
    category: str | None = None
    batch_lot_number: str | None = None
    complainant_email: str | None = None
    complainant_phone: str | None = None
    complainant_company: str | None = None


class StatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_status: str | None
    to_status: str
    changed_by: str | None
    note: str | None
    changed_at: datetime


class ComplaintDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    complaint_number: str
    complainant_name: str
    complainant_email: str | None
    complainant_phone: str | None
    complainant_company: str | None
    complainant_address: str | None
    product_name: str | None
    product_ndc: str | None
    batch_lot_number: str | None
    manufacturing_date: str | None
    expiry_date: str | None
    dosage_form: str | None
    strength: str | None
    category: str | None
    severity: str | None
    description: str
    complaint_date: str | None
    quantity_affected: str | None
    submitted_via: str | None
    status: str
    assigned_to: str | None
    notes: str | None
    root_cause: str | None
    risk_level: str | None
    risk_score: float | None
    risk_rationale: str | None
    ai_summary: str | None
    ai_categories: list[Any] | None
    ai_extracted_fields: dict[str, Any] | None
    duplicate_of: str | None
    duplicate_score: float | None
    root_cause_suggestion: str | None
    capa_recommendation: str | None
    created_at: datetime
    updated_at: datetime
    status_history: list[StatusHistoryOut] = []


class ComplaintList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    complaint_number: str
    complainant_name: str
    product_name: str | None
    batch_lot_number: str | None
    category: str | None
    severity: str | None
    description: str
    status: str
    risk_level: str | None
    complaint_date: str | None
    created_at: datetime
    updated_at: datetime


# ---------- AI features ----------
class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=3)


class ExtractResponse(BaseModel):
    fields: dict[str, Any]
    raw_text: str


class RiskAssessmentRequest(BaseModel):
    description: str = Field(..., min_length=3)
    category: str | None = None
    product_name: str | None = None
    batch_lot_number: str | None = None
    severity: str | None = None


class RiskAssessmentResponse(BaseModel):
    risk_level: str
    risk_score: float
    rationale: str
    category: str | None
    severity: str | None
    duplicate_of: str | None
    duplicate_score: float | None
    summary: str | None
    root_cause_suggestion: str | None
    capa_recommendation: str | None


class CompletenessReport(BaseModel):
    complete: bool
    missing_fields: list[str]
    message: str


class DuplicateMatch(BaseModel):
    complaint_id: str
    complaint_number: str
    score: float
    reason: str


class AIAnalysisResponse(BaseModel):
    complaint_id: str
    complaint_number: str
    risk_level: str
    risk_score: float
    rationale: str
    category: str | None
    severity: str | None
    summary: str | None
    root_cause_suggestion: str | None
    capa_recommendation: str | None
    duplicate_of: str | None
    duplicate_score: float | None
