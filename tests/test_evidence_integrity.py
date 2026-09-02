from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from app.main import app
from app.models import BusinessSignal
from app.rules import evaluate_signals


PAYLOAD = {
    "id": "support-1", "source": "synthetic.support", "signal_type": "support",
    "observed_at": "2026-09-02T12:00:00Z", "metric": "open_urgent_items", "value": 4,
}
client = TestClient(app)


@pytest.mark.parametrize("value", ["not-a-number", True, -1, 3.5, "Infinity", "NaN"])
def test_invalid_count_returns_validation_error(value):
    response = client.post("/analyze", json=[{**PAYLOAD, "value": value}])
    assert response.status_code == 422


def test_overflow_json_returns_safe_422_without_raw_input():
    response = client.post(
        "/analyze",
        content='[{"id":"x","source":"s","signal_type":"support","metric":"open_urgent_items","observed_at":"2026-09-02T12:00:00Z","value":1e999}]',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert all(set(item) == {"loc", "msg", "type"} for item in response.json()["detail"])


def test_missing_receivable_amount_is_not_treated_as_zero():
    payload = {**PAYLOAD, "signal_type": "receivable", "metric": "invoice_days_overdue", "value": 60}
    assert client.post("/analyze", json=[payload]).status_code == 422


@pytest.mark.parametrize("amount", [None, "lots", True, -1, "Infinity"])
def test_invalid_receivable_amount_is_rejected(amount):
    payload = {**PAYLOAD, "signal_type": "receivable", "metric": "invoice_days_overdue", "value": 60,
               "metadata": {"amount": amount}}
    assert client.post("/analyze", json=[payload]).status_code == 422


def test_duplicate_delivery_produces_one_stable_finding():
    first = client.post("/analyze", json=[PAYLOAD]).json()
    retry = client.post("/analyze", json=[PAYLOAD, PAYLOAD]).json()
    assert first["findings"] == retry["findings"]
    assert first["action_queue"] == retry["action_queue"]
    assert retry["signal_count"] == 2  # Input count remains backward-compatible.


def test_conflicting_source_identity_fails_closed_in_either_order():
    conflict = {**PAYLOAD, "value": 0}
    for signals in ([PAYLOAD, conflict], [conflict, PAYLOAD]):
        response = client.post("/analyze", json=signals)
        assert response.status_code == 422
        assert response.json()["detail"] == "Conflicting observations share the same source and signal ID."


def test_ids_are_scoped_to_source_and_order_is_deterministic():
    other = {**PAYLOAD, "source": "synthetic.other"}
    forward = client.post("/analyze", json=[PAYLOAD, other]).json()
    reverse = client.post("/analyze", json=[other, PAYLOAD]).json()
    assert len(forward["findings"]) == 2
    assert forward["findings"] == reverse["findings"]
    assert len({finding["id"] for finding in forward["findings"]}) == 2


def test_equivalent_timestamp_offsets_share_finding_identity():
    signal = BusinessSignal(**PAYLOAD)
    equivalent = BusinessSignal(**{**PAYLOAD, "observed_at": "2026-09-02T14:00:00+02:00"})
    assert len(evaluate_signals([signal, equivalent])) == 1
    assert evaluate_signals([signal])[0].id == evaluate_signals([equivalent])[0].id


def test_findings_preserve_material_evidence():
    payload = {**PAYLOAD, "signal_type": "receivable", "metric": "invoice_days_overdue", "value": 60,
               "unit": "days", "entity_ref": "invoice-42", "metadata": {"amount": 2500}}
    finding = client.post("/analyze", json=[payload]).json()["findings"][0]
    assert finding["rule_version"] == "v1"
    evidence = finding["evidence"][0]
    assert evidence["amount"] == 2500
    assert evidence["entity_ref"] == "invoice-42"
    assert evidence["observed_at"] == "2026-09-02T12:00:00Z"
    sales = {**PAYLOAD, "signal_type": "sales", "metric": "daily_revenue", "value": 500, "baseline": 1000}
    evidence = client.post("/analyze", json=[sales]).json()["findings"][0]["evidence"][0]
    assert evidence["baseline"] == 1000


def test_naive_time_and_oversized_batch_are_rejected():
    assert client.post("/analyze", json=[{**PAYLOAD, "observed_at": "2026-09-02T12:00:00"}]).status_code == 422
    assert client.post("/analyze", json=[PAYLOAD] * 1001).status_code == 422


@pytest.mark.parametrize("value", [float("inf"), float("nan")])
def test_nonfinite_model_inputs_are_rejected(value):
    with pytest.raises(ValidationError):
        BusinessSignal(**{**PAYLOAD, "value": value})


def test_unsupported_metric_remains_accepted_without_fabricated_finding():
    signal = BusinessSignal(**{**PAYLOAD, "metric": "status", "value": "waiting"})
    assert evaluate_signals([signal]) == []


@pytest.mark.parametrize("baseline", [True, "unknown", -1, "Infinity"])
def test_invalid_revenue_baseline_is_rejected(baseline):
    payload = {**PAYLOAD, "signal_type": "sales", "metric": "daily_revenue", "baseline": baseline}
    assert client.post("/analyze", json=[payload]).status_code == 422
