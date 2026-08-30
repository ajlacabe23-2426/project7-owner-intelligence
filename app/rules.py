from __future__ import annotations

from uuid import uuid4

from app.models import BusinessSignal, EvidenceRef, Finding, Severity, SignalType


def _evidence(signal: BusinessSignal) -> EvidenceRef:
    return EvidenceRef(
        signal_id=signal.id,
        source=signal.source,
        metric=signal.metric,
        observed_value=signal.value,
    )


def evaluate_signals(signals: list[BusinessSignal]) -> list[Finding]:
    """Evaluate normalized signals using transparent V1 rules.

    The rule engine intentionally favors explainability over sophistication.
    Each finding must cite the exact source signals that triggered it.
    """
    findings: list[Finding] = []

    for signal in signals:
        if signal.signal_type == SignalType.receivable and signal.metric == "invoice_days_overdue":
            days = float(signal.value)
            amount = float(signal.metadata.get("amount", 0))
            if days >= 30 and amount >= 1000:
                severity = Severity.high if days < 60 else Severity.critical
                findings.append(
                    Finding(
                        id=str(uuid4()),
                        title="Material overdue receivable",
                        severity=severity,
                        explanation=(
                            f"A receivable worth {amount:.0f} is {days:.0f} days overdue. "
                            "This can create avoidable cash-flow pressure."
                        ),
                        recommended_action="Review the invoice, customer status, and collection next step today.",
                        evidence=[_evidence(signal)],
                    )
                )

        elif signal.signal_type == SignalType.support and signal.metric == "open_urgent_items":
            count = int(signal.value)
            if count >= 3:
                findings.append(
                    Finding(
                        id=str(uuid4()),
                        title="Urgent support backlog",
                        severity=Severity.high,
                        explanation=f"There are {count} urgent support items currently open.",
                        recommended_action="Assign an owner and due time to each urgent item before taking lower-priority work.",
                        evidence=[_evidence(signal)],
                    )
                )

        elif signal.signal_type == SignalType.review and signal.metric == "average_rating":
            rating = float(signal.value)
            baseline = float(signal.baseline) if signal.baseline is not None else None
            if rating < 4.0 and (baseline is None or rating < baseline):
                findings.append(
                    Finding(
                        id=str(uuid4()),
                        title="Customer rating below operating threshold",
                        severity=Severity.medium,
                        explanation=(
                            f"Average rating is {rating:.1f}."
                            + (f" Prior baseline was {baseline:.1f}." if baseline is not None else "")
                        ),
                        recommended_action="Review the newest negative feedback and identify any repeated service failure.",
                        evidence=[_evidence(signal)],
                    )
                )

        elif signal.signal_type == SignalType.sales and signal.metric == "daily_revenue":
            revenue = float(signal.value)
            baseline = float(signal.baseline) if signal.baseline is not None else None
            if baseline and baseline > 0:
                change = (revenue - baseline) / baseline
                if change <= -0.20:
                    findings.append(
                        Finding(
                            id=str(uuid4()),
                            title="Revenue materially below baseline",
                            severity=Severity.medium if change > -0.40 else Severity.high,
                            explanation=f"Revenue is {abs(change):.0%} below the supplied baseline.",
                            recommended_action="Check whether the change is explained by seasonality, pipeline volume, capacity, or a data issue.",
                            evidence=[_evidence(signal)],
                        )
                    )

        elif signal.signal_type == SignalType.calendar and signal.metric == "unassigned_customer_appointments":
            count = int(signal.value)
            if count > 0:
                findings.append(
                    Finding(
                        id=str(uuid4()),
                        title="Customer appointments lack ownership",
                        severity=Severity.high if count >= 3 else Severity.medium,
                        explanation=f"{count} customer appointment(s) are currently unassigned.",
                        recommended_action="Assign an accountable owner before the appointment window begins.",
                        evidence=[_evidence(signal)],
                    )
                )

    rank = {Severity.critical: 0, Severity.high: 1, Severity.medium: 2, Severity.low: 3}
    return sorted(findings, key=lambda item: rank[item.severity])
