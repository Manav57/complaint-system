"""API tests for the complaint CRUD + status tracking endpoints.

Runs against the isolated SQLite test database created in conftest.py.
"""
from app.models.complaint import Complaint, StatusHistory

VALID_PAYLOAD = {
    "complainant_name": "Dr. Jane Wilson",
    "complainant_email": "jane.wilson@lakesidepharmacy.com",
    "complainant_phone": "+1-555-0101",
    "complainant_company": "Lakeside Pharmacy",
    "product_name": "Paracetamol",
    "batch_lot_number": "PAR-2025-2210",
    "dosage_form": "tablet",
    "strength": "500 mg",
    "expiry_date": "09/2027",
    "category": "Product Quality",
    "severity": "High",
    "description": "Customer reports black specks on tablets from batch PAR-2025-2210.",
    "quantity_affected": "8",
    "submitted_via": "Phone",
}


# ---------------------------------------------------------------- create
def test_create_complaint(client):
    res = client.post("/api/complaints", json=VALID_PAYLOAD)
    assert res.status_code == 201
    body = res.json()
    assert body["id"]
    assert body["complaint_number"].startswith("CMP-")
    assert body["status"] == "New"
    assert body["complainant_name"] == "Dr. Jane Wilson"
    assert body["product_name"] == "Paracetamol"
    assert body["complaint_date"] is None
    assert body["created_at"]
    assert len(body["status_history"]) == 1
    assert body["status_history"][0]["to_status"] == "New"


def test_create_complaint_increments_number(client):
    first = client.post("/api/complaints", json=VALID_PAYLOAD).json()
    second = client.post("/api/complaints", json=VALID_PAYLOAD).json()
    assert second["complaint_number"] == first["complaint_number"][:-4] + "0002"


def test_create_complaint_stores_optional_date(client):
    res = client.post(
        "/api/complaints", json={**VALID_PAYLOAD, "complaint_date": "2026-08-08"}
    )
    assert res.status_code == 201
    assert res.json()["complaint_date"] == "2026-08-08"


def test_create_complaint_validation_422(client):
    # missing required description
    res = client.post("/api/complaints", json={"complainant_name": "A"})
    assert res.status_code == 422
    # empty complainant_name
    res = client.post("/api/complaints", json={**VALID_PAYLOAD, "complainant_name": ""})
    assert res.status_code == 422
    # empty description
    res = client.post("/api/complaints", json={**VALID_PAYLOAD, "description": ""})
    assert res.status_code == 422


# ---------------------------------------------------------------- list
def test_list_complaints_empty(client):
    assert client.get("/api/complaints").json() == []


def test_list_complaints_returns_all(client):
    client.post("/api/complaints", json=VALID_PAYLOAD)
    client.post(
        "/api/complaints",
        json={**VALID_PAYLOAD, "product_name": "Amoxicillin", "description": "Broken seals on blister packs."},
    )
    res = client.get("/api/complaints")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_list_filters_by_status(client):
    created = client.post("/api/complaints", json=VALID_PAYLOAD).json()
    client.patch(f"/api/complaints/{created['id']}", json={"status": "Investigating"})
    res = client.get("/api/complaints", params={"status": "Investigating"}).json()
    assert len(res) == 1 and res[0]["id"] == created["id"]
    res = client.get("/api/complaints", params={"status": "New"}).json()
    assert len(res) == 0


def test_list_filters_by_category(client):
    client.post("/api/complaints", json=VALID_PAYLOAD)  # Product Quality
    client.post(
        "/api/complaints",
        json={**VALID_PAYLOAD, "category": "Labeling", "description": "Wrong strength printed on carton."},
    )
    res = client.get("/api/complaints", params={"category": "Labeling"}).json()
    assert len(res) == 1 and res[0]["category"] == "Labeling"


def test_list_filters_by_risk(client, db_session):
    a = client.post("/api/complaints", json=VALID_PAYLOAD).json()
    b = client.post(
        "/api/complaints",
        json={**VALID_PAYLOAD, "product_name": "Amoxicillin", "description": "Broken seals on blister packs."},
    ).json()
    for cid, level in ((a["id"], "High"), (b["id"], "Medium")):
        c = db_session.get(Complaint, cid)
        c.risk_level = level
        c.risk_score = 0.7
    db_session.commit()

    res = client.get("/api/complaints", params={"risk": "High"}).json()
    assert [x["id"] for x in res] == [a["id"]]
    res = client.get("/api/complaints", params={"risk": "Medium"}).json()
    assert [x["id"] for x in res] == [b["id"]]
    assert client.get("/api/complaints", params={"risk": "Critical"}).json() == []


def test_list_search(client):
    client.post("/api/complaints", json=VALID_PAYLOAD)
    client.post(
        "/api/complaints",
        json={**VALID_PAYLOAD, "product_name": "Amoxicillin", "batch_lot_number": "AMX-2025-0001",
              "description": "Broken seals on blister packs."},
    )
    assert len(client.get("/api/complaints", params={"search": "paracetamol"}).json()) == 1
    assert len(client.get("/api/complaints", params={"search": "jane"}).json()) == 2
    assert len(client.get("/api/complaints", params={"search": "AMX-2025-0001"}).json()) == 1
    assert client.get("/api/complaints", params={"search": "zzzz-no-match"}).json() == []


def test_list_pagination_newest_first(client):
    ids = []
    for i in range(5):
        ids.append(
            client.post("/api/complaints", json={**VALID_PAYLOAD, "complainant_name": f"Person {i}"}).json()["id"]
        )
    page1 = client.get("/api/complaints", params={"limit": 2}).json()
    page2 = client.get("/api/complaints", params={"limit": 2, "offset": 2}).json()
    assert [x["id"] for x in page1] == ids[3:][::-1]
    assert [x["id"] for x in page2] == ids[1:3][::-1]


def test_list_limit_capped_at_500(client):
    res = client.get("/api/complaints", params={"limit": 9999})
    assert res.status_code == 422


# ---------------------------------------------------------------- get
def test_get_complaint_detail(client):
    created = client.post("/api/complaints", json=VALID_PAYLOAD).json()
    res = client.get(f"/api/complaints/{created['id']}")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == created["id"]
    assert body["complainant_email"] == VALID_PAYLOAD["complainant_email"]
    assert body["batch_lot_number"] == "PAR-2025-2210"


def test_get_complaint_404(client):
    res = client.get("/api/complaints/does-not-exist")
    assert res.status_code == 404
    assert res.json()["detail"] == "Complaint not found"


# ---------------------------------------------------------------- patch / status history
def test_patch_status_writes_status_history(client):
    created = client.post("/api/complaints", json=VALID_PAYLOAD).json()
    cid = created["id"]

    history = client.get(f"/api/complaints/{cid}/status-history").json()
    assert len(history) == 1
    assert history[0]["from_status"] is None
    assert history[0]["to_status"] == "New"
    assert history[0]["changed_by"] == "system"

    res = client.patch(f"/api/complaints/{cid}", json={"status": "Under Review"})
    assert res.status_code == 200
    assert res.json()["status"] == "Under Review"

    history = client.get(f"/api/complaints/{cid}/status-history").json()
    assert len(history) == 2
    assert history[1]["from_status"] == "New"
    assert history[1]["to_status"] == "Under Review"
    assert history[1]["changed_by"] == "user"
    assert history[1]["note"] == "Status changed to Under Review"


def test_patch_same_status_does_not_write_history(client):
    created = client.post("/api/complaints", json=VALID_PAYLOAD).json()
    res = client.patch(f"/api/complaints/{created['id']}", json={"status": "New"})
    assert res.status_code == 200
    assert len(client.get(f"/api/complaints/{created['id']}/status-history").json()) == 1


def test_patch_updates_work_fields(client):
    created = client.post("/api/complaints", json=VALID_PAYLOAD).json()
    res = client.patch(
        f"/api/complaints/{created['id']}",
        json={"notes": "Needs batch record review", "assigned_to": "QA Team", "severity": "Low"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["notes"] == "Needs batch record review"
    assert body["assigned_to"] == "QA Team"
    assert body["severity"] == "Low"


def test_patch_status_changed_by_is_dropped_by_schema(client):
    """Regression-documents audit finding: frontend sends changed_by but the
    ComplaintUpdate schema has no such field, so it is silently dropped and the
    audit trail records 'user' instead of the actual operator."""
    created = client.post("/api/complaints", json=VALID_PAYLOAD).json()
    res = client.patch(
        f"/api/complaints/{created['id']}",
        json={"status": "Resolved", "changed_by": "QA User", "status_note": "Closed after CAPA"},
    )
    assert res.status_code == 200
    history = client.get(f"/api/complaints/{created['id']}/status-history").json()
    assert history[1]["changed_by"] == "user"  # schema dropped 'QA User'
    assert history[1]["note"] == "Status changed to Resolved"  # status_note dropped too


def test_patch_complaint_404(client):
    res = client.patch("/api/complaints/does-not-exist", json={"status": "Resolved"})
    assert res.status_code == 404


def test_status_history_endpoint_404(client):
    res = client.get("/api/complaints/does-not-exist/status-history")
    assert res.status_code == 404


# ---------------------------------------------------------------- delete
def test_delete_complaint(client):
    created = client.post("/api/complaints", json=VALID_PAYLOAD).json()
    res = client.delete(f"/api/complaints/{created['id']}")
    assert res.status_code == 204
    assert client.get(f"/api/complaints/{created['id']}").status_code == 404


def test_delete_cascades_status_history(client, db_session):
    created = client.post("/api/complaints", json=VALID_PAYLOAD).json()
    cid = created["id"]
    client.patch(f"/api/complaints/{cid}", json={"status": "Investigating"})
    assert db_session.query(StatusHistory).filter_by(complaint_id=cid).count() == 2
    client.delete(f"/api/complaints/{cid}")
    assert db_session.query(StatusHistory).filter_by(complaint_id=cid).count() == 0
    assert db_session.get(Complaint, cid) is None


def test_delete_complaint_404(client):
    res = client.delete("/api/complaints/does-not-exist")
    assert res.status_code == 404


# ---------------------------------------------------------------- meta
def test_root_endpoint(client):
    res = client.get("/")
    assert res.status_code == 200
    body = res.json()
    assert body["app"] and body["version"] and body["docs"] == "/docs"


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["database"] is True
    assert body["groq_configured"] is False  # tests always run in mock mode
