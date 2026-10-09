from __future__ import annotations

import hashlib
import json
from datetime import timezone

from pydantic import BaseModel, Field, model_validator

from app.brief import build_owner_brief
from app.models import BusinessSignal, OwnerBrief


class SignalBatch(BaseModel):
    """Provider-neutral boundary between source adapters and the intelligence core."""

    batch_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9._:-]+$")
    source: str = Field(min_length=1, max_length=200)
    connector_run_id: str | None = Field(
        default=None, min_length=1, max_length=120, pattern=r"^[A-Za-z0-9._:-]+$"
    )
    signals: list[BusinessSignal] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_source_contract(self) -> "SignalBatch":
        ids: set[str] = set()
        for signal in self.signals:
            if signal.source != self.source:
                raise ValueError("every signal source must match the batch source")
            if signal.id in ids:
                raise ValueError("signal IDs must be unique within one source batch")
            ids.add(signal.id)
        return self


class IngestionResult(BaseModel):
    batch_id: str
    source: str
    connector_run_id: str | None = None
    accepted_count: int = Field(ge=1)
    batch_digest: str
    brief: OwnerBrief


def batch_digest(batch: SignalBatch) -> str:
    """Stable digest independent of adapter delivery order."""
    # Two adapters may express the same instant with different timezone offsets.
    # Normalize before sorting and hashing so equivalent evidence has one digest.
    canonical_signals = []
    for signal in batch.signals:
        item = signal.model_dump(mode="json")
        item["observed_at"] = signal.observed_at.astimezone(timezone.utc).isoformat()
        canonical_signals.append(item)
    canonical_signals.sort(key=lambda item: (item["observed_at"], item["id"]))
    payload = {
        "batch_id": batch.batch_id,
        "source": batch.source,
        "connector_run_id": batch.connector_run_id,
        "signals": canonical_signals,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def analyze_signal_batch(batch: SignalBatch) -> IngestionResult:
    return IngestionResult(
        batch_id=batch.batch_id,
        source=batch.source,
        connector_run_id=batch.connector_run_id,
        accepted_count=len(batch.signals),
        batch_digest=batch_digest(batch),
        brief=build_owner_brief(batch.signals),
    )
