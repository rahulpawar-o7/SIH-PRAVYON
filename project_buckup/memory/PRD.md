# PAIMANA — Predictive Intelligence & Early Warning System

## Original Problem Statement
Build a predictive intelligence layer on top of a government project monitoring portal to estimate risks, explain factors, and prioritize projects.

## Strict Constraints (user-mandated)
1. DO NOT implement real ML logic — risk scores / AI predictions are MOCKED placeholders.
2. DO NOT write new PDF extraction logic — use user-provided `extract_table6(pdf_path, reporting_month)` (`/app/backend/extract_table6.py`, pdfplumber). Do not modify.
3. PostgreSQL UPSERT for `project_monthly_history` (unique on project_code + reporting_month) so new PDF reports merge with history.

## Stack
- Frontend: React + Tailwind + Shadcn (`/app/frontend/src/App.js` — all 6 pages)
- Backend: FastAPI (`/app/backend/server.py`), psycopg → Supabase PostgreSQL (DATABASE_URL in backend/.env)
- PDF staging: Emergent Object Storage
- Pages: Home, Data Management (PDF upload), Dashboard (KPIs), Project Explorer, Project Intelligence, Early Warning

## DB Schema
- `projects`: project_code (PK), project_name, agency, ministry, sector, state, approval_start_date, original_target_doc, original_cost
- `project_monthly_history`: id, project_code (FK), reporting_month, revised_doc, revised_cost, cumulative_expenditure, physical_progress_pct (UNIQUE project_code+reporting_month)

## API Endpoints
- POST /api/upload (PDF + reporting_month → extract → UPSERT)
- GET /api/dashboard, /api/projects (search+filters), /api/projects/{code}, /api/alerts (mocked)

## Implemented (as of June 2026)
- [x] Full frontend (6 pages, responsive, graceful error states)
- [x] Backend + PostgreSQL schema + UPSERT + seed of 8 demo projects
- [x] Object storage PDF staging, extract_table6 integration
- [x] Supabase connection FIXED (user reset password; new string applied this session)
- [x] Full E2E test pass: backend 11/11 pytest, frontend all pages verified (iteration_2.json)
- [x] Fixed filter dropdown bug (App.js: filters keyed singular, plural label "All ministries")
- [x] Real PDF upload E2E VERIFIED (iteration_3): fixture generator /app/backend/tests/make_table6_pdf.py builds realistic Table-6 PDFs (months 2026-04, 2026-05); uploaded both months + re-upload → UPSERT idempotent, no dupes. 3 real-format projects added (NH-48-CB-2024, ZJT-AR-P2, RVNL-RK-BG-19); 11 projects total in DB
- [x] Trend arrows: /api/projects returns per-project trend {progress_delta, cost_delta} (latest vs prev month); Project Explorer shows green/red arrow badges (progress up = green; cost up = red). Testids: progress-trend-{code}, cost-trend-{code}
- [x] Fixed detail-page chart bug: "chart-card trend" class collided with new .trend badge CSS → removed stray class, chart bars verified

## Known/Intentional
- ML insights, risk scores, early-warning alerts are MOCKED by design.

## Backlog
- P2: CSV export of project data
- P2: Guard demo seed behind env flag for production
- P2: Surface API errors in Project Explorer instead of silent empty state
