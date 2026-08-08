"""API tests for conversational correction sessions + PDF upload.

Runs in MOCK LLM mode (conftest forces GROQ_API_KEY empty), so behaviour is
deterministic. Covers the four required flows:
  - text complaint populates fields (extract workflow)
  - follow-up correction changes ONLY the mentioned fields (amend workflow)
  - PDF upload populates fields (same extract workflow)
  - correction after a PDF upload works the same way
plus validation errors.
"""
import io

from reportlab.pdfgen import canvas

CONTAMINATION_TEXT = (
    "I'm Dr. Jane Wilson from Lakeside Pharmacy. We received Paracetamol 500mg "
    "tablets from batch PAR-2025-2210 with a strange black residue on the surface "
    "and a burnt smell suggesting contamination, expiry 09/30/2027. "
    "jane.wilson@lakesidepharmacy.com"
)


def _make_pdf(text: str) -> bytes:
    """Render text into a small real text-based PDF (no OCR needed).

    Wraps on word boundaries so words are never split across lines (which would
    scramble the extracted text layer).
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.setFont("Helvetica", 11)
    y = 750
    for line in text.splitlines():
        cur: list[str] = []
        for word in line.split():
            if cur and sum(len(x) + 1 for x in cur) + len(word) > 90:
                c.drawString(60, y, " ".join(cur))
                y -= 16
                cur = [word]
            else:
                cur.append(word)
        if cur:
            c.drawString(60, y, " ".join(cur))
            y -= 16
    c.save()
    return buf.getvalue()


def test_create_session(client):
    res = client.post("/api/ai/session")
    assert res.status_code == 200
    body = res.json()
    assert body["session_id"]
    assert body["fields"] == {}
    assert "intake assistant" in body["reply"].lower()


def test_session_text_message_populates_fields(client):
    session_id = client.post("/api/ai/session").json()["session_id"]
    res = client.post(f"/api/ai/session/{session_id}/message", json={"text": CONTAMINATION_TEXT})
    assert res.status_code == 200
    body = res.json()
    fields = body["fields"]
    assert body["session_id"] == session_id
    assert "Jane Wilson" in fields["complainant_name"]
    assert fields["product_name"] == "Paracetamol"
    assert fields["batch_lot_number"] == "PAR-2025-2210"
    assert fields["category"] == "Contamination"
    assert fields["severity"] == "High"
    assert body["changed"] == fields  # first message: everything is new
    assert "extracted" in body["reply"].lower()


def test_session_followup_changes_only_mentioned_field(client):
    session_id = client.post("/api/ai/session").json()["session_id"]
    client.post(f"/api/ai/session/{session_id}/message", json={"text": CONTAMINATION_TEXT})
    res = client.post(
        f"/api/ai/session/{session_id}/message",
        json={"text": "Actually, the correct batch number is PAR-2025-2211"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["changed"] == {"batch_lot_number": "PAR-2025-2211"}
    # every other field is preserved exactly
    assert body["fields"]["batch_lot_number"] == "PAR-2025-2211"
    assert body["fields"]["product_name"] == "Paracetamol"
    assert body["fields"]["severity"] == "High"
    assert body["fields"]["complainant_email"] == "jane.wilson@lakesidepharmacy.com"
    assert "PAR-2025-2211" in body["reply"]


def test_session_followup_with_no_changes_returns_empty_changed(client):
    session_id = client.post("/api/ai/session").json()["session_id"]
    client.post(f"/api/ai/session/{session_id}/message", json={"text": CONTAMINATION_TEXT})
    res = client.post(
        f"/api/ai/session/{session_id}/message",
        json={"text": "Thanks, that is all."},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["changed"] == {}
    assert body["fields"]["batch_lot_number"] == "PAR-2025-2210"  # untouched


def test_session_pdf_upload_populates_fields(client):
    session_id = client.post("/api/ai/session").json()["session_id"]
    res = client.post(
        f"/api/ai/session/{session_id}/message",
        files={"file": ("complaint.pdf", _make_pdf(CONTAMINATION_TEXT), "application/pdf")},
    )
    assert res.status_code == 200
    fields = res.json()["fields"]
    assert fields["product_name"] == "Paracetamol"
    assert fields["batch_lot_number"] == "PAR-2025-2210"
    assert fields["category"] == "Contamination"


def test_session_correction_after_pdf(client):
    session_id = client.post("/api/ai/session").json()["session_id"]
    client.post(
        f"/api/ai/session/{session_id}/message",
        files={"file": ("complaint.pdf", _make_pdf(CONTAMINATION_TEXT), "application/pdf")},
    )
    res = client.post(
        f"/api/ai/session/{session_id}/message",
        json={"text": "The complainant email is actually wilson@lakeside.com"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["changed"].get("complainant_email") == "wilson@lakeside.com"
    assert body["fields"]["complainant_email"] == "wilson@lakeside.com"
    assert body["fields"]["batch_lot_number"] == "PAR-2025-2210"  # preserved


def test_session_message_unknown_session_404(client):
    res = client.post("/api/ai/session/does-not-exist/message", json={"text": "hello"})
    assert res.status_code == 404
    assert res.json()["detail"] == "Session not found"


def test_session_message_missing_input_400(client):
    session_id = client.post("/api/ai/session").json()["session_id"]
    assert client.post(f"/api/ai/session/{session_id}/message", json={}).status_code == 400


def test_session_rejects_non_pdf_upload(client):
    session_id = client.post("/api/ai/session").json()["session_id"]
    res = client.post(
        f"/api/ai/session/{session_id}/message",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert res.status_code == 400
    assert "PDF" in res.json()["detail"]
