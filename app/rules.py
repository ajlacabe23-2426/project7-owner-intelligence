from __future__ import annotations

from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from app.evidence import assess_evidence, observation_signature, unique_observations
from app.models import (
    BusinessSignal,
    EvidenceQuality,
    EvidenceRef,
    Finding,
    FindingConfidence,
    Severity,
    SignalType,
)


def _confidence(quality: EvidenceQuality) -> FindingConfidence:
    if quality.level == "blocked":
        return "blocked"
    if quality.level == "degraded":
        return "reduced"
    return "normal"


def _evidence(signal: BusinessSignal, quality: EvidenceQuality) -> EvidenceRef:
    return EvidenceRef(
        signal_id=signal.id,
        source=signal.source,
        metric=signal.metric,
        observed_value=signal.value,
        observed_at=signal.observed_at.astimezone(timezone.utc),
        baseline=signal.baseline,
        unit=signal.unit,
        entity_ref=signal.entity_ref,
        amount=(
            signal.metadata.get("amount")
            if signal.metric == "invoice_days_overdue"
            else None
        ),
        quality=quality,
    )


def evaluate_signals(
    signals: list[BusinessSignal],
    *,
    as_of: datetime | None = None,
    quality_by_observation: dict[tuple[str, str], EvidenceQuality] | None = None,
) -> list[Finding]:
    """Evaluate normalized signals using transparent, evidence-aware rules.

    Each finding cites the exact source observation and inherits confidence from
    inspectable evidence quality. Stale evidence is reduced-confidence and
    cross-source factual conflicts are blocked-confidence; neither is hidden.
    """
    findings: list[Finding] = []
    observed = unique_observations(signals)
    if quality_by_observation is None:
        quality_by_observation, _ = assess_evidence(observed, as_of=as_of)

    for signal in observed:
        quality = quality_by_observation[(signal.source, signal.id)]
        confidence = _confidence(quality)
        evidence = [_evidence(signal, quality)]
        finding_id = str(
            uuid5(
                NAMESPACE_URL,
                "project7:rules:v1:" + observation_signature(signal),
            )
        )
        if (
            signal.signal_type == SignalType.receivable
            and signal.metric == "invoice_days_overdue"
        ):
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
                        recommended_action=(
                            "Review the invoice, customer status, and collection next step today."
                        ),
                        evidence=evidence,
                        confidence=confidence,
                    )
                )

        elif (
            signal.signal_type == SignalType.support
            and signal.metric == "open_urgent_items"
        ):
            count = int(signal.value)
            if count >= 3:
                findings.append(
                    Finding(
                        id=finding_id,
                        title="Urgent support backlog",
                        severity=Severity.high,
                        explanation=(
                            f"The supplied observation reports {count} open urgent support items."
                        ),
                        recommended_action=(
                            "Assign an owner and due time to each urgent item before taking lower-priority work."
                        ),
                        evidence=evidence,
                        confidence=confidence,
                    )
                )

        elif (
            signal.signal_type == SignalType.review
            and signal.metric == "average_rating"
        ):
            rating = float(signal.value)
            baseline = (
                float(signal.baseline) if signal.baseline is not None else None
            )
            if rating < 4.0 and (baseline is None or rating < baseline):
                findings.append(
                    Finding(
                        id=finding_id,
                        title="Customer rating below operating threshold",
                        severity=Severity.medium,
                        explanation=(
                            f"Average rating is {rating:.1f}."
                            + (
                                f" Prior baseline was {baseline:.1f}."
                                if baseline is not None
                                else ""
                            )
                        ),
                        recommended_action=(
                            "Review the newest negative feedback and identify any repeated service failure."
                        ),
                        evidence=evidence,
                        confidence=confidence,
                    )
                )

        elif (
            signal.signal_type == SignalType.sales
            and signal.metric == "daily_revenue"
        ):
            revenue = float(signal.value)
            baseline = (
                float(signal.baseline) if signal.baseline is not None else None
            )
            if baseline and baseline > 0:
                change = (revenue - baseline) / baseline
                if change <= -0.20:
                    findings.append(
                        Finding(
                            id=finding_id,
                            title="Revenue materially below baseline",
                            severity=(
                                Severity.medium if change > -0.40 else Severity.high
                            ),
                            explanation=(
                                f"Revenue is {abs(change):.0%} below the supplied baseline."
                            ),
                            recommended_action=(
                                "Check whether the change is explained by seasonality, pipeline volume, capacity, or a data issue."
                            ),
                            evidence=evidence,
                            confidence=confidence,
                        )
                    )

        elif (
            signal.signal_type == SignalType.calendar
            and signal.metric == "unassigned_customer_appointments"
        ):
            count = int(signal.value)
            if count > 0:
                findings.append(
                    Finding(
                        id=finding_id,
                        title="Customer appointments lack ownership",
                        severity=(
                            Severity.high if count >= 3 else Severity.medium
                        ),
                        explanation=(
                            f"The supplied observation reports {count} unassigned customer appointment(s)."
                        ),
                        recommended_action=(
                            "Assign an accountable owner before the appointment window begins."
                        ),
                        evidence=evidence,
                        confidence=confidence,
                    )
                )

    rank = {
        Severity.critical: 0,
        Severity.high: 1,
        Severity.medium: 2,
        Severity.low: 3,
    }
    return sorted(findings, key=lambda item: (rank[item.severity], item.id))
