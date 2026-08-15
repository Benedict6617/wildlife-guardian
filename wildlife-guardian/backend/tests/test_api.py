"""
Smoke tests for the core API surface. Run with `pytest` from backend/.
Uses a throwaway SQLite file and reseeds it fresh for the test session.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = "sqlite:///./test_wildlife_guardian.db"

import pytest
from fastapi.testclient import TestClient

from app.seed import seed
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    seed()
    yield
    db_path = "./test_wildlife_guardian.db"
    if os.path.exists(db_path):
        os.remove(db_path)


def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_species():
    resp = client.get("/api/v1/species")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 4
    assert any(s["common_name"] == "African Elephant" for s in data)


def test_list_animals_and_detail():
    resp = client.get("/api/v1/animals")
    assert resp.status_code == 200
    animals = resp.json()
    assert len(animals) > 0

    animal_id = animals[0]["id"]
    detail = client.get(f"/api/v1/animals/{animal_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == animal_id


def test_animal_movement_prediction():
    animals = client.get("/api/v1/animals").json()
    animal_id = animals[0]["id"]
    resp = client.get(f"/api/v1/animals/{animal_id}/predict")
    assert resp.status_code == 200
    body = resp.json()
    assert "predicted_latitude" in body
    assert 0 <= body["confidence_pct"] <= 100


def test_live_tracking_positions():
    resp = client.get("/api/v1/tracking/live")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_alerts_list_and_status_update():
    resp = client.get("/api/v1/alerts")
    assert resp.status_code == 200
    alerts = resp.json()
    assert len(alerts) > 0

    alert_id = alerts[0]["id"]
    patch = client.patch(f"/api/v1/alerts/{alert_id}/status", json={"status": "acknowledged"})
    assert patch.status_code == 200
    assert patch.json()["status"] == "acknowledged"


def test_generate_patrol_route():
    zones = client.get("/api/v1/habitat-zones").json()
    zone_id = zones[0]["id"]
    payload = {
        "zone_id": zone_id,
        "scheduled_date": "2026-09-01T06:00:00",
        "team_size": 3,
        "max_waypoints": 4,
    }
    resp = client.post("/api/v1/patrols/generate", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["zone_id"] == zone_id
    assert len(body["waypoints"]) <= 4


def test_sms_broadcast():
    zones = client.get("/api/v1/habitat-zones").json()
    payload = {
        "category": "poaching_warning",
        "message": "Test broadcast message for automated tests.",
        "zone_id": zones[0]["id"],
    }
    resp = client.post("/api/v1/sms-alerts/broadcast", json=payload)
    assert resp.status_code == 201
    assert resp.json()["recipient_count"] >= 0


def test_dashboard_summary():
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_animals_tracked"] > 0


def test_fundraising_allocation_breakdown():
    resp = client.get("/api/v1/fundraising/allocation-breakdown")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


def test_cites_permit_pdf_generation():
    permits = client.get("/api/v1/cites-permits").json()
    assert len(permits) > 0
    permit_id = permits[0]["id"]
    resp = client.get(f"/api/v1/cites-permits/{permit_id}/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
