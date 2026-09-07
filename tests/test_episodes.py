from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def support_payload(
    *,
    signal_id: str,
    value: int = 4,
    observed_at: datetime | None = None,
    source: str = "test.support",
):
    return {
        "id": signal_id,
        "source": source,
        "signal_type": "support",
        "observed_at": (observed_at or datetime.now(timezone.utc)).isoformat(),
        "metric": "open_urgent_items",
        "value": value,
        "entity_ref": "support-queue-1",
        "metadata": {},
    }


def test_episode_create_and_exact_retry_do_not_fake_recurrence(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "OWNER_INTELLIGENCE_DB_PATH", str(tmp_path / "episodes-create.db")
    )
    observed = datetime.now(timezone.utc)
    payload = support_payload(signal_id="support-1", observed_at=observed)

    first = client.post("/analyze/episodes", json=[payload])
    retry = client.post("/analyze/episodes", json=[payload])
    episodes = client.get("/episodes")

    assert first.status_code == 200
    assert first.json()["findings"][0]["episode_state"] == "new"
    assert first.json()["findings"][0]["episode_recurrence_count"] == 1
    assert retry.json()["findings"][0]["episode_state"] == "ongoing"
    assert retry.json()["findings"][0]["episode_recurrence_count"] == 1
    assert len(episodes.json()) == 1
    assert episodes.json()[0]["recurrence_count"] == 1
    assert len(episodes.json()[0]["recommendation_history"]) == 1


def test_new_supporting_observation_updates_existing_episode(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "OWNER_INTELLIGENCE_DB_PATH", str(tmp_path / "episodes-repeat.db")
    )
    observed = datetime.now(timezone.utc)
    first = support_payload(signal_id="support-1", observed_at=observed)
    second = support_payload(
        signal_id="support-2",
        value=5,
        observed_at=observed + timedelta(minutes=1),
    )

    created = client.post("/analyze/episodes", json=[first]).json()
    repeated = client.post("/analyze/episodes", json=[second]).json()

    assert repeated["findings"][0]["episode_id"] == created["findings"][0]["episode_id"]
    assert repeated["findings"][0]["episode_state"] == "ongoing"
    assert repeated["findings"][0]["episode_recurrence_count"] == 2
    episode = client.get("/episodes").json()[0]
    assert episode["recurrence_count"] == 2
    assert episode["current_status"] == "open"


def test_resolved_episode_requires_new_evidence_to_reopen(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "OWNER_INTELLIGENCE_DB_PATH", str(tmp_path / "episodes-reopen.db")
    )
    observed = datetime.now(timezone.utc)
    original = support_payload(signal_id="support-1", observed_at=observed)
    created = client.post("/analyze/episodes", json=[original]).json()
    episode_id = created["findings"][0]["episode_id"]

    resolved = client.post(
        f"/episodes/{episode_id}/resolve",
        json={"reason_code": "operator.confirmed-resolved"},
    )
    replay = client.post("/analyze/episodes", json=[original])

    assert resolved.status_code == 200
    assert resolved.json()["current_status"] == "resolved"
    assert resolved.json()["resolution_timestamp"] is not None
    assert resolved.json()["resolution_reason_code"] == "operator.confirmed-resolved"
    assert replay.json()["findings"][0]["episode_state"] == "resolved"
    assert replay.json()["findings"][0]["episode_recurrence_count"] == 1
    assert replay.json()["action_queue"] == []

    new_evidence = support_payload(
        signal_id="support-2",
        value=6,
        observed_at=observed + timedelta(minutes=2),
    )
    reopened = client.post("/analyze/episodes", json=[new_evidence])
    episode = client.get("/episodes").json()[0]

    assert reopened.json()["findings"][0]["episode_state"] == "reopened"
    assert reopened.json()["findings"][0]["episode_recurrence_count"] == 2
    assert episode["current_status"] == "open"
    assert episode["resolution_timestamp"] is None
    assert episode["resolution_reason_code"] is None
    assert episode["reopen_count"] == 1


def test_conflicting_blocked_evidence_does_not_mutate_episode_memory(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "OWNER_INTELLIGENCE_DB_PATH", str(tmp_path / "episodes-conflict.db")
    )
    observed = datetime.now(timezone.utc)
    left = support_payload(
        signal_id="left", value=4, observed_at=observed, source="support.a"
    )
    right = support_payload(
        signal_id="right", value=7, observed_at=observed, source="support.b"
    )

    response = client.post("/analyze/episodes", json=[left, right])
    findings = response.json()["findings"]

    assert response.status_code == 200
    assert {finding["confidence"] for finding in findings} == {"blocked"}
    assert all(finding["episode_id"] is None for finding in findings)
    assert response.json()["action_queue"] == []
    assert client.get("/episodes").json() == []


def test_resolving_unknown_episode_returns_404(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "OWNER_INTELLIGENCE_DB_PATH", str(tmp_path / "episodes-missing.db")
    )
    response = client.post(
        "/episodes/not-real/resolve",
        json={"reason_code": "operator.confirmed-resolved"},
    )
    assert response.status_code == 404
