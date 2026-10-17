"""Synthetic investor/client demo contracts for owner intelligence.

Checks that visible findings cite synthetic inputs and no future-only
observation can create an actionable task. No production data is used.
"""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app


def test_demo_brief_sources_are_traceable_to_synthetic_inputs():
    with TestClient(app) as client:
        signals = client.get("/demo/signals")
        briefing = client.get("/demo/brief")

    assert signals.status_code == 200
    assert briefing.status_code == 200
    source_rows = signals.json()
    brief = briefing.json()
    source_ids = {signal["id"] for signal in source_rows}
    assert len(source_ids) == len(source_rows) == brief["signal_count"]
    assert all(signal["source"].startswith("synthetic.") for signal in source_rows)
    assert brief["findings"], "Demo must show an actual inspectable finding"
    assert brief["action_queue"], "Demo must show a bounded proposed next action"
    for finding in brief["findings"]:
        assert finding["evidence"], "A finding must not lack its provenance"
        for evidence in finding["evidence"]:
            assert evidence["signal_id"] in source_ids
            assert evidence["source"].startswith("synthetic.")


def test_future_only_evidence_cannot_drive_client_action_queue():
    future_signal = {
        "id": "synthetic-future-support-001",
        "source": "synthetic.client-demo",
        "signal_type": "support",
        "observed_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "metric": "open_urgent_items",
        "value": 12,
        "unit": "items",
        "entity_ref": "dummy-support-queue",
        "metadata": {},
    }

    with TestClient(app) as client:
        response = client.post("/analyze", json=[future_signal])

    assert response.status_code == 200
    payload = response.json()
    assert payload["action_queue"] == [], "Future-only evidence must not create a client action"
    assert any(
        issue["code"] == "observation.future-dated"
        and future_signal["id"] in issue["signal_ids"]
        for issue in payload["evidence_issues"]
    ), "Future-dated input must be visibly identified"
    assert all(finding["confidence"] == "blocked" for finding in payload["findings"])
