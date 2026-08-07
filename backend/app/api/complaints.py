"""Complaint CRUD + status tracking endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.crud import (
    create_complaint,
    delete_complaint,
    get_complaint,
    get_complaints,
    update_complaint,
)
from app.database import get_db
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintDetail,
    ComplaintList,
    ComplaintUpdate,
)

router = APIRouter(prefix="/api/complaints", tags=["complaints"])
logger = logging.getLogger("api")


@router.get("", response_model=list[ComplaintList])
def list_complaints(
    search: str | None = None,
    status: str | None = None,
    category: str | None = None,
    risk: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    return get_complaints(db, search=search, status=status, category=category, risk=risk, limit=limit, offset=offset)


@router.post("", response_model=ComplaintDetail, status_code=201)
def create_new_complaint(payload: ComplaintCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["complaint_date"] = data.get("complaint_date") or None
    return create_complaint(db, data)


@router.get("/{complaint_id}", response_model=ComplaintDetail)
def get_complaint_detail(complaint_id: str, db: Session = Depends(get_db)):
    complaint = get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


@router.patch("/{complaint_id}", response_model=ComplaintDetail)
def update_complaint_detail(complaint_id: str, payload: ComplaintUpdate, db: Session = Depends(get_db)):
    complaint = get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    data = payload.model_dump(exclude_unset=True)
    return update_complaint(db, complaint, data)


@router.delete("/{complaint_id}", status_code=204)
def delete_complaint_detail(complaint_id: str, db: Session = Depends(get_db)):
    complaint = get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    delete_complaint(db, complaint)


@router.get("/{complaint_id}/status-history")
def get_status_history(complaint_id: str, db: Session = Depends(get_db)):
    complaint = get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return [
        {
            "from_status": h.from_status,
            "to_status": h.to_status,
            "changed_by": h.changed_by,
            "note": h.note,
            "changed_at": h.changed_at.isoformat(),
        }
        for h in complaint.status_history
    ]
