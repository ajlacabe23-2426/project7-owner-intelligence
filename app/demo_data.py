from datetime import datetime, timezone

from app.models import BusinessSignal, SignalType


def synthetic_signals() -> list[BusinessSignal]:
    now = datetime.now(timezone.utc)
    return [
        BusinessSignal(
            id="sig-receivable-001",
            source="synthetic.accounting",
            signal_type=SignalType.receivable,
            observed_at=now,
            metric="invoice_days_overdue",
            value=67,
            unit="days",
            entity_ref="invoice-demo-1042",
            metadata={"amount": 4200},
        ),
        BusinessSignal(
            id="sig-support-001",
            source="synthetic.support",
            signal_type=SignalType.support,
            observed_at=now,
            metric="open_urgent_items",
            value=4,
            unit="items",
        ),
        BusinessSignal(
            id="sig-sales-001",
            source="synthetic.sales",
            signal_type=SignalType.sales,
            observed_at=now,
            metric="daily_revenue",
            value=6200,
            baseline=9000,
            unit="USD",
        ),
        BusinessSignal(
            id="sig-calendar-001",
            source="synthetic.calendar",
            signal_type=SignalType.calendar,
            observed_at=now,
            metric="unassigned_customer_appointments",
            value=2,
            unit="appointments",
        ),
        BusinessSignal(
            id="sig-review-001",
            source="synthetic.reviews",
            signal_type=SignalType.review,
            observed_at=now,
            metric="average_rating",
            value=3.7,
            baseline=4.5,
            unit="stars",
        ),
    ]
