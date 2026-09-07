"""Canonical observation identity and inspectable evidence-quality policy."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json

from app.models import (
    BusinessSignal,
    EvidenceIssue,
    EvidenceQuality,
    SignalType,
)


class ConflictingObservation(ValueError):
    """The same source observation ID has incompatible contents."""


ObservationKey = tuple[str, str]
ExpectedObservation = tuple[SignalType, str, str | None]

DEFAULT_FRESHNESS = timedelta(hours=24)
CONFLICT_WINDOW = timedelta(hours=1)
FUTURE_TOLERANCE = timedelta(minutes=5)
FRESHNESS_WINDOWS: dict[tuple[SignalType, str], timedelta] = {
    (SignalType.support, "open_urgent_items"): timedelta(hours=4),
    (SignalType.calendar, "unassigned_customer_appointments"): timedelta(hours=4),
    (SignalType.sales, "daily_revenue"): timedelta(hours=36),
    (SignalType.review, "average_rating"): timedelta(days=7),
    (SignalType.receivable, "invoice_days_overdue"): timedelta(hours=48),
}


def observation_signature(signal: BusinessSignal) -> str:
    payload = signal.model_dump(mode="json")
    payload["observed_at"] = signal.observed_at.astimezone(timezone.utc).isoformat()
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def unique_observations(signals: list[BusinessSignal]) -> list[BusinessSignal]:
    observations: dict[ObservationKey, tuple[str, BusinessSignal]] = {}
    for signal in signals:
        key = (signal.source, signal.id)
        signature = observation_signature(signal)
        previous = observations.get(key)
        if previous is not None and previous[0] != signature:
            raise ConflictingObservation(
                "Conflicting observations share the same source and signal ID."
            )
        observations[key] = (signature, signal)
    return [observations[key][1] for key in sorted(observations)]


def evidence_identity(signal: BusinessSignal) -> ExpectedObservation:
    """Identify the operational fact represented by an observation."""
    return (signal.signal_type, signal.metric, signal.entity_ref)


def _comparison_value(signal: BusinessSignal) -> str:
    """Canonicalize the factual value used to detect cross-source disagreement."""
    return json.dumps(
        {"value": signal.value, "baseline": signal.baseline},
        sort_keys=True,
        separators=(",", ":"),
    )


def _append_reason(quality: EvidenceQuality, reason: str, level: str) -> None:
    if reason not in quality.reason_codes:
        quality.reason_codes.append(reason)
    rank = {"fresh": 0, "degraded": 1, "blocked": 2}
    if rank[level] > rank[quality.level]:
        quality.level = level  # type: ignore[assignment]


def assess_evidence(
    signals: list[BusinessSignal],
    *,
    as_of: datetime | None = None,
    expected_observations: set[ExpectedObservation] | None = None,
) -> tuple[dict[ObservationKey, EvidenceQuality], list[EvidenceIssue]]:
    """Assess freshness, missing expectations, and cross-source contradictions.

    The policy is deterministic and contains no model/LLM resolution. Conflicting
    source facts are kept visible and marked blocked rather than averaged together.
    """
    observed = unique_observations(signals)
    assessed_at = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if assessed_at.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    quality_by_observation: dict[ObservationKey, EvidenceQuality] = {}
    issues: list[EvidenceIssue] = []

    for signal in observed:
        observed_at = signal.observed_at.astimezone(timezone.utc)
        delta = assessed_at - observed_at
        age_seconds = max(0, int(delta.total_seconds()))
        quality = EvidenceQuality(
            level="fresh",
            reason_codes=[],
            assessed_at=assessed_at,
            age_seconds=age_seconds,
        )
        if observed_at - assessed_at > FUTURE_TOLERANCE:
            _append_reason(quality, "observation.future-dated", "degraded")
            issues.append(
                EvidenceIssue(
                    code="observation.future-dated",
                    metric=signal.metric,
                    entity_ref=signal.entity_ref,
                    signal_ids=[signal.id],
                    sources=[signal.source],
                    detail="Observation timestamp is materially later than the assessment time.",
                )
            )
        freshness = FRESHNESS_WINDOWS.get(
            (signal.signal_type, signal.metric), DEFAULT_FRESHNESS
        )
        if delta > freshness:
            _append_reason(quality, "observation.stale", "degraded")
            issues.append(
                EvidenceIssue(
                    code="observation.stale",
                    metric=signal.metric,
                    entity_ref=signal.entity_ref,
                    signal_ids=[signal.id],
                    sources=[signal.source],
                    detail=(
                        f"Observation age exceeds the {int(freshness.total_seconds() // 3600)}-hour "
                        "freshness policy for this metric."
                    ),
                )
            )
        quality_by_observation[(signal.source, signal.id)] = quality

    grouped: dict[ExpectedObservation, list[BusinessSignal]] = defaultdict(list)
    for signal in observed:
        grouped[evidence_identity(signal)].append(signal)

    for identity, group in sorted(
        grouped.items(), key=lambda item: (item[0][0].value, item[0][1], item[0][2] or "")
    ):
        ordered = sorted(
            group,
            key=lambda signal: (
                signal.observed_at.astimezone(timezone.utc),
                signal.source,
                signal.id,
            ),
        )
        conflicting: set[ObservationKey] = set()
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                if left.source == right.source:
                    continue
                time_gap = abs(
                    left.observed_at.astimezone(timezone.utc)
                    - right.observed_at.astimezone(timezone.utc)
                )
                if time_gap > CONFLICT_WINDOW:
                    continue
                if _comparison_value(left) != _comparison_value(right):
                    conflicting.add((left.source, left.id))
                    conflicting.add((right.source, right.id))

        if conflicting:
            conflict_signals = [
                signal
                for signal in ordered
                if (signal.source, signal.id) in conflicting
            ]
            for signal in conflict_signals:
                _append_reason(
                    quality_by_observation[(signal.source, signal.id)],
                    "observation.cross-source-conflict",
                    "blocked",
                )
            issues.append(
                EvidenceIssue(
                    code="observation.cross-source-conflict",
                    metric=identity[1],
                    entity_ref=identity[2],
                    signal_ids=[signal.id for signal in conflict_signals],
                    sources=[signal.source for signal in conflict_signals],
                    detail=(
                        "Different sources reported incompatible values for the same "
                        "metric/entity within the conflict window; no value was averaged away."
                    ),
                )
            )

    if expected_observations:
        observed_identities = set(grouped)
        for missing in sorted(
            expected_observations - observed_identities,
            key=lambda item: (item[0].value, item[1], item[2] or ""),
        ):
            issues.append(
                EvidenceIssue(
                    code="observation.missing",
                    metric=missing[1],
                    entity_ref=missing[2],
                    signal_ids=[],
                    sources=[],
                    detail=(
                        f"Expected {missing[0].value} observation is absent from the supplied evidence set."
                    ),
                )
            )

    return quality_by_observation, issues
