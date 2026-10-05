from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.ingestion import SignalBatch, batch_digest
from app.main import app
from app.models import BusinessSignal, SignalType


def signal(signal_id: str, value: int) -> dict:
    return BusinessSignal(
        id=signal_id,
        source="demo.support",
        signal_type=SignalType.support,
        observed_at=datetime.now(timezone.utc),
        metric="open_urgent_items",
        value=value,
    ).model_dump(mode="json")


def test_ingestion_batch_returns_digest_and_evidence_linked_brief():
    payload = {
        "batch_id": "batch-001",
        "source": "demo.support",
        "connector_run_id": "run-001",
        "signals": [signal("support-1", 4)],
    }
    with TestClient(app) as client:
        response = client.post("/ingest/analyze", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["accepted_count"] == 1
    assert len(body["batch_digest"]) == 64
    assert body["brief"]["findings"][0]["evidence"][0]["signal_id"] == "support-1"


def test_batch_rejects_cross_source_signal():
    payload = {
        "batch_id": "batch-002",
        "source": "demo.support",
        "signals": [{**signal("support-2", 4), "source": "other.support"}],
    }
    with TestClient(app) as client:
        response = client.post("/ingest/analyze", json=payload)
    assert response.status_code == 422


def test_batch_rejects_duplicate_signal_ids():
    item = signal("support-3", 4)
    payload = {
        "batch_id": "batch-003",
        "source": "demo.support",
        "signals": [item, item],
    }
    with TestClient(app) as client:
        response = client.post("/ingest/analyze", json=payload)
    assert response.status_code == 422


def test_batch_digest_is_independent_of_delivery_order():
    first = SignalBatch(
        batch_id="batch-004",
        source="demo.support",
        signals=[signal("a", 4), signal("b", 5)],
    )
    second = SignalBatch(
        batch_id="batch-004",
        source="demo.support",
        signals=[signal("b", 5), signal("a", 4)],
    )
    assert batch_digest(first) == batch_digest(second)
