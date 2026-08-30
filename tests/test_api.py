from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_demo_brief_has_evidence_linked_findings():
    response = client.get("/demo/brief")
    assert response.status_code == 200
    payload = response.json()
    assert payload["signal_count"] == 5
    assert len(payload["findings"]) >= 4
    assert all(finding["evidence"] for finding in payload["findings"])
    assert len(payload["action_queue"]) >= 2


def test_analyze_accepts_normalized_signals():
    payload = [
        {
            "id": "calendar-1",
            "source": "test.calendar",
            "signal_type": "calendar",
            "observed_at": "2026-08-29T12:00:00Z",
            "metric": "unassigned_customer_appointments",
            "value": 3,
            "unit": "appointments",
            "metadata": {},
        }
    ]
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["findings"][0]["severity"] == "high"
    assert data["findings"][0]["evidence"][0]["signal_id"] == "calendar-1"
