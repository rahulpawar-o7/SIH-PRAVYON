"""PAIMANA backend API tests"""
import io
import os

import pytest
import requests
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://risk-forecast-6.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def s():
    return requests.Session()


# ---------- Health ----------
def test_root(s):
    r = s.get(f"{API}/")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "online"


# ---------- Dashboard ----------
def test_dashboard(s):
    r = s.get(f"{API}/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert "direct_data" in data and "breakdowns" in data and "processed_months" in data
    dd = data["direct_data"]
    for key in ("total_projects", "total_original_cost", "total_revised_cost",
                "total_cumulative_expenditure", "average_physical_progress_pct", "cost_variance_pct"):
        assert key in dd
    assert dd["total_projects"] >= 8
    assert isinstance(data["breakdowns"]["ministry"], list)
    assert isinstance(data["breakdowns"]["sector"], list)


# ---------- Projects list ----------
def test_projects_list(s):
    r = s.get(f"{API}/projects")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 8
    assert len(data["projects"]) == data["count"]
    p = data["projects"][0]
    for key in ("project_code", "project_name", "ml_intelligence"):
        assert key in p
    assert "ministry" in data["filters"]


def test_projects_search(s):
    r = s.get(f"{API}/projects", params={"search": "PRJ-2026-001"})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert any(p["project_code"] == "PRJ-2026-001" for p in data["projects"])


def test_projects_filter_ministry(s):
    r = s.get(f"{API}/projects", params={"ministry": "Ministry of Railways"})
    assert r.status_code == 200
    data = r.json()
    for p in data["projects"]:
        assert p["ministry"] == "Ministry of Railways"


# ---------- Project detail ----------
def test_project_detail(s):
    r = s.get(f"{API}/projects/PRJ-2026-001")
    assert r.status_code == 200
    data = r.json()
    assert data["project"]["project_code"] == "PRJ-2026-001"
    assert isinstance(data["monthly_history"], list)
    assert len(data["monthly_history"]) >= 1
    assert "ml_intelligence" in data


def test_project_detail_404(s):
    r = s.get(f"{API}/projects/DOES-NOT-EXIST-XYZ")
    assert r.status_code == 404


# ---------- Alerts ----------
def test_alerts(s):
    r = s.get(f"{API}/alerts")
    assert r.status_code == 200
    data = r.json()
    for key in ("total_alerts", "high_risk_count", "medium_risk_count", "low_risk_count", "alerts", "status"):
        assert key in data


# ---------- Upload ----------
def _dummy_pdf_bytes():
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(100, 750, "Dummy PDF - not a valid Table 6")
    c.showPage()
    c.save()
    return buf.getvalue()


def test_upload_invalid_month(s):
    r = s.post(f"{API}/upload",
               files={"file": ("t.pdf", _dummy_pdf_bytes(), "application/pdf")},
               data={"reporting_month": "2026/07"})
    assert r.status_code == 400


def test_upload_valid_pdf_no_table(s):
    # PDF without Table 6 should not 500; should succeed with 0 records processed
    r = s.post(f"{API}/upload",
               files={"file": ("t.pdf", _dummy_pdf_bytes(), "application/pdf")},
               data={"reporting_month": "2026-09"})
    # Accept success (graceful 0 rows) or a controlled 4xx – but must NOT be 500
    assert r.status_code != 500, f"Server crashed: {r.text[:300]}"
    if r.status_code == 200:
        data = r.json()
        assert data.get("status") == "success"
        assert data.get("projects_processed") == 0


# ---------- Real Table-6 PDF E2E ----------
import subprocess, pathlib

FIXTURE_DIR = pathlib.Path("/tmp/paimana_fixtures")
FIXTURE_DIR.mkdir(exist_ok=True)


def _make_real_pdf(month):
    out = FIXTURE_DIR / f"r_{month}.pdf"
    subprocess.check_call(["python", "tests/make_table6_pdf.py", month, str(out)],
                          cwd="/app/backend")
    return out


def test_upload_real_pdf_2026_04(s):
    pdf = _make_real_pdf("2026-04")
    with pdf.open("rb") as fh:
        r = s.post(f"{API}/upload",
                   files={"file": (pdf.name, fh, "application/pdf")},
                   data={"reporting_month": "2026-04"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "success"
    assert d["projects_processed"] == 3, f"expected 3 projects, got {d}"


def test_upload_real_pdf_2026_05_and_history(s):
    pdf = _make_real_pdf("2026-05")
    with pdf.open("rb") as fh:
        r = s.post(f"{API}/upload",
                   files={"file": (pdf.name, fh, "application/pdf")},
                   data={"reporting_month": "2026-05"})
    assert r.status_code == 200
    assert r.json()["projects_processed"] == 3

    # Verify NH-48-CB-2024 history has both months and progress_delta=4.4
    r = s.get(f"{API}/projects/NH-48-CB-2024")
    assert r.status_code == 200
    hist = r.json()["monthly_history"]
    months = [h["reporting_month"] for h in hist]
    assert "2026-04" in months and "2026-05" in months
    # month->progress
    prog = {h["reporting_month"]: float(h["physical_progress_pct"]) for h in hist}
    assert prog["2026-04"] == 48.2
    assert prog["2026-05"] == 52.6

    # Check /api/projects trend
    r = s.get(f"{API}/projects", params={"search": "NH-48-CB-2024"})
    p = r.json()["projects"][0]
    assert p["trend"]["progress_delta"] == 4.4
    # cost identical across months for this fixture -> delta 0
    assert p["trend"]["cost_delta"] in (0.0, 0)


def test_reupload_same_month_no_duplicates(s):
    # Re-upload April and confirm history row count stays same for NH-48-CB-2024
    r0 = s.get(f"{API}/projects/NH-48-CB-2024")
    before_count = sum(1 for h in r0.json()["monthly_history"] if h["reporting_month"] == "2026-04")
    assert before_count == 1
    pdf = _make_real_pdf("2026-04")
    with pdf.open("rb") as fh:
        r = s.post(f"{API}/upload",
                   files={"file": (pdf.name, fh, "application/pdf")},
                   data={"reporting_month": "2026-04"})
    assert r.status_code == 200
    r1 = s.get(f"{API}/projects/NH-48-CB-2024")
    after_count = sum(1 for h in r1.json()["monthly_history"] if h["reporting_month"] == "2026-04")
    assert after_count == 1, "UPSERT failed - duplicate row created"


def test_projects_trend_seeded(s):
    # Seeded PRJ-2026-001 should have positive progress_delta and cost_delta (3 months of history)
    r = s.get(f"{API}/projects", params={"search": "PRJ-2026-001"})
    assert r.status_code == 200
    p = r.json()["projects"][0]
    assert p["trend"]["progress_delta"] is not None
    assert p["trend"]["progress_delta"] > 0
    assert p["trend"]["cost_delta"] is not None
    assert p["trend"]["cost_delta"] > 0


def test_upload_idempotent_same_month(s):
    # Second upload of same PDF/month should also be safe (UPSERT semantics)
    payload_pdf = _dummy_pdf_bytes()
    for _ in range(2):
        r = s.post(f"{API}/upload",
                   files={"file": ("t.pdf", payload_pdf, "application/pdf")},
                   data={"reporting_month": "2026-10"})
        assert r.status_code != 500
    # Verify no duplicate months created for existing project
    r = s.get(f"{API}/projects/PRJ-2026-001")
    months = [h["reporting_month"] for h in r.json()["monthly_history"]]
    # No duplicates
    assert len(months) == len(set(months))
