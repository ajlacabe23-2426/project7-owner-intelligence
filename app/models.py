from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class SignalType(str, Enum):
    sales = "sales"
    cash = "cash"
    receivable = "receivable"
    calendar = "calendar"
    support = "support"
    review = "review"
    lead = "lead"
    operations = "operations"


class BusinessSignal(BaseModel):
    id: str
    source: str
    signal_type: SignalType
    observed_at: datetime
    metric: str
    value: float | int | str | bool
    baseline: float | int | None = None
    unit: str | None = None
    entity_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceRef(BaseModel):
    signal_id: str
    source: str
    metric: str
    observed_value: float | int | str | bool


class Finding(BaseModel):
    id: str
    title: str
    severity: Severity
    explanation: str
    recommended_action: str
    evidence: list[EvidenceRef]


class OwnerBrief(BaseModel):
    generated_at: datetime
    headline: str
    findings: list[Finding]
    action_queue: list[str]
    signal_count: int
