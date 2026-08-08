"""Generate the sample complaint PDFs in this folder.

These are real text-based PDFs (not scans) so the text layer can be extracted
with pypdf and fed through the same extract/amend AI pipeline as typed text.

Run from anywhere:
    python docs/sample-complaints/generate_samples.py

Requires: reportlab (declared in backend/requirements.txt)
"""
import os

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

COMPLAINTS = [
    {
        "filename": "complaint_paracetamol_contamination.pdf",
        "title": "AIVOA PHARMA LABS - CUSTOMER COMPLAINT REPORT",
        "lines": [
            "Date: 2026-08-06",
            "Complaint Reference: CUST-2026-0081",
            "",
            "To Whom It May Concern,",
            "",
            "I'm Dr. Jane Wilson from Lakeside Pharmacy. We received Paracetamol "
            "500mg tablets from batch PAR-2025-2210 with a strange black residue "
            "on the surface and a burnt smell, suggesting contamination. 8 tablets "
            "were affected, expiry 09/2027. My email is "
            "jane.wilson@lakesidepharmacy.com and my phone is +1-555-0101.",
            "",
            "We would like a replacement and a formal investigation of the batch.",
            "",
            "Regards,",
            "Dr. Jane Wilson",
            "Lakeside Pharmacy, 2210 Riverside Avenue",
        ],
    },
    {
        "filename": "complaint_omeprazole_adverse_event.pdf",
        "title": "AIVOA PHARMA LABS - CUSTOMER COMPLAINT REPORT",
        "lines": [
            "Date: 2026-08-07",
            "Complaint Reference: CUST-2026-0084",
            "",
            "To Whom It May Concern,",
            "",
            "This is Rahul Mehta from Sunrise Medicals. A patient developed severe "
            "skin rash and face swelling 1 hour after taking Omeprazole 20mg "
            "capsules from batch OME-2025-8841 and needed emergency care at the "
            "hospital. Please treat this as a possible adverse reaction for "
            "pharmacovigilance review.",
            "",
            "Contact rahul@sunrise-medicals.com or +91-98765-43210 for the patient "
            "case details.",
            "",
            "Regards,",
            "Rahul Mehta",
            "Sunrise Medicals, 88 Market Road",
        ],
    },
]


def _wrap(text: str, width: int = 95) -> list[str]:
    words = text.split()
    lines, cur = [], []
    for w in words:
        if sum(len(x) + 1 for x in cur) + len(w) > width:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    return lines


def make_pdf(filename: str, title: str, lines: list[str]) -> None:
    path = os.path.join(OUT_DIR, filename)
    c = canvas.Canvas(path, pagesize=letter)
    width, height = letter
    y = height - 1.1 * inch

    c.setFont("Helvetica-Bold", 15)
    c.drawString(0.75 * inch, y, title)
    y -= 0.35 * inch
    c.setStrokeColorRGB(0.1, 0.3, 0.5)
    c.setLineWidth(1.5)
    c.line(0.75 * inch, y, width - 0.75 * inch, y)
    y -= 0.4 * inch

    c.setFont("Helvetica", 11)
    for raw in lines:
        if not raw:
            y -= 0.18 * inch
            continue
        for line in _wrap(raw):
            c.drawString(0.75 * inch, y, line)
            y -= 0.22 * inch
            if y < 0.8 * inch:  # next page (not expected for these short letters)
                c.showPage()
                c.setFont("Helvetica", 11)
                y = height - 1.0 * inch
    c.save()
    print(f"wrote {path}")


if __name__ == "__main__":
    for c in COMPLAINTS:
        make_pdf(c["filename"], c["title"], c["lines"])
