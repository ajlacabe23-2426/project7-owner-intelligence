"""Contract tests for the read-only synthetic investor dashboard.

These exercise the actual API endpoint used by the page, without creating
customer records, outbound side effects, or claiming visual browser acceptance.
"""
from fastapi.testclient import TestClient

from app.main import app


def test_root_serves_local_dashboard_with_clear_synthetic_boundary():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    body = response.text
    assert "SYNTHETIC / LOCAL DEMO" in body
    assert "Traceable source evidence" in body
    assert 'fetch("/demo/signals"' in body
    assert 'fetch("/analyze"' in body
    assert "No automatic" in body
    assert "real accounting" in body
    assert "https://" not in body


def test_dashboard_analyzes_same_synthetic_source_snapshot():
    with TestClient(app) as client:
        source_response = client.get("/demo/signals")
        assert source_response.status_code == 200
        sources = source_response.json()
        assert all(signal["source"].startswith("synthetic.") for signal in sources)
        review = client.post("/analyze", json=sources)
    assert review.status_code == 200
    brief = review.json()
    assert brief["signal_count"] == len(sources)
    assert brief["findings"]
    source_by_id = {signal["id"]: signal for signal in sources}
    assert len(source_by_id) == len(sources)
    for finding in brief["findings"]:
        for ref in finding["evidence"]:
            signal = source_by_id[ref["signal_id"]]
            assert ref["source"] == signal["source"]
            assert ref["metric"] == signal["metric"]
            assert ref["observed_value"] == signal["value"]
            assert ref["observed_at"] == signal["observed_at"]
