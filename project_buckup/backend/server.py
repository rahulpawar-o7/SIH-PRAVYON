
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone

import pandas as pd
import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from extract_table6 import extract_table6

load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required")

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def store_pdf(data: bytes, content_type: str):
    path = f"{uuid.uuid4()}.pdf"
    with open(os.path.join(UPLOAD_DIR, path), "wb") as f:
        f.write(data)
    return {"path": path}

app = FastAPI(title="PRAVYON Predictive Intelligence API")
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
api = APIRouter(prefix="/api")

def db():
    return psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row)

def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS projects (
            project_code TEXT PRIMARY KEY, project_name TEXT NOT NULL, agency TEXT, ministry TEXT,
            sector TEXT, state TEXT, approval_start_date TEXT, original_target_doc TEXT, original_cost NUMERIC
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS project_monthly_history (
            id BIGSERIAL PRIMARY KEY, project_code TEXT REFERENCES projects(project_code) ON DELETE CASCADE,
            reporting_month TEXT NOT NULL, revised_doc TEXT, revised_cost NUMERIC,
            cumulative_expenditure NUMERIC, physical_progress_pct NUMERIC, created_at TIMESTAMPTZ NOT NULL,
            UNIQUE(project_code, reporting_month)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS predictions (
            project_code TEXT PRIMARY KEY REFERENCES projects(project_code) ON DELETE CASCADE,
            prediction_date TEXT, risk_score NUMERIC, risk_category TEXT, cost_overrun_probability NUMERIC,
            time_overrun_probability NUMERIC, top_risk_factors JSONB
        )""")

init_db()

def clean_number(value, default=0.0):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    match = re.search(r"-?[\d,]+(?:\.\d+)?", str(value))
    return float(match.group(0).replace(",", "")) if match else default

@api.get("/")
def root():
    return {"status": "online", "system": "PRAVYON Predictive Intelligence API"}

@api.post("/upload")
def upload(file: UploadFile = File(...), reporting_month: str = Form(...)):
    if not re.fullmatch(r"\d{4}-\d{2}", reporting_month):
        raise HTTPException(400, "reporting_month must use YYYY-MM format")
    content = file.file.read()
    temp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    temp.write(content)
    temp.close()
    try:
        frame = extract_table6(temp.name, reporting_month)
        count = 0
        with db() as conn:
            conn.autocommit = True
            for _, row in frame.iterrows():
                code = str(row.get("project_code") or "").strip()
                if not code or code == "nan":
                    continue
                original = clean_number(row.get("original_cost_cr", row.get("original_cost")))
                revised = clean_number(row.get("revised_cost_cr", row.get("revised_cost")), original)
                conn.execute("""INSERT INTO projects (project_code,project_name,agency,ministry,sector,state,approval_start_date,original_target_doc,original_cost)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(project_code) DO UPDATE SET project_name=EXCLUDED.project_name, agency=EXCLUDED.agency, ministry=EXCLUDED.ministry, sector=EXCLUDED.sector, state=EXCLUDED.state, approval_start_date=EXCLUDED.approval_start_date, original_target_doc=EXCLUDED.original_target_doc, original_cost=EXCLUDED.original_cost""", (code, row.get("project_name") or "Infrastructure Project", row.get("agency"), row.get("ministry"), row.get("sector"), row.get("state"), row.get("approval_start_date"), row.get("target_doc") or row.get("original_target_doc"), original))
                conn.execute("""INSERT INTO project_monthly_history (project_code,reporting_month,revised_doc,revised_cost,cumulative_expenditure,physical_progress_pct,created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(project_code,reporting_month) DO UPDATE SET revised_doc=EXCLUDED.revised_doc,revised_cost=EXCLUDED.revised_cost,cumulative_expenditure=EXCLUDED.cumulative_expenditure,physical_progress_pct=EXCLUDED.physical_progress_pct,created_at=EXCLUDED.created_at""", (code, reporting_month, row.get("revised_doc"), revised, clean_number(row.get("cumulative_expenditure_cr", row.get("cumulative_expenditure"))), clean_number(row.get("physical_progress_pct")), datetime.now(timezone.utc)))
                count += 1
        return {"status": "success", "message": f"Processed report for {reporting_month}", "filename": file.filename, "projects_processed": count, "history_records_upserted": count}
    finally:
        os.unlink(temp.name)

@api.get("/dashboard")
def dashboard():
    with db() as conn:
        data = conn.execute("""WITH latest AS (SELECT DISTINCT ON (project_code) * FROM project_monthly_history ORDER BY project_code, reporting_month DESC)
            SELECT (SELECT COUNT(*) FROM projects) total_projects, (SELECT COALESCE(SUM(original_cost),0) FROM projects) total_original_cost,
            (SELECT COALESCE(SUM(revised_cost),0) FROM latest) total_revised_cost, (SELECT COALESCE(SUM(cumulative_expenditure),0) FROM latest) total_cumulative_expenditure,
            (SELECT COALESCE(AVG(physical_progress_pct),0) FROM latest) average_physical_progress_pct""").fetchone()
        ministry = conn.execute("SELECT ministry, COUNT(*)::int AS count FROM projects GROUP BY ministry ORDER BY count DESC").fetchall()
        sector = conn.execute("SELECT sector, COUNT(*)::int AS count FROM projects GROUP BY sector ORDER BY count DESC").fetchall()
        months = conn.execute("SELECT DISTINCT reporting_month FROM project_monthly_history ORDER BY reporting_month DESC").fetchall()
    original = float(data["total_original_cost"]); revised = float(data["total_revised_cost"])
    direct = {k: float(v) if k != "total_projects" else v for k, v in data.items()}
    direct["cost_variance_pct"] = round((revised - original) / original * 100, 2) if original else 0
    return {"direct_data": direct, "breakdowns": {"ministry": ministry, "sector": sector}, "processed_months": [m["reporting_month"] for m in months]}

@api.get("/projects")
def projects(search: str = Query(""), ministry: str = Query(""), sector: str = Query(""), state: str = Query(""), risk_level: str = Query(""), page: int = Query(1), page_size: int = Query(50)):
    with db() as conn:
        clauses = ["1=1"]; params = []
        if search: clauses.append("(p.project_code ILIKE %s OR p.project_name ILIKE %s OR p.agency ILIKE %s)"); params += [f"%{search}%"] * 3
        for field, value in (("ministry", ministry), ("sector", sector), ("state", state)):
            if value: clauses.append(f"p.{field}=%s"); params.append(value)
        if risk_level: clauses.append("COALESCE(pr.risk_category,'Placeholder')=%s"); params.append(risk_level)
        base_query = f"""WITH ranked AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY project_code ORDER BY reporting_month DESC) rn FROM project_monthly_history),
            latest AS (SELECT * FROM ranked WHERE rn=1), prev AS (SELECT * FROM ranked WHERE rn=2)
            SELECT p.*, latest.reporting_month, latest.revised_cost, latest.cumulative_expenditure, latest.physical_progress_pct, prev.physical_progress_pct AS prev_progress_pct, prev.revised_cost AS prev_revised_cost, pr.risk_score, pr.risk_category FROM projects p LEFT JOIN latest ON latest.project_code=p.project_code LEFT JOIN prev ON prev.project_code=p.project_code LEFT JOIN predictions pr ON pr.project_code=p.project_code WHERE {' AND '.join(clauses)} ORDER BY p.project_code"""
        total_count = conn.execute(f"SELECT COUNT(*) c FROM ({base_query}) sub", params).fetchone()["c"]
        rows = conn.execute(base_query + " LIMIT %s OFFSET %s", params + [page_size, (page - 1) * page_size]).fetchall()
        filters = {key: [r[key] for r in conn.execute(f"SELECT DISTINCT {key} FROM projects WHERE {key} IS NOT NULL ORDER BY {key}").fetchall()] for key in ("ministry", "sector", "state")}
    def trend(r):
        progress = round(float(r["physical_progress_pct"]) - float(r["prev_progress_pct"]), 1) if r["physical_progress_pct"] is not None and r["prev_progress_pct"] is not None else None
        cost = round(float(r["revised_cost"]) - float(r["prev_revised_cost"]), 1) if r["revised_cost"] is not None and r["prev_revised_cost"] is not None else None
        return {"progress_delta": progress, "cost_delta": cost}
    return {"count": total_count, "page": page, "page_size": page_size, "projects": [{**r, "trend": trend(r), "ml_intelligence": {"status": "OK" if r["risk_category"] else "PLACEHOLDER — model not connected", "risk_score": r["risk_score"], "risk_category": r["risk_category"]}} for r in rows], "filters": filters}
@api.get("/projects/{project_code}")
def project_detail(project_code: str):
    with db() as conn:
        project = conn.execute("SELECT * FROM projects WHERE project_code=%s", (project_code,)).fetchone()
        if not project: raise HTTPException(404, "Project not found")
        history = conn.execute("SELECT reporting_month,revised_doc,revised_cost,cumulative_expenditure,physical_progress_pct,created_at FROM project_monthly_history WHERE project_code=%s ORDER BY reporting_month", (project_code,)).fetchall()
        prediction = conn.execute("SELECT prediction_date,risk_score,risk_category,cost_overrun_probability,time_overrun_probability,top_risk_factors FROM predictions WHERE project_code=%s", (project_code,)).fetchone()
    return {"project": project, "monthly_history": history, "ml_intelligence": prediction or {"status": "PLACEHOLDER — model not connected", "message": "Risk score and explanation will be supplied by the ML service."}}

@api.get("/alerts")
def alerts():
    with db() as conn:
        rows = conn.execute("""
            SELECT p.project_code, p.project_name, p.ministry, pr.risk_score, pr.risk_category, pr.top_risk_factors
            FROM predictions pr JOIN projects p ON p.project_code = pr.project_code
            WHERE pr.risk_category IN ('High','Medium') ORDER BY pr.risk_score DESC
        """).fetchall()
        counts = {"High": 0, "Medium": 0, "Low": 0}
        for r in conn.execute("SELECT risk_category, COUNT(*) c FROM predictions GROUP BY risk_category").fetchall():
            counts[r["risk_category"]] = r["c"]
    return {"total_alerts": len(rows), "high_risk_count": counts["High"], "medium_risk_count": counts["Medium"],
            "low_risk_count": counts["Low"], "alerts": rows}

app.include_router(api)
