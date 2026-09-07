from datetime import datetime, timedelta, timezone

from app.brief import build_owner_brief
from app.evidence import assess_evidence
from app.models import BusinessSignal, SignalType


BASE = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def support_signal(
    *,
    signal_id: str,
    source: str,
    value: int = 4,
    observed_at: datetime = BASE,
    entity_ref: str = "support-queue",
) -> BusinessSignal:
    return BusinessSignal(
        id=signal_id,
        source=source,
        signal_type=SignalType.support,
        observed_at=observed_at,
        metric="open_urgent_items",
        value=value,
        entity_ref=entity_ref,
    )


def test_fresh_evidence_retains_normal_confidence():
    signal = support_signal(signal_id="fresh-1", source="support.a")
    brief = build_owner_brief([signal], as_of=BASE + timedelta(hours=1))

    assert brief.evidence_issues == []
    assert brief.findings[0].confidence == "normal"
    assert brief.findings[0].evidence[0].quality is not None
    assert brief.findings[0].evidence[0].quality.level == "fresh"
    assert brief.findings[0].evidence[0].quality.reason_codes == []


def test_stale_evidence_is_explicit_and_reduces_confidence():
    signal = support_signal(signal_id="stale-1", source="support.a")
    brief = build_owner_brief([signal], as_of=BASE + timedelta(hours=5))

    assert brief.findings[0].confidence == "reduced"
    quality = brief.findings[0].evidence[0].quality
    assert quality is not None
    assert quality.level == "degraded"
    assert "observation.stale" in quality.reason_codes
    assert any(issue.code == "observation.stale" for issue in brief.evidence_issues)


def test_cross_source_conflict_is_visible_blocked_and_not_averaged():
    left = support_signal(signal_id="a-1", source="support.a", value=4)
    right = support_signal(
        signal_id="b-1",
        source="support.b",
        value=7,
        observed_at=BASE + timedelta(minutes=20),
    )
    brief = build_owner_brief([right, left], as_of=BASE + timedelta(hours=1))

    conflicts = [
        issue
        for issue in brief.evidence_issues
        if issue.code == "observation.cross-source-conflict"
    ]
    assert len(conflicts) == 1
    assert set(conflicts[0].signal_ids) == {"a-1", "b-1"}
    assert set(conflicts[0].sources) == {"support.a", "support.b"}
    assert {finding.confidence for finding in brief.findings} == {"blocked"}
    assert {
        finding.evidence[0].signal_id for finding in brief.findings
    } == {"a-1", "b-1"}
    assert brief.action_queue == []


def test_missing_expected_observation_has_reason_code():
    expected = {(SignalType.sales, "daily_revenue", "store-1")}
    quality, issues = assess_evidence(
        [], as_of=BASE, expected_observations=expected
    )

    assert quality == {}
    assert len(issues) == 1
    assert issues[0].code == "observation.missing"
    assert issues[0].metric == "daily_revenue"
    assert issues[0].entity_ref == "store-1"
    assert issues[0].signal_ids == []


def test_out_of_order_input_produces_same_quality_result():
    older = support_signal(
        signal_id="older",
        source="support.a",
        observed_at=BASE,
        value=4,
    )
    newer = support_signal(
        signal_id="newer",
        source="support.b",
        observed_at=BASE + timedelta(hours=2),
        value=4,
    )
    as_of = BASE + timedelta(hours=3)

    forward_quality, forward_issues = assess_evidence(
        [older, newer], as_of=as_of
    )
    reversed_quality, reversed_issues = assess_evidence(
        [newer, older], as_of=as_of
    )

    assert forward_quality == reversed_quality
    assert forward_issues == reversed_issues


def test_future_dated_observation_is_degraded_not_treated_as_current():
    future = support_signal(
        signal_id="future",
        source="support.a",
        observed_at=BASE + timedelta(hours=1),
    )
    quality, issues = assess_evidence([future], as_of=BASE)

    result = quality[("support.a", "future")]
    assert result.level == "degraded"
    assert "observation.future-dated" in result.reason_codes
    assert any(issue.code == "observation.future-dated" for issue in issues)
