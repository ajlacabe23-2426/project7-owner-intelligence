from datetime import datetime, timezone

from app.models import BusinessSignal, OwnerBrief, Severity
from app.rules import evaluate_signals


def build_owner_brief(signals: list[BusinessSignal]) -> OwnerBrief:
    findings = evaluate_signals(signals)

    if not findings:
        headline = "No rule-based exceptions detected in the supplied signals."
    else:
        top = findings[0]
        headline = f"{len(findings)} operating exception(s) detected; top priority: {top.title}."

    action_queue = [f.recommended_action for f in findings if f.severity in {Severity.critical, Severity.high}]

    return OwnerBrief(
        generated_at=datetime.now(timezone.utc),
        headline=headline,
        findings=findings,
        action_queue=action_queue,
        signal_count=len(signals),
    )
