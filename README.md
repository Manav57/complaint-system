# PharmaCare — AI Customer Complaint Management System

AI-powered complaint intake and risk assessment for pharmaceutical manufacturing (API / FDF), built for the AIVOA Round 1 AI Product Engineer (Fresher) assessment.

**Stack (as mandated):** React + Redux (frontend) · FastAPI (backend) · LangGraph (agent orchestration) · Groq `gemma2-9b-it` (LLM, with optional `llama-3.3-70b-versatile` for heavier reasoning) · PostgreSQL (DB) · Google "Inter" font.

## Features

### Core
- **Log Customer Complaint** — structured intake form (complainant, product batch/lot, category, severity, description, etc.) with an **AI agent that auto-populates the form from free text** (LangGraph extract workflow).
- **AI Copilot Risk Assessment** — LangGraph-driven panel next to the form/detail view that classifies risk (Low/Medium/High/Critical), with rationale, duplicate detection, summary, root-cause suggestion and CAPA recommendation.
- **Complaint management** — list (search + filters by status/category/risk), detail view, status tracking with history timeline, edit, delete.

### Conversational intake (session-based)
- **Chat with the intake agent** — a Copilot chat panel (`POST /api/ai/session` + `/api/ai/session/{id}/message`) that extracts complaint fields from a pasted message and shows a natural-language reply in the chat bubble.
- **Conversational corrections** — follow-up messages run a LangGraph **amend** workflow that changes ONLY the fields the user mentions (e.g. "the batch is actually PAR-2025-2211" updates just the batch/lot), preserving every other field exactly.
- **PDF upload** — attach a text-based PDF complaint (📎 in the chat); its text layer is extracted with pypdf and fed through the **same** extract/amend logic — no separate pipeline. Sample PDFs live in `docs/sample-complaints/`.

### Bonus AI features (all implemented)
1. Completeness checker (flags missing required fields before submit)
2. AI risk classification (integrated into Copilot)
3. Complaint summary generation
4. Duplicate complaint detection (batch match + description similarity)
5. Root cause recommendation
6. CAPA (Corrective and Preventive Action) recommendation

## Architecture

```
frontend/  React 18 + Redux Toolkit + React Router (Vite)  →  :3000 (proxy /api → :8000)
backend/   FastAPI + SQLAlchemy 2 + Alembic  →  :8000  (OpenAPI docs at /docs)
           app/ai/graph.py   →  LangGraph StateGraph workflows (extract + assess)
           app/ai/llm.py     →  Groq client (gemma2-9b-it) with rule-based mock fallback
DB         PostgreSQL  →  complaints, status_history
```

### LangGraph workflows (`backend/app/ai/graph.py`)

1. **Extract workflow** — `START → extract → finalize → END`
   Extracts structured fields (complainant, product, batch, category, severity…) from the customer's free-text message → auto-fills the form.
2. **Assess workflow** — `START → assess_risk → check_completeness → gen_summary → gen_root_cause → finalize → END`
   Runs in one graph invocation: risk classification (heavy model), completeness check, executive summary, root cause + CAPA. Duplicate detection runs against stored complaints as a deterministic stage after the graph.

### Groq vs mock

If `GROQ_API_KEY` is set, all agent calls go to **Groq** (`gemma2-9b-it`, `llama-3.3-70b-versatile` for the risk + root-cause reasoning steps). Without a key, a **clearly-marked rule-based mock** (logs `using rule-based MOCK LLM`) keeps the whole app functional so the full flow can be demoed — the app never crashes without a key.

**Model fallback:** `gemma2-9b-it` is the spec-mandated default, but Groq has since decommissioned that model id. When a live call is rejected because the model no longer exists, the client transparently retries once with `llama-3.1-8b-instant` (see `_MODEL_FALLBACKS` in `app/ai/llm.py`) — so a real API key still produces live LLM output, and the mock is only used when no key is configured or the API is genuinely unreachable.

## Setup & Run

Prerequisites: Python 3.11+, Node 18+, Groq API key (free at https://console.groq.com/keys). PostgreSQL is recommended and used for full CRUD/persistence in the demo environment, but **not strictly required** — the backend automatically falls back to a local `complaints.db` (SQLite) file if Postgres is unreachable or `DATABASE_URL` is unset (a clear warning is logged).

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows   (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt

cp .env.example .env            # then set GROQ_API_KEY and DATABASE_URL

alembic upgrade head            # create schema (migrations in alembic/versions/)
python -m app.seed              # optional: seed 6 sample complaints
uvicorn app.main:app --reload --port 8000
```

- API docs (OpenAPI/Swagger): **http://localhost:8000/docs**

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                     # http://localhost:3000
```

### 3. Environment variables (`backend/.env`)

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy URL — Postgres/MySQL preferred; SQLite fallback if unset or unreachable | `postgresql+psycopg2://postgres:postgres@localhost:5432/complaint_system` |
| `GROQ_API_KEY` | Groq API key (empty → mock mode) | *(empty)* |
| `GROQ_MODEL` | Default model | `gemma2-9b-it` |
| `GROQ_HEAVY_MODEL` | Heavier reasoning model | `llama-3.3-70b-versatile` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000,http://127.0.0.1:3000` |

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/complaints` | List + filter (search, status, category, risk) |
| POST | `/api/complaints` | Create complaint (auto `CMP-YYYYMMDD-NNNN` number) |
| GET | `/api/complaints/{id}` | Detail with AI results + status history |
| PATCH | `/api/complaints/{id}` | Update status / assignment / notes (writes status history) |
| DELETE | `/api/complaints/{id}` | Delete complaint |
| GET | `/api/complaints/{id}/status-history` | Status change timeline |
| POST | `/api/ai/extract` | **LangGraph extract workflow** — auto-populate form fields |
| POST | `/api/ai/assess` | **LangGraph assess workflow** — Copilot risk assessment |
| POST | `/api/ai/completeness` | Completeness checker |
| GET | `/api/ai/duplicates/{id}` | Duplicate detection for an existing complaint |
| POST | `/api/ai/analyze?complaint_id=` | Full AI analysis persisted to the record |
| POST | `/api/ai/session` | Start a conversational intake session |
| POST | `/api/ai/session/{id}/message` | Send a message (`{"text": ...}` JSON **or** a PDF file upload) — first message extracts, follow-ups amend |

## What's implemented vs. stubbed

**Implemented:** all core + bonus features, conversational intake sessions (extract → amend) with PDF upload, PostgreSQL persistence (with automatic SQLite fallback) and Alembic migrations, status history tracking, seeded sample data, agent sanity test (`backend/test_agent.py`), full CRUD, duplicate detection, complete UI.

**Stubbed / note:** without `GROQ_API_KEY` the LLM is a deterministic rule-based mock (clearly logged) — swap in a real key for live Groq output; no user auth (single-tenant demo scope); PDF attachments are text-layer only (no OCR for scanned documents); images are not accepted.

## Tests

```bash
cd backend
python test_agent.py    # runs 4 varied complaints through both LangGraph workflows
```

## Project layout

```
backend/
  app/ai/graph.py        LangGraph workflows (extract + assess)
  app/ai/llm.py          Groq client + mock fallback
  app/api/               FastAPI routers (/api/complaints, /api/ai)
  app/models/            SQLAlchemy models (Complaint, StatusHistory)
  app/schemas/           Pydantic schemas
  app/crud/              DB operations
  app/seed.py            Sample pharma complaint data
  alembic/               Migrations
frontend/
  src/pages/             ComplaintList, ComplaintForm, ComplaintDetail
  src/store/             Redux Toolkit slices (complaints, ai)
  src/services/api.js    API client
  src/styles/global.css  Inter font + design system
```

---

*Demo videos:* see `docs/DEMO_SCRIPT.md` for a scripted walkthrough of both required demo videos (frontend/API and LangGraph workflow).
