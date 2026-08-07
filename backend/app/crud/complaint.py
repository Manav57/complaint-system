"""CRUD operations for complaints."""
import logging
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint, ComplaintStatus, StatusHistory

logger = logging.getLogger("crud")


def _next_complaint_number(db: Session) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"CMP-{today}-"
    stmt = select(Complaint.complaint_number).where(Complaint.complaint_number.like(f"{prefix}%"))
    existing = [n for (n,) in db.execute(stmt).all()]
    seq = max([int(n.rsplit("-", 1)[-1]) for n in existing], default=0) + 1
    return f"{prefix}{seq:04d}"


def create_complaint(db: Session, data: dict) -> Complaint:
    complaint = Complaint(complaint_number=_next_complaint_number(db), **data)
    db.add(complaint)
    db.flush()
    history = StatusHistory(
        complaint_id=complaint.id,
        from_status=None,
        to_status=ComplaintStatus.NEW.value,
        changed_by="system",
        note="Complaint logged",
    )
    db.add(history)
    db.commit()
    db.refresh(complaint)
    logger.info("Created complaint %s", complaint.complaint_number)
    return complaint


def get_complaint(db: Session, complaint_id: str) -> Complaint | None:
    return db.get(Complaint, complaint_id)


def get_complaints(
    db: Session,
    *,
    search: str | None = None,
    status: str | None = None,
    category: str | None = None,
    risk: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Complaint]:
    stmt = select(Complaint).order_by(Complaint.created_at.desc())
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                Complaint.description.ilike(like),
                Complaint.complainant_name.ilike(like),
                Complaint.product_name.ilike(like),
                Complaint.batch_lot_number.ilike(like),
                Complaint.complaint_number.ilike(like),
            )
        )
    if status:
        stmt = stmt.where(Complaint.status == status)
    if category:
        stmt = stmt.where(Complaint.category == category)
    if risk:
        stmt = stmt.where(Complaint.risk_level == risk)
    stmt = stmt.offset(offset).limit(limit)
    return list(db.execute(stmt).scalars().all())


def list_for_duplicate_check(db: Session, limit: int = 200) -> list[dict]:
    stmt = select(Complaint).order_by(Complaint.created_at.desc()).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [
        {
            "id": c.id,
            "complaint_number": c.complaint_number,
            "description": c.description,
            "batch_lot_number": c.batch_lot_number,
        }
        for c in rows
    ]


def update_complaint(db: Session, complaint: Complaint, data: dict) -> Complaint:
    changed_status = "status" in data and data["status"] and data["status"] != complaint.status
    old_status = complaint.status
    for key, value in data.items():
        setattr(complaint, key, value)
    if changed_status:
        history = StatusHistory(
            complaint_id=complaint.id,
            from_status=old_status,
            to_status=data["status"],
            changed_by=data.get("changed_by") or "user",
            note=data.get("status_note") or f"Status changed to {data['status']}",
        )
        db.add(history)
    db.commit()
    db.refresh(complaint)
    return complaint


def delete_complaint(db: Session, complaint: Complaint) -> None:
    db.delete(complaint)
    db.commit()
