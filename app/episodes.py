from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.models import (
    Finding,
    FindingEpisode,
    OwnerBrief,
    RecommendationHistoryEntry,
    Severity,
)


DEFAULT_EPISODE_DB_PATH = "data/owner_intelligence.db"


class EpisodeNotFound(LookupError):
    """Requested finding episode does not exist."""


def _db_path() -> Path:
    return Path(os.getenv("OWNER_INTELLIGENCE_DB_PATH", DEFAULT_EPISODE_DB_PATH))


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_episode_database() -> None:
    with _connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS finding_episodes (
                episode_id TEXT PRIMARY KEY,
                finding_key TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                current_status TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                recurrence_count INTEGER NOT NULL,
                resolution_timestamp TEXT,
                resolution_reason_code TEXT,
                reopen_count INTEGER NOT NULL DEFAULT 0,
                recommendation_history_json TEXT NOT NULL DEFAULT '[]',
                latest_finding_json TEXT NOT NULL,
                seen_finding_ids_json TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_finding_episodes_status ON finding_episodes(current_status)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_finding_episodes_last_seen ON finding_episodes(last_seen)"
        )


def _episode_key(finding: Finding) -> str:
    if not finding.evidence:
        raise ValueError("Episode-backed findings require evidence.")
    evidence = finding.evidence[0]
    logical_identity = json.dumps(
        {
            "rule_version": finding.rule_version,
            "title": finding.title,
            "metric": evidence.metric,
            "entity_ref": evidence.entity_ref or "__global__",
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(logical_identity.encode("utf-8")).hexdigest()


def _episode_id(finding_key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"project7:episode:v1:{finding_key}"))


def _observation_times(findings: list[Finding]) -> tuple[datetime, datetime]:
    times = [
        evidence.observed_at.astimezone(timezone.utc)
        for finding in findings
        for evidence in finding.evidence
    ]
    if not times:
        raise ValueError("Episode-backed findings require timestamped evidence.")
    return min(times), max(times)


def _representative(findings: list[Finding]) -> Finding:
    return max(
        findings,
        key=lambda finding: (
            max(e.observed_at.astimezone(timezone.utc) for e in finding.evidence),
            finding.id,
        ),
    )


def _recommendation_history(
    existing: list[RecommendationHistoryEntry], representative: Finding, recorded_at: datetime
) -> list[RecommendationHistoryEntry]:
    if existing and existing[-1].recommendation == representative.recommended_action:
        return existing
    return [
        *existing,
        RecommendationHistoryEntry(
            recorded_at=recorded_at,
            recommendation=representative.recommended_action,
            finding_id=representative.id,
        ),
    ]


def _row_to_episode(row: sqlite3.Row) -> FindingEpisode:
    return FindingEpisode(
        episode_id=row["episode_id"],
        finding_key=row["finding_key"],
        title=row["title"],
        current_status=row["current_status"],
        first_seen=datetime.fromisoformat(row["first_seen"]),
        last_seen=datetime.fromisoformat(row["last_seen"]),
        recurrence_count=row["recurrence_count"],
        resolution_timestamp=(
            datetime.fromisoformat(row["resolution_timestamp"])
            if row["resolution_timestamp"]
            else None
        ),
        resolution_reason_code=row["resolution_reason_code"],
        reopen_count=row["reopen_count"],
        recommendation_history=[
            RecommendationHistoryEntry.model_validate(item)
            for item in json.loads(row["recommendation_history_json"])
        ],
        latest_finding=Finding.model_validate(json.loads(row["latest_finding_json"])),
    )


def list_episodes() -> list[FindingEpisode]:
    initialize_episode_database()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT * FROM finding_episodes
            ORDER BY CASE current_status WHEN 'open' THEN 0 ELSE 1 END,
                     last_seen DESC, episode_id
            """
        ).fetchall()
    return [_row_to_episode(row) for row in rows]


def resolve_episode(episode_id: str, reason_code: str) -> FindingEpisode:
    initialize_episode_database()
    with _connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT * FROM finding_episodes WHERE episode_id = ?", (episode_id,)
        ).fetchone()
        if row is None:
            raise EpisodeNotFound(f"Episode {episode_id} was not found.")
        if row["current_status"] == "resolved":
            return _row_to_episode(row)
        resolved_at = datetime.now(timezone.utc).isoformat()
        connection.execute(
            """
            UPDATE finding_episodes
            SET current_status = 'resolved',
                resolution_timestamp = ?,
                resolution_reason_code = ?
            WHERE episode_id = ?
            """,
            (resolved_at, reason_code, episode_id),
        )
        updated = connection.execute(
            "SELECT * FROM finding_episodes WHERE episode_id = ?", (episode_id,)
        ).fetchone()
    if updated is None:
        raise RuntimeError("Episode resolution was not persisted.")
    return _row_to_episode(updated)


def reconcile_brief(brief: OwnerBrief) -> OwnerBrief:
    """Persist active finding episodes and annotate the current brief.

    Exact replayed findings do not increment recurrence. A resolved episode reopens
    only when a previously unseen qualifying finding supplies new evidence. Blocked
    confidence findings never mutate episode state.
    """
    initialize_episode_database()
    grouped: dict[str, list[Finding]] = defaultdict(list)
    passthrough: list[Finding] = []
    for finding in brief.findings:
        if finding.confidence == "blocked" or not finding.evidence:
            passthrough.append(finding)
            continue
        grouped[_episode_key(finding)].append(finding)

    enriched_by_id: dict[str, Finding] = {finding.id: finding for finding in passthrough}
    episode_state_counts = {"new": 0, "ongoing": 0, "reopened": 0, "resolved": 0}

    with _connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        for finding_key in sorted(grouped):
            findings = grouped[finding_key]
            first_observed, last_observed = _observation_times(findings)
            representative = _representative(findings)
            episode_id = _episode_id(finding_key)
            current_ids = {finding.id for finding in findings}
            row = connection.execute(
                "SELECT * FROM finding_episodes WHERE finding_key = ?", (finding_key,)
            ).fetchone()

            if row is None:
                presentation_state = "new"
                recurrence_count = len(current_ids)
                history = _recommendation_history([], representative, last_observed)
                connection.execute(
                    """
                    INSERT INTO finding_episodes (
                        episode_id, finding_key, title, current_status,
                        first_seen, last_seen, recurrence_count,
                        resolution_timestamp, resolution_reason_code, reopen_count,
                        recommendation_history_json, latest_finding_json,
                        seen_finding_ids_json
                    ) VALUES (?, ?, ?, 'open', ?, ?, ?, NULL, NULL, 0, ?, ?, ?)
                    """,
                    (
                        episode_id,
                        finding_key,
                        representative.title,
                        first_observed.isoformat(),
                        last_observed.isoformat(),
                        recurrence_count,
                        json.dumps([item.model_dump(mode="json") for item in history]),
                        representative.model_dump_json(),
                        json.dumps(sorted(current_ids)),
                    ),
                )
            else:
                seen_ids = set(json.loads(row["seen_finding_ids_json"]))
                new_ids = current_ids - seen_ids
                current_status = row["current_status"]
                if not new_ids:
                    presentation_state = (
                        "resolved" if current_status == "resolved" else "ongoing"
                    )
                    recurrence_count = row["recurrence_count"]
                else:
                    presentation_state = (
                        "reopened" if current_status == "resolved" else "ongoing"
                    )
                    recurrence_count = row["recurrence_count"] + len(new_ids)
                    existing_history = [
                        RecommendationHistoryEntry.model_validate(item)
                        for item in json.loads(row["recommendation_history_json"])
                    ]
                    history = _recommendation_history(
                        existing_history, representative, last_observed
                    )
                    merged_seen = seen_ids | current_ids
                    previous_first = datetime.fromisoformat(row["first_seen"])
                    previous_last = datetime.fromisoformat(row["last_seen"])
                    new_first = min(previous_first, first_observed)
                    new_last = max(previous_last, last_observed)
                    reopen_count = row["reopen_count"] + (
                        1 if current_status == "resolved" else 0
                    )
                    connection.execute(
                        """
                        UPDATE finding_episodes
                        SET current_status = 'open',
                            first_seen = ?,
                            last_seen = ?,
                            recurrence_count = ?,
                            resolution_timestamp = NULL,
                            resolution_reason_code = NULL,
                            reopen_count = ?,
                            recommendation_history_json = ?,
                            latest_finding_json = ?,
                            seen_finding_ids_json = ?
                        WHERE finding_key = ?
                        """,
                        (
                            new_first.isoformat(),
                            new_last.isoformat(),
                            recurrence_count,
                            reopen_count,
                            json.dumps(
                                [item.model_dump(mode="json") for item in history]
                            ),
                            representative.model_dump_json(),
                            json.dumps(sorted(merged_seen)),
                            finding_key,
                        ),
                    )

            persisted = connection.execute(
                "SELECT * FROM finding_episodes WHERE finding_key = ?", (finding_key,)
            ).fetchone()
            if persisted is None:
                raise RuntimeError("Episode reconciliation was not persisted.")
            episode = _row_to_episode(persisted)
            episode_state_counts[presentation_state] += 1
            for finding in findings:
                enriched_by_id[finding.id] = finding.model_copy(
                    update={
                        "episode_id": episode.episode_id,
                        "episode_state": presentation_state,
                        "episode_first_seen": episode.first_seen,
                        "episode_last_seen": episode.last_seen,
                        "episode_recurrence_count": episode.recurrence_count,
                    }
                )

    enriched_findings = [enriched_by_id[finding.id] for finding in brief.findings]
    action_queue = [
        finding.recommended_action
        for finding in enriched_findings
        if finding.severity in {Severity.critical, Severity.high}
        and finding.confidence != "blocked"
        and finding.episode_state != "resolved"
    ]
    episode_summary = ", ".join(
        f"{count} {state}"
        for state, count in episode_state_counts.items()
        if count
    )
    headline = brief.headline
    if episode_summary:
        headline += f" Episode state: {episode_summary}."

    return brief.model_copy(
        update={
            "headline": headline,
            "findings": enriched_findings,
            "action_queue": action_queue,
        }
    )
