from datetime import datetime, timezone

from app.evidence import ExpectedObservation, assess_evidence
from app.models import BusinessSignal, OwnerBrief, Severity
from app.rules import evaluate_signals


def build_owner_brief(
    signals: list[BusinessSignal],
    *,
    as_of: datetime | None = None,
    expected_observations: set[ExpectedObservation] | None = None,
) -> OwnerBrief:
    generated_at = as_of or datetime.now(timezone.utc)
    quality_by_observation, evidence_issues = assess_evidence(
        signals,
        as_of=generated_at,
        expected_observations=expected_observations,
    )
    findings = evaluate_signals(
        signals,
        as_of=generated_at,
        quality_by_observation=quality_by_observation,
    )

    if not findings:
        headline = "No rule-based exceptions detected in the supplied signals."
    else:
        top = findings[0]
        headline = (
            f"{len(findings)} operating exception(s) detected; top priority: {top.title}."
        )
    if evidence_issues:
        headline += f" Evidence review flagged {len(evidence_issues)} quality issue(s)."

    action_queue = [
        finding.recommended_action
        for finding in findings
        if finding.severity in {Severity.critical, Severity.high}
        and finding.confidence != "blocked"
    ]

    return OwnerBrief(
        generated_at=generated_at,
        headline=headline,
        findings=findings,
        action_queue=action_queue,
        signal_count=len(signals),
        evidence_issues=evidence_issues,
    )
