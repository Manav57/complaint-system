# SHIP CHECKLIST — PharmaCare AI Complaint Management (AIVOA Round 1)

- **Project:** PharmaCare — AI-powered pharma Customer Complaint Management System (React+Redux · FastAPI · LangGraph+Groq · Postgres/SQLite)
- **Date:** 2026-08-08 · **Deadline:** 2026-08-08 (today — ship day)
- **Deliverable:** AIVOA Round 1 submission = working app + GitHub repo URL + 2 demo videos
- **Source of truth for:** ceo / product-manager / cto / lead-dev / qa-engineer / designer / human

| Role | Owner of |
|---|---|
| CEO | final go/no-go on submission |
| Product Manager | this checklist, priorities, final status report (SC-14) |
| CTO | decisions SC-SQLITE, SC-BATCH (Decisions section) |
| Lead Dev | git secret scan, push, fresh-clone smoke test |
| QA Engineer | live Groq verification, feature regressions, video QA |
| Designer | UI pass vs DEMO_SCRIPT |
| Human | demo video recording, GitHub credentials |

---

## Master list (execution priority: a → b → c; within a, by dependency)

### (a) Blocks submission entirely

1. **SC-01 · Secret scan of git history** — (a) · lead-dev · UNCHECKED
   - AC: `git log -p` full history scanned with `grep -i "gsk_"` → zero hits; any hit reported to PM immediately (history rewrite decision); scan result noted in wrap-up.
   - Note: MUST run before any push (SC-02).

2. **SC-02 · Push repo to GitHub (create remote + URL)** — (a) · lead-dev · KNOWN-ISSUE
   - AC: `git remote -v` shows origin; `git push` to main succeeds; repo URL captured and handed to PM for submission.
   - Note: repo has real commits but NO remote — never pushed; submission requires a repo URL; needs human-provided GitHub credentials (see Human-owned items).

3. **SC-03 · Fresh-clone smoke test** — (a) · lead-dev · UNCHECKED
   - AC: fresh `git clone` of the pushed repo; README setup run top-to-bottom; backend boots on :8000, frontend on :3000; seeded complaints visible in UI.
   - Note: validates the submitted artifact, not the working directory.

4. **SC-04 · Live Groq verification (real LLM, not mock)** — (a) · qa-engineer · UNCHECKED
   - AC: ≥3 varied sample complaints (adverse event / contamination / logistics delay) through the real Groq API; backend logs show NO `using rule-based MOCK LLM`; outputs are genuinely LLM-generated (varied risk classes incl. Critical and Low, non-templated text).
   - Note: `GROQ_API_KEY` exists in backend/.env (gitignored); blocking because Video 2 must show real Groq output — gate for SC-06.

5. **SC-05 · Demo Video 1 — frontend + API + backend walkthrough** — (a) · human · KNOWN-ISSUE
   - AC: follows docs/DEMO_SCRIPT.md §Video 1 (endpoints in Swagger, list/search/filters, detail + timeline, status change, psql); 5–10 min at 1920x1080 (OBS/Loom); QA confirms file exists, plays, and covers all scripted beats; link added to README.
   - Note: no videos exist today — recording is HUMAN-OWNED (no agent can record screen video).

6. **SC-06 · Demo Video 2 — LangGraph workflow + AI form population + Copilot** — (a) · human · KNOWN-ISSUE
   - AC: follows DEMO_SCRIPT §Video 2 (graph.py/llm.py walkthrough, auto-populate, Copilot steps, ≥3 complaints, Swagger `/api/ai/assess` JSON); 5–10 min at 1080p; QA confirms REAL Groq output visible (no mock banner); link added to README.
   - Note: gate = SC-04 DONE; recording is HUMAN-OWNED.

7. **SC-07 · Resolve SQLite-fallback claim (decision SC-SQLITE)** — (a) · cto · DONE
   - AC: CTO picks IMPLEMENT (≈15-line fix in app/config.py + app/database.py) OR CORRECT-DOC (fix README + env-var table); resolution row filled in Decisions; outcome verified (fallback actually works, or README no longer claims it).
   - Note: RESOLVED via decision SC-SQLITE — fallback ALREADY implemented in HEAD (3d269cd) and verified live by CTO; backend/app/database.py `_resolve_engine()` falls back to `sqlite:///./complaints.db` with a clear logged warning when the configured DB is unreachable, and goes directly to SQLite when the URL is blank; README claims accurate; no code change needed.

8. **SC-08 · Reconcile `batch_lot_number` vs `batch_number` (decision SC-BATCH)** — (a) · cto · DONE
   - AC: canonical name decided; aligned across Pydantic schema, SQLAlchemy model, frontend payloads, README/API docs; create→detail round-trip shows batch persists and displays in UI.
   - Note: RESOLVED via decision SC-BATCH — canonical field is `batch_lot_number`, ALREADY consistent end-to-end (57 occurrences across model/schemas/crud/api/graph/llm/seed/migration/tests/frontend; zero `batch_number` in any code, payload, README, or demo doc); doc-only decision — no alembic migration or code change needed.

### (b) Required deliverable — not blocking

9. **SC-09 · Regression — core complaint management** — (b) · qa-engineer · UNCHECKED
   - AC: list + search + filters (status/category/risk) work; detail view renders; status change writes a timeline entry (New → Under Review → Investigating); edit and delete work.
   - Note: AIVOA acceptance surface — must keep working.

10. **SC-10 · Regression — AI form auto-population (LangGraph extract)** — (b) · qa-engineer · UNCHECKED
    - AC: `POST /api/ai/extract` on sample text returns complainant/product/batch/category/severity; frontend Auto-populate fills the form; works in both mock and live Groq modes.
    - Note: AIVOA acceptance surface.

11. **SC-11 · Regression — Copilot Risk Assessment (LangGraph assess)** — (b) · qa-engineer · UNCHECKED
    - AC: `POST /api/ai/assess` returns risk_level + risk_score + rationale + summary + root cause + CAPA; duplicate detection flags batch/similarity match when applicable; copilot panel in UI renders all outputs.
    - Note: AIVOA acceptance surface.

12. **SC-12 · Regression — completeness checker** — (b) · qa-engineer · UNCHECKED
    - AC: `POST /api/ai/completeness` flags missing required fields; frontend completeness banner appears on a partial form; submit blocked until complete.
    - Note: AIVOA acceptance surface.

13. **SC-13 · Regression — seeded sample data** — (b) · qa-engineer · UNCHECKED
    - AC: `python -m app.seed` creates 6 sample complaints incl. Critical adverse event and Low logistics delay; status_history seeded; complaint numbers auto-generated (`CMP-YYYYMMDD-NNNN`).
    - Note: AIVOA acceptance surface.

14. **SC-14 · Final PM status report** — (b) · product-manager · UNCHECKED
    - AC: every item's final status recorded in this checklist; blockers escalated to CEO for go/no-go; report states repo URL, both video links, and live-Groq evidence.
    - Note: wrap-up deliverable end of day.

### (c) Polish

15. **SC-15 · README accuracy pass** — (c) · product-manager · DONE
    - AC: README reflects SC-SQLITE + SC-BATCH resolutions; env-var table, API table, and "implemented vs stubbed" accurate; demo video links present.
    - Note: verified read-only against code (2026-08-08): SQLite-fallback claim CONFIRMED — database.py `_resolve_engine()` falls back to `sqlite:///./complaints.db` with a logged warning when the configured DB is unreachable and directly to SQLite on a blank URL; API table — all 11 endpoints match the actual routers (api/complaints.py + api/ai.py); env-var table matches config.py defaults + .env.example (DATABASE_URL, GROQ_API_KEY, GROQ_MODEL, GROQ_HEAVY_MODEL, CORS_ORIGINS); "implemented vs stubbed" matches repo (test_agent.py + alembic/ + seed 6 samples + no auth/attachments — confirmed); layout paths all exist; no README edits needed. Demo-video links remain pending human recording (SC-05/SC-06); README correctly points to DEMO_SCRIPT.md meanwhile.

16. **SC-16 · UI/design pass vs DEMO_SCRIPT** — (c) · designer · UNCHECKED
    - AC: risk pills (Critical/High/Medium/Low), status pills, copilot panel, Inter font match the scripted look; no layout breakage at 1080p on the Video 1 scenes.
    - Note: cosmetic-only; do not rework UI on ship day.

---

## Decisions (TBD placeholders — filled when CTO reports)

| ID | Decision | Owner | Status | Options | Impact | Resolution |
|---|---|---|---|---|---|---|
| SC-SQLITE | SQLite-fallback claim: implement or correct docs | CTO | RESOLVED | IMPLEMENT (~15-line fix in app/config.py + app/database.py) vs CORRECT-DOC (README + env table) | README truthfulness, demo credibility | IMPLEMENTED — already in HEAD (3d269cd), verified live; no change needed |
| SC-BATCH | Canonical batch field name | CTO | RESOLVED | `batch_lot_number` (API current) vs `batch_number` (some payloads/docs) | schema, model, frontend, docs, demo | RESOLVED — canonical batch_lot_number, consistent end-to-end; no changes |

- **SC-SQLITE hardening (non-blocking, optional):** config.py hard-defaults `database_url`, so the "unset" fast path in `_resolve_engine()` is unreachable in practice — the same SQLite result is reached via the connection-refused path. Changing the default to `""` is optional, not required.

---

## Human-owned items (agents cannot do these — flag prominently)

- **Demo Video 1** (SC-05): record 5–10 min, 1920x1080, OBS/Loom, per DEMO_SCRIPT §Video 1; upload + link from README. Required for submission.
- **Demo Video 2** (SC-06): record 5–10 min, 1080p, per DEMO_SCRIPT §Video 2; MUST show real Groq output (wait for SC-04 DONE); upload + link from README. Required for submission.
- **GitHub credentials** (needed by lead-dev for SC-02): provide account/token so the repo can be pushed; without this, submission has no repo URL — top blocker.

---

## Out of scope today

- **Auth spec (docs/AUTH_SPEC.md):** documented future work, NOT in today's scope — do not implement.
