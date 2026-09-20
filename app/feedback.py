"""Local/demo-only operator feedback and post-action outcome observations.

This module records human decisions without pretending correlation proves causation.
It deliberately does not change finding rules, episode resolution, or priorities.
There is no authentication or tenant isolation: never serve this API with real data.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from app.episodes import EpisodeNotFound, _connect, _row_to_episode, initialize_episode_database
from app.models import (
    EpisodeFeedback,
    OperatorDisposition,
    OperatorDispositionRequest,
    OutcomeObservation,
    OutcomeObservationRequest,
)


class FeedbackConflict(ValueError):
    """An event ID was reused with different content, or an outcome is ineligible."""


def initialize_feedback_database() -> None:
    initialize_episode_database()
    with _connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS operator_feedback (
                event_id TEXT PRIMARY KEY,
                episode_id TEXT NOT NULL,
                event_type TEXT NOT NULL CHECK (event_type IN ('disposition', 'outcome')),
                recorded_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_operator_feedback_episode "
            "ON operator_feedback (episode_id, recorded_at, event_id)"
        )


def _episode_row(connection: sqlite3.Connection, episode_id: str) -> sqlite3.Row:
    row = connection.execute(
        "SELECT * FROM finding_episodes WHERE episode_id = ?", (episode_id,)
    ).fetchone()
    if row is None:
        raise EpisodeNotFound("Finding episode was not found.")
    return row


def _stored_or_conflict(
    connection: sqlite3.Connection, event_id: str, event_type: str,
    expected: dict[str, object],
) -> dict[str, object] | None:
    row = connection.execute(
        "SELECT event_type, payload_json FROM operator_feedback WHERE event_id = ?",
        (event_id,),
    ).fetchone()
    if row is None:
        return None
    payload = json.loads(row["payload_json"])
    if row["event_type"] != event_type or payload != expected:
        raise FeedbackConflict("Event ID already exists with different content.")
    return payload


def record_disposition(
    episode_id: str, request: OperatorDispositionRequest
) -> OperatorDisposition:
    initialize_feedback_database()
    with _connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _episode_row(connection, episode_id)
        expected = {
            "event_id": request.event_id,
            "episode_id": episode_id,
            "status": request.status,
            "reason_code": request.reason_code,
        }
        stored = _stored_or_conflict(connection, request.event_id, "disposition", expected)
        if stored is not None:
            row = connection.execute(
                "SELECT recorded_at FROM operator_feedback WHERE event_id = ?",
                (request.event_id,),
            ).fetchone()
            return OperatorDisposition.model_validate({**stored, "recorded_at": row["recorded_at"]})
        recorded_at = datetime.now(timezone.utc).isoformat()
        connection.execute(
            "INSERT INTO operator_feedback VALUES (?, ?, 'disposition', ?, ?)",
            (request.event_id, episode_id, recorded_at, json.dumps(expected, sort_keys=True)),
        )
        return OperatorDisposition.model_validate({**expected, "recorded_at": recorded_at})


def record_outcome(
    episode_id: str, request: OutcomeObservationRequest
) -> OutcomeObservation:
    initialize_feedback_database()
    with _connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        episode = _row_to_episode(_episode_row(connection, episode_id))
        expected = {
            "event_id": request.event_id,
            "episode_id": episode_id,
            "disposition_event_id": request.disposition_event_id,
            "signal": request.signal.model_dump(mode="json"),
            "interpretation": "observation-only",
        }
        stored = _stored_or_conflict(connection, request.event_id, "outcome", expected)
        if stored is not None:
            row = connection.execute(
                "SELECT recorded_at FROM operator_feedback WHERE event_id = ?",
                (request.event_id,),
            ).fetchone()
            return OutcomeObservation.model_validate({**stored, "recorded_at": row["recorded_at"]})

        disposition_row = connection.execute(
            "SELECT * FROM operator_feedback "
            "WHERE event_id = ? AND episode_id = ? AND event_type = 'disposition'",
            (request.disposition_event_id, episode_id),
        ).fetchone()
        if disposition_row is None:
            raise FeedbackConflict("Outcome requires a disposition for this episode.")
        disposition = json.loads(disposition_row["payload_json"])
        if disposition["status"] != "acted":
            raise FeedbackConflict("Outcome requires an acted disposition.")
        if request.signal.observed_at.astimezone(timezone.utc) <= datetime.fromisoformat(
            disposition_row["recorded_at"]
        ):
            raise FeedbackConflict("Outcome evidence must be observed after the recorded action.")
        if not episode.latest_finding.evidence:
            raise FeedbackConflict("Episode has no provenance to match the outcome.")
        original = episode.latest_finding.evidence[0]
        if (request.signal.metric, request.signal.entity_ref) != (
            original.metric, original.entity_ref
        ):
            raise FeedbackConflict("Outcome metric and entity must match the episode evidence.")
        if any(
            (e.source, e.signal_id) == (request.signal.source, request.signal.id)
            for e in episode.latest_finding.evidence
        ):
            raise FeedbackConflict("Outcome must be a new source observation.")
        recorded_at = datetime.now(timezone.utc).isoformat()
        connection.execute(
            "INSERT INTO operator_feedback VALUES (?, ?, 'outcome', ?, ?)",
            (request.event_id, episode_id, recorded_at, json.dumps(expected, sort_keys=True)),
        )
        return OutcomeObservation.model_validate({**expected, "recorded_at": recorded_at})


def get_episode_feedback(episode_id: str) -> EpisodeFeedback:
    initialize_feedback_database()
    with _connect() as connection:
        episode = _row_to_episode(_episode_row(connection, episode_id))
        rows = connection.execute(
            "SELECT * FROM operator_feedback WHERE episode_id = ? "
            "ORDER BY recorded_at, event_id",
            (episode_id,),
        ).fetchall()
        dispositions: list[OperatorDisposition] = []
        outcomes: list[OutcomeObservation] = []
        for row in rows:
            payload = {**json.loads(row["payload_json"]), "recorded_at": row["recorded_at"]}
            if row["event_type"] == "disposition":
                dispositions.append(OperatorDisposition.model_validate(payload))
            else:
                outcomes.append(OutcomeObservation.model_validate(payload))
    return EpisodeFeedback(episode=episode, dispositions=dispositions, outcomes=outcomes)
