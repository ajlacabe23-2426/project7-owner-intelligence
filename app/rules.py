from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5
from datetime import timezone

from app.models import BusinessSignal, EvidenceRef, Finding, Severity, SignalType
from app.evidence import observation_signature, unique_observations


def _evidence(signal: BusinessSignal) -> EvidenceRef:
    return EvidenceRef(
        signal_id=signal.id,
        source=signal.source,
        metric=signal.metric,
        observed_value=signal.value,
        observed_at=signal.observed_at.astimezone(timezone.utc),
        baseline=signal.baseline,
        unit=signal.unit,
        entity_ref=signal.entity_ref,
        amount=signal.metadata.get("amount") if signal.metric == "invoice_days_overdue" else None,
    )


def evaluate_signals(signals: list[BusinessSignal]) -> list[Finding]:
    """Evaluate normalized signals using transparent V1 rules.

    The rule engine intentionally favors explainability over sophistication.
    Each finding must cite the exact source signals that triggered it.
    """
    findings: list[Finding] = []

    for signal in unique_observations(signals):
        finding_id = str(uuid5(NAMESPACE_URL, "project7:rules:v1:" + observation_signature(signal)))
        if signal.signal_type == SignalType.receivable and signal.metric == "invoice_days_overdue":
            days = float(signal.value)
            amount = float(signal.metadata["amount"])
            if days >= 30 and amount >= 1000:
                severity = Severity.high if days < 60 else Severity.critical
                findings.append(
                    Finding(
                        id=finding_id,
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
                        id=finding_id,
                        title="Urgent support backlog",
                        severity=Severity.high,
                        explanation=f"The supplied observation reports {count} open urgent support items.",
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
                        id=finding_id,
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
                            id=finding_id,
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
                        id=finding_id,
                        title="Customer appointments lack ownership",
                        severity=Severity.high if count >= 3 else Severity.medium,
                        explanation=f"The supplied observation reports {count} unassigned customer appointment(s).",
                        recommended_action="Assign an accountable owner before the appointment window begins.",
                        evidence=[_evidence(signal)],
                    )
                )

    rank = {Severity.critical: 0, Severity.high: 1, Severity.medium: 2, Severity.low: 3}
    return sorted(findings, key=lambda item: (rank[item.severity], item.id))
