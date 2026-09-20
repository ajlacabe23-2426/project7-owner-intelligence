"""Human-in-the-loop feedback stays auditable, idempotent and local/demo-only."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def support_signal(signal_id: str, observed_at: datetime, *, value: int = 4, entity: str = "queue-a") -> dict:
    return {
        "id": signal_id,
        "source": "synthetic.support",
        "signal_type": "support",
        "observed_at": observed_at.isoformat(),
        "metric": "open_urgent_items",
        "value": value,
        "entity_ref": entity,
        "metadata": {},
    }


def create_episode(monkeypatch, tmp_path):
    monkeypatch.setenv("OWNER_INTELLIGENCE_DB_PATH", str(tmp_path / "feedback.db"))
    response = client.post("/analyze/episodes", json=[
        support_signal("before-action", datetime.now(timezone.utc) - timedelta(minutes=1))
    ])
    assert response.status_code == 200, response.text
    return response.json()["findings"][0]["episode_id"]


def test_disposition_is_persistent_idempotent_and_does_not_resolve_episode(monkeypatch, tmp_path):
    episode_id = create_episode(monkeypatch, tmp_path)
    url = f"/episodes/{episode_id}/dispositions"
    payload = {"event_id": "decision-1", "status": "acted", "reason_code": "assigned-owner"}
    first = client.post(url, json=payload)
    replay = client.post(url, json=payload)
    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    feedback = client.get(f"/episodes/{episode_id}/feedback")
    assert feedback.status_code == 200
    assert len(feedback.json()["dispositions"]) == 1
    assert feedback.json()["dispositions"][0]["reason_code"] == "assigned-owner"
    assert feedback.json()["episode"]["current_status"] == "open"
    assert feedback.json()["outcomes"] == []


def test_conflicting_event_id_returns_409_without_overwrite(monkeypatch, tmp_path):
    episode_id = create_episode(monkeypatch, tmp_path)
    url = f"/episodes/{episode_id}/dispositions"
    first = {"event_id": "decision-1", "status": "acted", "reason_code": "assigned-owner"}
    assert client.post(url, json=first).status_code == 201
    changed = {**first, "status": "dismissed"}
    response = client.post(url, json=changed)
    assert response.status_code == 409
    assert client.get(f"/episodes/{episode_id}/feedback").json()["dispositions"][0]["status"] == "acted"


def test_outcome_requires_acted_decision_and_new_matching_post_action_observation(monkeypatch, tmp_path):
    episode_id = create_episode(monkeypatch, tmp_path)
    feedback_url = f"/episodes/{episode_id}/feedback"
    decision_url = f"/episodes/{episode_id}/dispositions"
    outcome_url = f"/episodes/{episode_id}/outcomes"
    assert client.post(decision_url, json={
        "event_id": "defer-1", "status": "deferred", "reason_code": "awaiting-review"
    }).status_code == 201
    observation = support_signal("after-action", datetime.now(timezone.utc) + timedelta(seconds=2), value=1)
    outcome = {"event_id": "outcome-1", "disposition_event_id": "defer-1", "signal": observation}
    assert client.post(outcome_url, json=outcome).status_code == 409

    assert client.post(decision_url, json={
        "event_id": "act-1", "status": "acted", "reason_code": "assigned-owner"
    }).status_code == 201
    outcome["disposition_event_id"] = "act-1"
    assert client.post(outcome_url, json=outcome).status_code == 201
    assert client.post(outcome_url, json=outcome).status_code == 201
    feedback = client.get(feedback_url).json()
    assert len(feedback["outcomes"]) == 1
    assert feedback["outcomes"][0]["interpretation"] == "observation-only"
    assert feedback["outcomes"][0]["signal"]["id"] == "after-action"
    assert "not proof" in feedback["interpretation_note"]
    assert feedback["episode"]["current_status"] == "open"


def test_outcome_rejects_wrong_entity_old_or_reused_observation(monkeypatch, tmp_path):
    episode_id = create_episode(monkeypatch, tmp_path)
    assert client.post(f"/episodes/{episode_id}/dispositions", json={
        "event_id": "act-1", "status": "acted", "reason_code": "assigned-owner"
    }).status_code == 201
    url = f"/episodes/{episode_id}/outcomes"
    signal = support_signal("fresh-outcome", datetime.now(timezone.utc) + timedelta(seconds=2))
    base = {"event_id": "result-1", "disposition_event_id": "act-1", "signal": signal}
    assert client.post(url, json={**base, "signal": {**signal, "entity_ref": "other-queue"}}).status_code == 409
    assert client.post(url, json={**base, "signal": {**signal, "observed_at": "2025-01-01T00:00:00Z"}}).status_code == 409
    assert client.post(url, json={**base, "signal": {**signal, "id": "before-action"}}).status_code == 409
    assert client.get(f"/episodes/{episode_id}/feedback").json()["outcomes"] == []


def test_unknown_episode_and_invalid_payload_do_not_create_feedback(monkeypatch, tmp_path):
    monkeypatch.setenv("OWNER_INTELLIGENCE_DB_PATH", str(tmp_path / "no-episode.db"))
    assert client.get("/episodes/nonexistent/feedback").status_code == 404
    assert client.post("/episodes/nonexistent/dispositions", json={
        "event_id": "one", "status": "acted", "reason_code": "assigned-owner"
    }).status_code == 404
    assert client.post("/episodes/nonexistent/outcomes", json={
        "event_id": "two",
        "disposition_event_id": "one",
        "signal": support_signal("s", datetime.now(timezone.utc)),
    }).status_code == 404
    assert client.post("/episodes/nonexistent/dispositions", json={
        "event_id": "invalid", "status": "invented", "reason_code": "test"
    }).status_code == 422


def test_feedback_persists_across_repeated_reads_without_changing_action_queue(monkeypatch, tmp_path):
    episode_id = create_episode(monkeypatch, tmp_path)
    before = client.get(f"/episodes/{episode_id}/feedback").json()
    assert client.post(f"/episodes/{episode_id}/dispositions", json={
        "event_id": "decision-1", "status": "dismissed", "reason_code": "false-positive"
    }).status_code == 201
    after = client.get(f"/episodes/{episode_id}/feedback").json()
    assert len(after["dispositions"]) == 1
    assert before["episode"]["recurrence_count"] == after["episode"]["recurrence_count"]
    assert before["episode"]["current_status"] == after["episode"]["current_status"]
