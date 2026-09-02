from datetime import datetime
from enum import Enum
from typing import Any
import math

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


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
    model_config = ConfigDict(allow_inf_nan=False)

    id: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=200)
    signal_type: SignalType
    observed_at: AwareDatetime
    metric: str = Field(min_length=1, max_length=200)
    value: float | int | str | bool
    baseline: float | int | None = None
    unit: str | None = None
    entity_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("baseline", mode="before")
    @classmethod
    def validate_baseline_type(cls, value: Any) -> Any:
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise ValueError("baseline must be a number or null")
        return value

    @model_validator(mode="after")
    def validate_rule_inputs(self) -> "BusinessSignal":
        numeric_metrics = {
            (SignalType.receivable, "invoice_days_overdue"),
            (SignalType.support, "open_urgent_items"),
            (SignalType.review, "average_rating"),
            (SignalType.sales, "daily_revenue"),
            (SignalType.calendar, "unassigned_customer_appointments"),
        }
        if (self.signal_type, self.metric) not in numeric_metrics:
            return self

        def number(value: Any, label: str) -> float:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{label} must be a finite number")
            try:
                finite = math.isfinite(value)
            except OverflowError:
                finite = False
            if not finite or value < 0:
                raise ValueError(f"{label} must be a finite non-negative number")
            return value

        value = number(self.value, "value")
        if self.baseline is not None:
            number(self.baseline, "baseline")
        if self.metric in {"open_urgent_items", "unassigned_customer_appointments", "invoice_days_overdue"}:
            if value != int(value):
                raise ValueError("count and day metrics must be whole numbers")
        if self.metric == "average_rating":
            if value > 5 or (self.baseline is not None and self.baseline > 5):
                raise ValueError("ratings must be between zero and five")
        if self.metric == "invoice_days_overdue":
            if "amount" not in self.metadata:
                raise ValueError("receivable evidence requires metadata.amount")
            number(self.metadata["amount"], "metadata.amount")
        return self


class EvidenceRef(BaseModel):
    signal_id: str
    source: str
    metric: str
    observed_value: float | int | str | bool
    observed_at: datetime
    baseline: float | int | None = None
    unit: str | None = None
    entity_ref: str | None = None
    amount: float | int | None = None


class Finding(BaseModel):
    id: str
    title: str
    severity: Severity
    explanation: str
    recommended_action: str
    evidence: list[EvidenceRef]
    rule_version: str = "v1"


class OwnerBrief(BaseModel):
    generated_at: datetime
    headline: str
    findings: list[Finding]
    action_queue: list[str]
    signal_count: int
