"""Canonical observation identity for repeatable, source-scoped analysis."""
from datetime import timezone
import json

from app.models import BusinessSignal


class ConflictingObservation(ValueError):
    """The same source observation ID has incompatible contents."""


def observation_signature(signal: BusinessSignal) -> str:
    payload = signal.model_dump(mode="json")
    payload["observed_at"] = signal.observed_at.astimezone(timezone.utc).isoformat()
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def unique_observations(signals: list[BusinessSignal]) -> list[BusinessSignal]:
    observations: dict[tuple[str, str], tuple[str, BusinessSignal]] = {}
    for signal in signals:
        key = (signal.source, signal.id)
        signature = observation_signature(signal)
        previous = observations.get(key)
        if previous is not None and previous[0] != signature:
            raise ConflictingObservation("Conflicting observations share the same source and signal ID.")
        observations[key] = (signature, signal)
    return [observations[key][1] for key in sorted(observations)]
