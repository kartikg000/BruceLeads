"""Automated flow tests for BruceLeads API."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_and_setup(client):
    assert client.get("/").json()["status"] == "ok"
    assert client.get("/stats").status_code == 200
    assert client.get("/config").status_code == 200
    setup = client.get("/api/setup/status").json()
    assert "setup_complete" in setup


def test_playwright_status_reports_launch_capability(client):
    status = client.get("/api/setup/playwright-status").json()
    assert status["playwright_installed"] is True
    assert "chromium_installed" in status


def test_lead_crud_flow(client):
    created = client.post(
        "/api/leads/add",
        json={
            "business_name": "Test Lead Co",
            "email": "test@example.com",
            "website": "https://example.com",
            "source": "Manual",
        },
    )
    assert created.status_code == 200
    lead_id = created.json()["id"]

    updated = client.put(f"/api/leads/{lead_id}", json={"notes": "pytest"})
    assert updated.status_code == 200

    fetched = client.get(f"/api/leads/{lead_id}")
    assert fetched.status_code == 200
    assert fetched.json()["business_name"] == "Test Lead Co"

    deleted = client.delete(f"/api/leads/{lead_id}")
    assert deleted.status_code == 200


@patch("backend.api.scraper._run_maps_scrape")
def test_maps_scrape_endpoint(mock_scrape, client):
    mock_scrape.return_value = {
        "status": "success",
        "leads_found": 1,
        "lead_ids": ["abc12345"],
        "message": "Found 1 leads",
    }

    response = client.post(
        "/api/scrape/start",
        json={
            "query": "coffee shop",
            "location": "New Delhi",
            "max_results": 1,
            "auto_enrich": False,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_scrape.assert_called_once()


@patch("emailer.composer.EmailComposer.compose")
def test_email_generate_flow(mock_compose, client):
    from emailer.composer import EmailResult

    mock_compose.return_value = EmailResult(
        subject="Hello",
        body="Test body",
        framework="AIDA",
        success=True,
    )

    created = client.post(
        "/api/leads/add",
        json={"business_name": "Email Flow Test", "email": "flow@example.com"},
    )
    lead_id = created.json()["id"]

    generated = client.post(
        "/api/email/generate",
        json={"lead_ids": [lead_id], "framework": "AIDA"},
    )
    assert generated.status_code == 200
    assert generated.json()["status"] == "success"

    saved = client.post(
        "/api/email/save",
        json={"lead_id": lead_id, "subject": "Draft", "body": "Draft body"},
    )
    assert saved.status_code == 200

    client.delete(f"/api/leads/{lead_id}")


def test_scrape_validation(client):
    response = client.post(
        "/api/scrape/start",
        json={"query": "", "location": "Delhi", "max_results": 1},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "error"
