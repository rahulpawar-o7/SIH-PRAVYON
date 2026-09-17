import pytest
import os
import io
from fastapi.testclient import TestClient
from server import app, init_db, DB_PATH

@pytest.fixture(autouse=True)
def setup_test_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    yield
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

client = TestClient(app)

def test_root():
    response = client.get("/api/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_dashboard_kpis():
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "direct_data" in data
    assert data["direct_data"]["total_projects"] > 0
    assert "breakdowns" in data
    assert "ministry" in data["breakdowns"]

def test_projects_list():
    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    assert len(data["projects"]) > 0

def test_project_detail():
    # Fetch first project code
    list_res = client.get("/api/projects")
    code = list_res.json()["projects"][0]["project_code"]
    
    detail_res = client.get(f"/api/projects/{code}")
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["project"]["project_code"] == code
    assert "monthly_history" in data
    assert "ml_intelligence" in data

def test_alerts_endpoint():
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert data["total_alerts"] > 0

def test_upload_endpoint():
    # Test uploading a dummy txt/pdf file
    dummy_pdf = io.BytesIO(b"Dummy PDF content for PAIMANA report testing")
    response = client.post(
        "/api/upload",
        files={"file": ("test_report.pdf", dummy_pdf, "application/pdf")},
        data={"reporting_month": "2026-09"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["history_records_upserted"] > 0
