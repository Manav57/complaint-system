# Demo Video Scripts

Two videos are required (5–10 min each). Record with OBS / Loom at 1920x1080.
Start servers first: backend on :8000, frontend on :3000 (see root README).

---

## Demo Video 1 — Frontend + API + Backend walkthrough (5–10 min)

1. **Intro (0:30)** — What the app is: AI complaint management for pharma manufacturing (API/FDF).
2. **Backend (1:30)** — Show `uvicorn` running; open **http://localhost:8000/docs** (Swagger).
   - Walk the endpoint list: `/api/complaints*`, `/api/ai/extract`, `/api/ai/assess`, `/api/ai/completeness`, `/api/ai/duplicates`, `/api/ai/analyze`.
   - Execute `GET /api/complaints` in Swagger — show seeded JSON records with risk levels.
3. **Frontend list view (1:00)** — http://localhost:3000 — complaints table with risk pills (Critical/High/Medium/Low), status pills. Search "Paracetamol", filter by status = New, filter risk = High.
4. **Detail view (1:30)** — open the Adverse Event complaint (Critical). Show: description, batch info, status history timeline (New → Investigating), AI copilot panel with rationale, summary, root cause, CAPA.
5. **Status change (1:00)** — click status buttons (New → Under Review → Investigating); refresh and show the timeline got a new entry.
6. **DB (1:00)** — show the `complaints` table via psql: `SELECT complaint_number, risk_level, status FROM complaints;` and `SELECT * FROM status_history;`
7. **Wrap (0:30)** — recap features.

## Demo Video 2 — LangGraph workflow + AI form population + Copilot (5–10 min)

1. **Intro (0:30)** — Where the agent lives: `backend/app/ai/graph.py` + `llm.py`; LangGraph StateGraph wired to Groq (gemma2-9b-it; llama-3.3-70b-versatile for heavy reasoning). Show the code briefly.
2. **Form auto-population (2:00)** — Go to **Log Complaint** → paste a raw customer message (use the sample dropdown):
   > "Hi, I'm Dr. Jane Wilson from Lakeside Pharmacy. We received Paracetamol 500mg tablets from batch PAR-2025-2210 with a strange black residue on the surface and a burnt smell. This looks like contamination, 8 tablets affected, expiry 09/2027."
   Click **Auto-populate form** → watch the fields fill (name, company, product, batch, category, severity, strength). Completeness banner appears.
3. **Copilot risk assessment (2:00)** — click **Run Copilot assessment** → watch the LangGraph steps render (assess_risk → check_completeness → gen_summary → gen_root_cause) → risk pill, score, rationale, summary, root cause, CAPA appear; duplicate banner if matched.
4. **Conversational correction + PDF upload (2:00)** — in the Copilot chat panel, paste a message → fields populate + chat reply appears. Send a follow-up like "the batch is actually PAR-2025-2211" → **only the batch field changes** in the form (prove it: every other field untouched). Attach `docs/sample-complaints/complaint_omeprazole_adverse_event.pdf` via 📎 → fields populate from the PDF text layer; correct a value afterwards and watch only that field update. Show the LangGraph amend node in `graph.py` + the pypdf extraction in `app/ai/pdf.py`.
5. **Submit (1:00)** — click **Submit complaint** → lands on detail page; AI results persisted (run `/api/ai/analyze` or show stored `risk_rationale` in psql).
6. **Run 2 more varied complaints (2:00)** — adverse event text (Critical result) and logistics delay (Low result) — show the classifier differentiates.
7. **Swagger deep dive (1:00)** — POST `/api/ai/assess` with a description, show the full JSON (risk_level, risk_score, rationale, capa_recommendation). Also show `POST /api/ai/session` and `POST /api/ai/session/{id}/message`.
8. **Wrap (0:30)** — recap: LangGraph orchestration + Groq + mock fallback without a key.

### Tip for clean demo
Set `GROQ_API_KEY` in `backend/.env` for live LLM output; without it the app runs on the deterministic mock (everything still works — the mock is logged with a warning).
