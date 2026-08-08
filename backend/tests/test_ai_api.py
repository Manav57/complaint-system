"""API tests for the AI endpoints (extract / assess / completeness /
duplicates / analyze) — always in rule-based MOCK LLM mode."""
from app.models.complaint import Complaint

CONTAMINATION_TEXT = (
    "Customer reports 6 tablets in batch PAR-2024-1187 have black specks on the "
    "surface and a strong burnt odor, suggesting contamination. Dispensed from "
    "a sealed blister pack."
)
ADVERSE_TEXT = (
    "Patient developed severe skin rash and face swelling 1 hour after taking "
    "Omeprazole 20mg capsules and visited the emergency room."
)
DELIVERY_TEXT = (
    "Shipment of Azithromycin suspension arrived 4 days late due to carrier "
    "delay. No product quality issue reported."
)


# ---------------------------------------------------------------- extract
def test_extract_endpoint_mock(client):
    text = (
        "I'm Dr. Jane Wilson from Lakeside Pharmacy. We received Paracetamol "
        "500mg tablets from batch PAR-2025-2210 with a strange black residue on "
        "the surface and a burnt smell suggesting contamination, expiry "
        "09/30/2027. jane.wilson@lakesidepharmacy.com"
    )
    res = client.post("/api/ai/extract", json={"text": text})
    assert res.status_code == 200
    body = res.json()
    fields = body["fields"]
    assert body["raw_text"] == text
    assert "Jane Wilson" in fields["complainant_name"]
    assert fields["complainant_email"] == "jane.wilson@lakesidepharmacy.com"
    assert fields["complainant_company"] == "Lakeside Pharmacy"
    assert fields["product_name"] == "Paracetamol"
    assert fields["batch_lot_number"] == "PAR-2025-2210"
    assert fields["category"] == "Contamination"
    assert fields["severity"] == "High"
    assert fields["strength"] == "500mg"
    assert fields["expiry_date"] == "09/30/2027"


def test_extract_endpoint_falls_back_to_description(client):
    res = client.post("/api/ai/extract", json={"text": "xyz"})
    assert res.status_code == 200
    fields = res.json()["fields"]
    assert fields.get("description") == "xyz"  # nothing extracted -> raw text


def test_extract_endpoint_validation_422(client):
    assert client.post("/api/ai/extract", json={"text": "ab"}).status_code == 422
    assert client.post("/api/ai/extract", json={}).status_code == 422


# ---------------------------------------------------------------- assess
def test_assess_contamination(client):
    res = client.post("/api/ai/assess", json={"description": CONTAMINATION_TEXT})
    assert res.status_code == 200
    body = res.json()
    assert body["risk_level"] == "High"
    assert body["risk_score"] == 0.85
    assert "contamination" in body["rationale"].lower()
    assert isinstance(body["category"], str) and body["category"]
    assert body["duplicate_of"] is None
    assert body["summary"].startswith("Customer reports")
    assert "deviation" in body["root_cause_suggestion"].lower()
    assert "investigation" in body["capa_recommendation"].lower()


def test_assess_adverse_event_is_critical(client):
    body = client.post("/api/ai/assess", json={"description": ADVERSE_TEXT}).json()
    assert body["risk_level"] == "Critical"
    assert body["risk_score"] == 0.95


def test_assess_delivery_is_low(client):
    body = client.post("/api/ai/assess", json={"description": DELIVERY_TEXT}).json()
    assert body["risk_level"] == "Low"
    assert body["risk_score"] == 0.35


def test_assess_detects_duplicate_in_db(client):
    created = client.post(
        "/api/complaints",
        json={
            "complainant_name": "Dr. Jane Wilson",
            "description": CONTAMINATION_TEXT,
            "batch_lot_number": "PAR-2024-1187",
        },
    ).json()
    body = client.post("/api/ai/assess", json={"description": CONTAMINATION_TEXT}).json()
    assert body["duplicate_of"] == created["id"]
    assert body["duplicate_score"] == 1.0


def test_assess_batch_match_boosts_duplicate(client):
    created = client.post(
        "/api/complaints",
        json={
            "complainant_name": "Dr. Jane Wilson",
            "description": "Totally unrelated complaint about shipping delays.",
            "batch_lot_number": "PAR-2024-1187",
        },
    ).json()
    body = client.post(
        "/api/ai/assess",
        json={"description": CONTAMINATION_TEXT, "batch_lot_number": "PAR-2024-1187"},
    ).json()
    assert body["duplicate_of"] == created["id"]
    assert body["duplicate_score"] == 0.75


def test_assess_validation_422(client):
    assert client.post("/api/ai/assess", json={"description": "ab"}).status_code == 422


# ---------------------------------------------------------------- completeness
def test_completeness_flags_missing_fields(client):
    res = client.post("/api/ai/completeness", json={"text": "Customer reports an issue with the shipment"})
    assert res.status_code == 200
    body = res.json()
    assert body["complete"] is False
    # "customer" present -> complainant_name covered; batch + product missing
    assert set(body["missing_fields"]) == {"batch_lot_number", "product_name"}
    assert body["message"].startswith("Missing fields:")


def test_completeness_complete(client):
    res = client.post(
        "/api/ai/completeness",
        json={"text": "I am John Smith. Reporting a problem with Product Paracetamol, batch PAR-123."},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["complete"] is True
    assert body["missing_fields"] == []
    assert body["message"] == "All required fields present."


def test_completeness_validation_422(client):
    assert client.post("/api/ai/completeness", json={"text": "ab"}).status_code == 422


# ---------------------------------------------------------------- duplicates
def test_duplicates_endpoint(client):
    desc = "Customer reports black specks on tablets from batch PAR-2025-2210."
    a = client.post(
        "/api/complaints",
        json={"complainant_name": "Person A", "description": desc, "batch_lot_number": "PAR-2025-2210"},
    ).json()
    b = client.post(
        "/api/complaints",
        json={"complainant_name": "Person B", "description": desc, "batch_lot_number": "PAR-2025-2210"},
    ).json()

    res = client.get(f"/api/ai/duplicates/{b['id']}")
    assert res.status_code == 200
    matches = res.json()
    assert len(matches) == 1
    assert matches[0]["complaint_id"] == a["id"]
    assert matches[0]["complaint_number"] == a["complaint_number"]
    assert matches[0]["score"] == 1.0
    assert a["complaint_number"] in matches[0]["reason"]

    res = client.get(f"/api/ai/duplicates/{a['id']}").json()
    assert [m["complaint_id"] for m in res] == [b["id"]]


def test_duplicates_endpoint_no_matches(client):
    client.post(
        "/api/complaints",
        json={"complainant_name": "Person A", "description": "Complaint about shipping delays."},
    ).json()
    b = client.post(
        "/api/complaints",
        json={"complainant_name": "Person B", "description": "Black specks on tablets, contamination."},
    ).json()
    assert client.get(f"/api/ai/duplicates/{b['id']}").json() == []


def test_duplicates_endpoint_404(client):
    res = client.get("/api/ai/duplicates/does-not-exist")
    assert res.status_code == 404


# ---------------------------------------------------------------- analyze
def test_analyze_existing_persists_results(client):
    created = client.post(
        "/api/complaints",
        json={"complainant_name": "Dr. Jane Wilson", "description": CONTAMINATION_TEXT},
    ).json()
    res = client.post(f"/api/ai/analyze?complaint_id={created['id']}")
    assert res.status_code == 200
    body = res.json()
    assert body["complaint_id"] == created["id"]
    assert body["risk_level"] == "High"
    assert body["risk_score"] == 0.85
    assert body["summary"].startswith("Customer reports")

    # persisted back to the record
    detail = client.get(f"/api/complaints/{created['id']}").json()
    assert detail["risk_level"] == "High"
    assert detail["risk_score"] == 0.85
    assert detail["ai_summary"].startswith("Customer reports")
    assert "deviation" in detail["root_cause_suggestion"].lower()
    assert "investigation" in detail["capa_recommendation"].lower()


def test_analyze_existing_404(client):
    res = client.post("/api/ai/analyze?complaint_id=does-not-exist")
    assert res.status_code == 404
