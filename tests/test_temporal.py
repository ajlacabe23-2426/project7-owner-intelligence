from datetime import datetime, timedelta, timezone

from app.brief import build_owner_brief
from app.models import BusinessSignal, SignalType
from app.temporal import assess_temporal_patterns


BASE = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)


def revenue(signal_id: str, value: float, hours: int, source: str = "sales.a") -> BusinessSignal:
    return BusinessSignal(
        id=signal_id,
        source=source,
        signal_type=SignalType.sales,
        observed_at=BASE + timedelta(hours=hours),
        metric="daily_revenue",
        value=value,
        entity_ref="store-1",
    )


def test_temporal_summary_requires_three_same_source_observations():
    assert assess_temporal_patterns([revenue("a", 100, 0), revenue("b", 90, 1)]) == []


def test_temporal_summary_is_order_independent_and_descriptive_only():
    signals = [revenue("c", 70, 2), revenue("a", 100, 0), revenue("b", 85, 1)]
    forward = assess_temporal_patterns(signals)
    reverse = assess_temporal_patterns(list(reversed(signals)))
    assert forward == reverse
    assert len(forward) == 1
    item = forward[0]
    assert item.direction == "falling"
    assert item.change_pct == -0.3
    assert item.observation_count == 3
    assert item.interpretation == "descriptive-only"


def test_sources_are_not_silently_combined_into_one_trend():
    signals = [
        revenue("a1", 100, 0, "sales.a"),
        revenue("a2", 90, 1, "sales.a"),
        revenue("a3", 80, 2, "sales.a"),
        revenue("b1", 100, 0, "sales.b"),
        revenue("b2", 110, 1, "sales.b"),
        revenue("b3", 120, 2, "sales.b"),
    ]
    assessments = assess_temporal_patterns(signals)
    assert [(item.source, item.direction) for item in assessments] == [
        ("sales.a", "falling"),
        ("sales.b", "rising"),
    ]


def test_owner_brief_exposes_temporal_context_without_changing_finding_priority():
    signals = [
        revenue("a", 100, 0),
        revenue("b", 90, 1),
        revenue("c", 70, 2),
    ]
    brief = build_owner_brief(signals, as_of=BASE + timedelta(hours=3))
    assert len(brief.temporal_assessments) == 1
    assert brief.temporal_assessments[0].direction == "falling"
    # No baseline was supplied, so the existing threshold rule still creates no finding.
    assert brief.findings == []
    assert brief.action_queue == []


def test_future_dated_observations_do_not_create_or_reverse_trends():
    current = [revenue("a", 100, 0), revenue("b", 85, 1)]
    future = revenue("future", 500, 12)
    as_of = BASE + timedelta(hours=3)

    only_two_current = build_owner_brief([future, *current], as_of=as_of)
    assert only_two_current.temporal_assessments == []
    assert any(
        issue.code == "observation.future-dated"
        for issue in only_two_current.evidence_issues
    )

    third_current = revenue("c", 70, 2)
    brief = build_owner_brief([future, third_current, *current], as_of=as_of)
    assert len(brief.temporal_assessments) == 1
    assessment = brief.temporal_assessments[0]
    assert assessment.direction == "falling"
    assert assessment.latest_value == 70
    assert assessment.observation_count == 3
    assert assessment.latest_observed_at == BASE + timedelta(hours=2)
