"""Integration tests for FastAPI REST API endpoints and API Key authentication."""
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.database import save_link
from app.models import Link, LinkStatus, LinkType
from datetime import datetime


client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_get_links_list():
    response = client.get("/api/links")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_link_lifecycle_and_highlights():
    # 1. Seed a test link directly
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    link = Link(
        id="api001",
        url="https://example.com/api-test",
        title="API Test Article",
        domain="example.com",
        entry_type=LinkType.ARTICLE,
        status=LinkStatus.INBOX,
        tags=["api", "test"],
        summary="Testing API endpoints",
        created_at=now,
        updated_at=now,
    )
    save_link(link)

    # 2. Get single link
    res_get = client.get("/api/links/api001")
    assert res_get.status_code == 200
    assert res_get.json()["title"] == "API Test Article"

    # 3. Patch link
    res_patch = client.patch(
        "/api/links/api001",
        json={"status": "reading", "user_notes": "API test note"}
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["status"] == "reading"
    assert res_patch.json()["user_notes"] == "API test note"

    # 4. Add highlight
    res_hl = client.post(
        "/api/links/api001/highlights",
        json={"text": "Highlighted sentence via API", "note": "Great point"}
    )
    assert res_hl.status_code == 200
    highlights = res_hl.json()["highlights"]
    assert len(highlights) == 1
    hl_id = highlights[0]["id"]

    # 5. Delete highlight
    res_del_hl = client.delete(f"/api/links/api001/highlights/{hl_id}")
    assert res_del_hl.status_code == 200
    assert len(res_del_hl.json()["highlights"]) == 0

    # 6. Delete link
    res_del = client.delete("/api/links/api001")
    assert res_del.status_code == 200
    assert res_del.json()["success"] is True


def test_briefing_endpoint():
    res = client.post("/api/briefings", json={"days": 14, "title": "API Generated Briefing"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "briefing" in data["filename"]


def test_stats_and_graph():
    res_stats = client.get("/api/stats")
    assert res_stats.status_code == 200
    assert "total_links" in res_stats.json()

    res_graph = client.get("/api/graph")
    assert res_graph.status_code == 200
    assert "nodes" in res_graph.json()
    assert "links" in res_graph.json()


def test_exports():
    res_json = client.get("/api/export/json")
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]

    res_csv = client.get("/api/export/csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]

    res_zip = client.get("/api/export/zip")
    assert res_zip.status_code == 200
    assert "application/zip" in res_zip.headers["content-type"]


def test_api_key_auth(monkeypatch):
    import app.config as cfg
    import app.routes.api as api_routes

    # Enable API key requirement
    monkeypatch.setattr(cfg, "HLIB_API_KEY", "secret-test-key-123")
    monkeypatch.setattr(api_routes, "HLIB_API_KEY", "secret-test-key-123")

    # Request without key should be rejected with 401
    res_unauth = client.post("/api/briefings", json={"days": 7})
    assert res_unauth.status_code == 401

    # Request with wrong key should be rejected with 401
    res_wrong = client.post(
        "/api/briefings",
        json={"days": 7},
        headers={"Authorization": "Bearer wrong-key"}
    )
    assert res_wrong.status_code == 401

    # Request with correct Bearer key should succeed
    res_auth = client.post(
        "/api/briefings",
        json={"days": 7},
        headers={"Authorization": "Bearer secret-test-key-123"}
    )
    assert res_auth.status_code == 200

    # Request with correct X-API-Key should succeed
    res_auth_header = client.post(
        "/api/briefings",
        json={"days": 7},
        headers={"X-API-Key": "secret-test-key-123"}
    )
    assert res_auth_header.status_code == 200
