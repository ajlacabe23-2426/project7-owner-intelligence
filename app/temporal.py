"""Descriptive temporal summaries for repeated numeric observations.

These summaries do not change finding severity, infer causality, or create facts.
"""
from __future__ import annotations

from collections import defaultdict
from numbers import Real

from app.evidence import unique_observations
from app.models import BusinessSignal, TemporalAssessment


def _numeric(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    return float(value)


def assess_temporal_patterns(signals: list[BusinessSignal]) -> list[TemporalAssessment]:
    """Summarize repeated same-source numeric observations without causal inference."""
    grouped: dict[tuple[str, object, str, str | None], list[BusinessSignal]] = defaultdict(list)
    for signal in unique_observations(signals):
        if _numeric(signal.value) is None:
            continue
        grouped[(signal.source, signal.signal_type, signal.metric, signal.entity_ref)].append(signal)

    assessments: list[TemporalAssessment] = []
    for (source, signal_type, metric, entity_ref), group in sorted(
        grouped.items(),
        key=lambda item: (item[0][0], item[0][1].value, item[0][2], item[0][3] or ""),
    ):
        if len(group) < 3:
            continue
        ordered = sorted(group, key=lambda signal: (signal.observed_at, signal.id))
        first = _numeric(ordered[0].value)
        latest = _numeric(ordered[-1].value)
        if first is None or latest is None:
            continue
        if first == 0:
            change_pct = None
            direction = "flat" if latest == 0 else ("rising" if latest > 0 else "falling")
        else:
            change_pct = (latest - first) / abs(first)
            direction = "flat" if abs(change_pct) < 0.05 else ("rising" if change_pct > 0 else "falling")
        assessments.append(
            TemporalAssessment(
                source=source,
                signal_type=signal_type,
                metric=metric,
                entity_ref=entity_ref,
                observation_count=len(ordered),
                first_observed_at=ordered[0].observed_at,
                latest_observed_at=ordered[-1].observed_at,
                first_value=first,
                latest_value=latest,
                change_pct=change_pct,
                direction=direction,
            )
        )
    return assessments
