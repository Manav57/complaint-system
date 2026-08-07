"""Create tables and seed sample pharma complaint data."""
import logging

from app.database import Base, SessionLocal, engine
from app.models.complaint import Complaint, ComplaintStatus, StatusHistory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

SAMPLE_COMPLAINTS = [
    {
        "complainant_name": "Dr. Sarah Mitchell",
        "complainant_email": "sarah.mitchell@citypharmacy.com",
        "complainant_phone": "+1-555-0101",
        "complainant_company": "City Pharmacy",
        "product_name": "Paracetamol",
        "batch_lot_number": "PAR-2024-1187",
        "dosage_form": "tablet",
        "strength": "500 mg",
        "expiry_date": "12/2026",
        "category": "Product Quality",
        "severity": "High",
        "description": "Customer reports 6 tablets in batch PAR-2024-1187 have black specks on the surface and a strong burnt odor. The tablets were dispensed from a sealed blister pack. Photos provided show dark discoloration covering about 20% of the tablet surface.",
        "quantity_affected": "6",
        "status": ComplaintStatus.INVESTIGATING.value,
        "risk_level": "High",
        "risk_score": 0.85,
        "risk_rationale": "Possible contamination or foreign matter in a marketed batch - requires immediate investigation and potential recall decision.",
    },
    {
        "complainant_name": "James Rodriguez",
        "complainant_email": "j.rodriguez@medsupply.net",
        "complainant_phone": "+1-555-0142",
        "complainant_company": "MedSupply Distributors",
        "product_name": "Amoxicillin",
        "batch_lot_number": "AMX-2024-0432",
        "dosage_form": "capsule",
        "strength": "250 mg",
        "expiry_date": "08/2026",
        "category": "Packaging",
        "severity": "Medium",
        "description": "Blister packs of batch AMX-2024-0432 arrived with broken seals and several punctured blisters. Packets were inside an outer carton that showed no external damage, suggesting the issue occurred during packing.",
        "quantity_affected": "12",
        "status": ComplaintStatus.UNDER_REVIEW.value,
        "risk_level": "Medium",
        "risk_score": 0.55,
        "risk_rationale": "Packaging integrity issue that could compromise sterility and stability, but no patient harm reported.",
    },
    {
        "complainant_name": "Maria Chen",
        "complainant_email": "maria.chen@gmail.com",
        "complainant_phone": "+1-555-0167",
        "complainant_company": "Consumer",
        "product_name": "Omeprazole",
        "batch_lot_number": "OME-2024-2210",
        "dosage_form": "capsule",
        "strength": "20 mg",
        "expiry_date": "03/2027",
        "category": "Adverse Event",
        "severity": "High",
        "description": "Patient developed severe skin rash and swelling of the face within 2 hours of taking Omeprazole 20mg from batch OME-2024-2210. Patient visited the emergency room. No known allergies prior to this event.",
        "quantity_affected": "1",
        "status": ComplaintStatus.INVESTIGATING.value,
        "risk_level": "Critical",
        "risk_score": 0.95,
        "risk_rationale": "Serious adverse event with ER visit - potential patient safety signal requiring pharmacovigilance escalation.",
    },
    {
        "complainant_name": "Dr. Alan Foster",
        "complainant_email": "alan.foster@hospitallab.com",
        "complainant_phone": "+1-555-0199",
        "complainant_company": "Hospital Lab Services",
        "product_name": "Metformin",
        "batch_lot_number": "MET-2024-3307",
        "dosage_form": "tablet",
        "strength": "850 mg",
        "expiry_date": "11/2026",
        "category": "Potency",
        "severity": "Medium",
        "description": "Three patients report that Metformin 850mg tablets from batch MET-2024-3307 are not controlling blood sugar levels. Patients switched from a previous batch and symptoms returned within a week. No other medication changes.",
        "quantity_affected": "3",
        "status": ComplaintStatus.NEW.value,
        "risk_level": "High",
        "risk_score": 0.75,
        "risk_rationale": "Reported lack of efficacy across multiple patients - potential potency issue requiring dissolution testing.",
    },
    {
        "complainant_name": "Linda Patel",
        "complainant_email": "linda.patel@discountdrugs.com",
        "complainant_phone": "+1-555-0113",
        "complainant_company": "Discount Drugs",
        "product_name": "Atorvastatin",
        "batch_lot_number": "ATO-2024-0955",
        "dosage_form": "tablet",
        "strength": "10 mg",
        "expiry_date": "05/2027",
        "category": "Labeling",
        "severity": "Medium",
        "description": "Cartons of Atorvastatin 10mg from batch ATO-2024-0955 have the strength printed as '100 mg' on the side panel. The blister pack label inside is correct at 10mg. Potential for patient confusion with incorrect dosing.",
        "quantity_affected": "24",
        "status": ComplaintStatus.UNDER_REVIEW.value,
        "risk_level": "Medium",
        "risk_score": 0.65,
        "risk_rationale": "Labeling discrepancy between carton and blister - potential patient confusion about correct dose.",
    },
    {
        "complainant_name": "Robert Nguyen",
        "complainant_email": "r.nguyen@carepluspharmacy.com",
        "complainant_phone": "+1-555-0158",
        "complainant_company": "CarePlus Pharmacy",
        "product_name": "Azithromycin",
        "batch_lot_number": "AZI-2024-7741",
        "dosage_form": "suspension",
        "strength": "200 mg/5ml",
        "expiry_date": "09/2026",
        "category": "Delivery / Logistics",
        "severity": "Low",
        "description": "Shipment of Azithromycin suspension arrived 4 days late due to carrier delay. Pharmacy ran out of stock and had to direct patients to a competitor. No product quality issue reported.",
        "quantity_affected": "40",
        "status": ComplaintStatus.RESOLVED.value,
        "risk_level": "Low",
        "risk_score": 0.35,
        "risk_rationale": "Logistics concern only - no product quality or patient safety impact reported.",
    },
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        count = db.query(Complaint).count()
        if count > 0:
            logger.info("DB already has %d complaints, skipping seed.", count)
            return
        for idx, item in enumerate(SAMPLE_COMPLAINTS, start=1):
            item = dict(item)
            status = item.pop("status")
            complaint = Complaint(complaint_number=f"CMP-SEED-{idx:04d}", **item)
            complaint.status = status
            db.add(complaint)
            db.flush()
            db.add(
                StatusHistory(
                    complaint_id=complaint.id,
                    from_status=None,
                    to_status=status,
                    changed_by="system",
                    note="Seeded sample complaint",
                )
            )
        db.commit()
        logger.info("Seeded %d sample complaints.", len(SAMPLE_COMPLAINTS))
    finally:
        db.close()


if __name__ == "__main__":
    seed()
