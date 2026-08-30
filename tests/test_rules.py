from datetime import datetime, timezone

from app.models import BusinessSignal, Severity, SignalType
from app.rules import evaluate_signals


def make_signal(**overrides):
    data = {
        "id": "sig-test",
        "source": "test.source",
        "signal_type": SignalType.support,
        "observed_at": datetime.now(timezone.utc),
        "metric": "open_urgent_items",
        "value": 0,
    }
    data.update(overrides)
    return BusinessSignal(**data)


def test_material_overdue_receivable_is_flagged():
    signal = make_signal(
        id="ar-1",
        signal_type=SignalType.receivable,
        metric="invoice_days_overdue",
        value=61,
        metadata={"amount": 2500},
    )
    findings = evaluate_signals([signal])
    assert len(findings) == 1
    assert findings[0].severity == Severity.critical
    assert findings[0].evidence[0].signal_id == "ar-1"


def test_small_overdue_receivable_is_not_flagged():
    signal = make_signal(
        signal_type=SignalType.receivable,
        metric="invoice_days_overdue",
        value=45,
        metadata={"amount": 300},
    )
    assert evaluate_signals([signal]) == []


def test_urgent_support_backlog_is_high_priority():
    signal = make_signal(metric="open_urgent_items", value=4)
    findings = evaluate_signals([signal])
    assert len(findings) == 1
    assert findings[0].severity == Severity.high


def test_revenue_drop_uses_supplied_baseline():
    signal = make_signal(
        signal_type=SignalType.sales,
        metric="daily_revenue",
        value=5000,
        baseline=10000,
    )
    findings = evaluate_signals([signal])
    assert len(findings) == 1
    assert findings[0].severity == Severity.high


def test_findings_sorted_by_severity():
    support = make_signal(id="support", metric="open_urgent_items", value=4)
    receivable = make_signal(
        id="ar",
        signal_type=SignalType.receivable,
        metric="invoice_days_overdue",
        value=70,
        metadata={"amount": 4000},
    )
    findings = evaluate_signals([support, receivable])
    assert findings[0].severity == Severity.critical
    assert findings[1].severity == Severity.high
