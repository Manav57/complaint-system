"""Complaint and status history models for pharma complaint management."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class ComplaintCategory(str, enum.Enum):
    PRODUCT_QUALITY = "Product Quality"
    PACKAGING = "Packaging"
    LABELING = "Labeling"
    ADVERSE_EVENT = "Adverse Event"
    CONTAMINATION = "Contamination"
    POTENCY = "Potency"
    STABILITY = "Stability"
    DISSOLUTION = "Dissolution"
    DELIVERY = "Delivery / Logistics"
    SERVICE = "Service"
    OTHER = "Other"


class ComplaintStatus(str, enum.Enum):
    NEW = "New"
    UNDER_REVIEW = "Under Review"
    INVESTIGATING = "Investigating"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class RiskLevel(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    complaint_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)

    # Complainant
    complainant_name: Mapped[str] = mapped_column(String(200))
    complainant_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    complainant_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    complainant_company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    complainant_address: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Product
    product_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    product_ndc: Mapped[str | None] = mapped_column(String(100), nullable=True)
    batch_lot_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    manufacturing_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    expiry_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    dosage_form: Mapped[str | None] = mapped_column(String(100), nullable=True)
    strength: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Complaint details
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    complaint_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    quantity_affected: Mapped[str | None] = mapped_column(String(100), nullable=True)
    submitted_via: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(40), default=ComplaintStatus.NEW.value)
    assigned_to: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI analysis results
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_categories: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_extracted_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    duplicate_of: Mapped[str | None] = mapped_column(String(36), nullable=True)
    duplicate_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    root_cause_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    capa_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    status_history: Mapped[list["StatusHistory"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan", order_by="StatusHistory.changed_at"
    )


class StatusHistory(Base):
    __tablename__ = "status_history"
    __table_args__ = (UniqueConstraint("complaint_id", "changed_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40))
    changed_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    complaint: Mapped["Complaint"] = relationship(back_populates="status_history")
