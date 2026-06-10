"""Campaign rule API tests."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_campaigns_empty():
    res = client.get("/api/campaigns")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_upsert_and_delete_campaign():
    payload = {
        "line_item_id": "TEST_LI_001",
        "campaign_name": "Test Campaign",
        "min_vcr": 75.0,
        "max_vcr": 89.0,
        "min_viewability": 70.0,
        "max_viewability": 85.0,
    }
    # Create
    res = client.post("/api/campaigns", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["campaign_id"] == "TEST_LI_001"
    rule_id = data["id"]

    # Toggle
    res = client.patch(f"/api/campaigns/by-id/{rule_id}/toggle")
    assert res.status_code == 200
    assert res.json()["enabled"] is False

    # Delete
    res = client.delete(f"/api/campaigns/by-id/{rule_id}")
    assert res.status_code == 200
    assert res.json()["deleted"] == rule_id


def test_settings_read_and_update():
    res = client.get("/api/settings")
    assert res.status_code == 200
    assert "min_ctr" in res.json()

    res = client.put("/api/settings", json={"min_ctr": 0.30, "max_ctr": 0.60})
    assert res.status_code == 200
    assert res.json()["min_ctr"] == 0.30
