import os

import pytest
import requests


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    pytest.skip("REACT_APP_BACKEND_URL is required", allow_module_level=True)
BASE_URL = BASE_URL.rstrip("/")


@pytest.fixture(scope="module")
def api_client():
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    return session


def test_root_is_online(api_client):
    response = api_client.get(f"{BASE_URL}/api/", timeout=20)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "online"
    assert body["system"] == "PAIMANA Predictive Intelligence API"


def test_dashboard_returns_direct_data_and_breakdowns(api_client):
    response = api_client.get(f"{BASE_URL}/api/dashboard", timeout=20)
    assert response.status_code == 200
    body = response.json()
    assert body["direct_data"]["total_projects"] >= 0
    assert "ministry" in body["breakdowns"]
    assert isinstance(body["processed_months"], list)


def test_projects_returns_rows_and_filters(api_client):
    response = api_client.get(f"{BASE_URL}/api/projects", timeout=20)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(body["projects"])
    assert set(body["filters"]) == {"ministry", "sector", "state"}
    assert body["projects"]
    assert body["projects"][0]["project_code"]
    assert body["projects"][0]["ml_intelligence"]["status"].startswith("PLACEHOLDER")


def test_project_detail_returns_history_and_placeholder(api_client):
    projects = api_client.get(f"{BASE_URL}/api/projects", timeout=20).json()["projects"]
    code = projects[0]["project_code"]
    response = api_client.get(f"{BASE_URL}/api/projects/{code}", timeout=20)
    assert response.status_code == 200
    body = response.json()
    assert body["project"]["project_code"] == code
    assert len(body["monthly_history"]) >= 1
    assert "status" in body["ml_intelligence"]


def test_unknown_project_is_not_found(api_client):
    response = api_client.get(f"{BASE_URL}/api/projects/TEST-NOT-FOUND", timeout=20)
    assert response.status_code == 404
    assert "Project not found" in response.text


def test_alerts_are_explicit_placeholder(api_client):
    response = api_client.get(f"{BASE_URL}/api/alerts", timeout=20)
    assert response.status_code == 200
    body = response.json()
    assert body["total_alerts"] == 0
    assert body["alerts"] == []
    assert body["status"].startswith("PLACEHOLDER")