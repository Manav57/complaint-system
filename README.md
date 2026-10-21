<div align="center">

# 🧪 PharmaCare

**An AI-native complaint management system for pharmaceutical manufacturing — structured intake, LangGraph risk assessment, and CAPA recommendations in one workflow.**

[![Build](https://img.shields.io/badge/Tests-pytest-2EA44F?style=for-the-badge&logo=pytest&logoColor=white)](#-testing)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](#-tech-stack)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](#-tech-stack)
[![React](https://img.shields.io/badge/React-Redux-61DAFB?style=for-the-badge&logo=react&logoColor=black)](#-tech-stack)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](#-architecture)
[![PRs](https://img.shields.io/badge/PRs-Welcome-6E40C9?style=for-the-badge&logo=github&logoColor=white)](#-contributing)

[Overview](#-overview) · [Features](#-key-features) · [Architecture](#-architecture) · [Quick Start](#-quick-start) · [API](#-api-surface) · [Testing](#-testing)

</div>

---

## 🎯 Overview

Pharma quality teams receive complaints as free text — emails, PDFs, portal messages — and must classify risk, spot duplicates, and propose corrective actions under regulatory pressure. **PharmaCare turns that into a guided workflow.**

A complaint is captured through a structured form (or auto-populated by an LLM from a pasted message), then analysed by **LangGraph workflows** that return a risk level with rationale, a summary, duplicate matches, a probable root cause and a CAPA recommendation. Every AI result is persisted alongside the complaint and its status history.

Built for the **AIVOA Round 1 AI Product Engineer** assessment, against the mandated stack.

---

## ✨ Key Features

### Core workflow
- **Structured intake** — complainant, product/batch/lot, category, severity and description, with auto-generated `CMP-YYYYMMDD-NNNN` numbers.
- **AI form autofill** — the `extract` LangGraph workflow maps free text onto form fields.
- **Risk assessment Copilot** — classifies **Low / Medium / High / Critical** with rationale, summary, duplicate detection, root-cause suggestion and CAPA recommendation.
- **Complaint management** — list with search + filters (status, category, risk), detail view, inline edit, delete.
- **Status timeline** — every change writes to a status-history table and renders as a timeline.

### Conversational intake
- **Session-based chat** (`POST /api/ai/session` + `/session/{id}/message`) that extracts fields from a pasted message and replies in natural language.
- **Conversational corrections** — follow-up messages run an `amend` workflow that changes **only** the fields you mention and preserves everything else.
- **PDF intake** — text-layer extraction with `pypdf`, fed through the same extract/amend logic (no second pipeline).

### Bonus AI capabilities (all implemented)
1. Completeness checker that flags missing required fields before submit
2. Risk classification integrated into the Copilot panel
3. Complaint summary generation
4. Duplicate detection (batch match + description similarity)
5. Root-cause recommendation
6. CAPA recommendation

---

## 🏗️ Architecture

```mermaid
flowchart LR
    subgraph Client
        R[React + Redux<br/>Vite dev server :3000]
    end

    subgraph API["FastAPI :8000"]
        C[/api/complaints/]
        A[/api/ai/]
    end

    subgraph LG["LangGraph workflows (app/ai/graph.py)"]
        EX[extract]
        AM[amend]
        AS[assess]
        CP[completeness]
    end

    G[Groq LLM client<br/>app/ai/llm.py]
    DB[(PostgreSQL<br/>SQLite fallback)]
    PDF[pypdf text layer]

    R --> C
    R --> A
    A --> LG
    LG --> G
    PDF --> A
    C --> DB
    A --> DB
```

### LangGraph workflows (`backend/app/ai/graph.py`)

| Workflow | Trigger | Output |
| --- | --- | --- |
| `extract` | New complaint / first chat message | Structured fields from free text |
| `amend` | Follow-up chat message | Only the mentioned fields changed |
| `assess` | Copilot panel | Risk level, rationale, summary, duplicates, root cause, CAPA |
| `completeness` | Pre-submit check | Missing required fields |

### Groq vs. mock
`gemma2-9b-it` is the spec-mandated default, but Groq has since decommissioned that model id. When a live call is rejected because the model no longer exists, the client transparently retries once with `llama-3.1-8b-instant` (`_MODEL_FALLBACKS` in `app/ai/llm.py`). A mock path is used **only** when no API key is configured or the API is genuinely unreachable — so the app is fully demoable offline.

---

## 🧰 Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React · Redux · Vite · plain CSS (Google "Inter") |
| Backend | FastAPI 0.115 · Uvicorn · Pydantic v2 |
| Agent orchestration | LangGraph 0.2 · langchain-groq · langchain-core |
| LLM | Groq (`gemma2-9b-it` → `llama-3.1-8b-instant` fallback, `llama-3.3-70b-versatile` for heavy reasoning) |
| Data | SQLAlchemy 2 · Alembic migrations · PostgreSQL (SQLite fallback) |
| Documents | pypdf (text-layer extraction) · reportlab |
| Tests | pytest |

---

## 🚀 Quick Start

**Prerequisites:** Python 3.11+, Node 18+, and a free [Groq API key](https://console.groq.com/keys). PostgreSQL is recommended; the backend falls back to a local `complaints.db` (SQLite) if `DATABASE_URL` is unset or unreachable.

### 1 · Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt

cp .env.example .env              # then set GROQ_API_KEY and DATABASE_URL

alembic upgrade head              # create the schema
python -m app.seed                # optional: 6 sample complaints
uvicorn app.main:app --reload --port 8000
```

→ Swagger UI: **http://localhost:8000/docs**

### 2 · Frontend

```bash
cd frontend
npm install
npm run dev                       # http://localhost:3000
```

### 3 · Environment variables (`backend/.env`)

| Variable | Description | Default |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy URL; SQLite fallback when unset/unreachable | `postgresql+psycopg2://postgres:postgres@localhost:5432/complaint_system` |
| `GROQ_API_KEY` | Groq key; empty ⇒ mock mode | *(empty)* |
| `GROQ_MODEL` | Default model | `gemma2-9b-it` |
| `GROQ_HEAVY_MODEL` | Heavier reasoning model | `llama-3.3-70b-versatile` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000,http://127.0.0.1:3000` |

---

## 🔌 API Surface

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/complaints` | List + filter (search, status, category, risk) |
| `POST` | `/api/complaints` | Create complaint (auto number) |
| `GET` | `/api/complaints/{id}` | Detail with AI results + status history |
| `PATCH` | `/api/complaints/{id}` | Update status / assignment / notes |
| `DELETE` | `/api/complaints/{id}` | Delete complaint |
| `GET` | `/api/complaints/{id}/status-history` | Status timeline |
| `POST` | `/api/ai/extract` | LangGraph **extract** — autofill form |
| `POST` | `/api/ai/assess` | LangGraph **assess** — risk Copilot |
| `POST` | `/api/ai/completeness` | Completeness checker |
| `GET` | `/api/ai/duplicates/{id}` | Duplicate detection |
| `POST` | `/api/ai/analyze?complaint_id=` | Full analysis, persisted |
| `POST` | `/api/ai/session` | Start a conversational session |
| `POST` | `/api/ai/session/{id}/message` | Message (`{"text": ...}`) **or** PDF upload |

---

## 🧪 Testing

```bash
cd backend
pytest -q            # 95 tests across tests/ (API, graph, LLM, session, config)
python test_agent.py # workflow sanity script: 4 varied complaints through both graphs
```

`pytest.ini` points `testpaths` at `tests/`.

---

## ⚖️ Implemented vs. intentionally stubbed

- **Implemented:** all core + bonus features, conversational sessions (extract → amend) with PDF upload, PostgreSQL persistence with automatic SQLite fallback, Alembic migrations, status-history tracking, seeded sample data, full CRUD, duplicate detection and the complete UI.
- **Mock path:** without `GROQ_API_KEY` the LLM is a deterministic rule-based mock (clearly logged); add a real key for live Groq output.
- **Not in scope:** user authentication (single-tenant demo), OCR for scanned PDFs, and image attachments.

---

## 📁 Project Structure

```text
complaint-system/
├── backend/
│   ├── app/
│   │   ├── ai/         # LangGraph graphs (extract, amend, assess) + Groq client
│   │   ├── api/        # FastAPI routers: complaints.py, ai.py
│   │   ├── crud/       # persistence helpers
│   │   ├── models/     # SQLAlchemy models (Complaint, StatusHistory)
│   │   ├── schemas/    # Pydantic models
│   │   ├── services/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── seed.py     # 6 sample complaints
│   │   └── main.py     # FastAPI app + /health
│   ├── alembic/        # migrations
│   ├── tests/          # pytest suite (95 tests)
│   ├── test_agent.py   # workflow sanity script
│   └── requirements.txt
├── frontend/
│   └── src/            # React + Redux UI, Copilot panel, chat intake
└── docs/               # sample complaint PDFs
```

## 🤝 Contributing

1. Fork the repo
2. `git checkout -b feat/your-feature`
3. `git commit -m "feat: your feature"`
4. Open a Pull Request

Please keep the AI results **persisted and auditable** — that is a design invariant, not an implementation detail.

---

<div align="center">

**⭐ If you find this project useful, consider giving it a star!**

[github.com/Manav57/complaint-system](https://github.com/Manav57/complaint-system)

<sub>Built by [Manav Patidar](https://github.com/Manav57)</sub>

</div>
