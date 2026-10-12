"""Exercise Project 7's real local API with synthetic evidence and returned IDs.

Run against a loopback-only demo server. Appends a uniquely named synthetic
episode and feedback; does not reset or delete existing data.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class WorkflowError(RuntimeError):
    pass


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_base_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "::1"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise WorkflowError("Use an HTTP loopback URL such as http://127.0.0.1:8000.")
    try:
        parsed.port
    except ValueError as error:
        raise WorkflowError("Invalid loopback port.") from error
    return value.rstrip("/")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise WorkflowError(message)


def run_lab(base_url: str) -> dict:
    base_url = validate_base_url(base_url)
    # Never send synthetic requests through environment proxies or redirects.
    opener = build_opener(ProxyHandler({}), NoRedirects())

    def request(method: str, path: str, payload=None, expected: int = 200):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = Request(base_url + path, data=body, method=method,
                      headers={"Content-Type": "application/json"})
        try:
            with opener.open(req, timeout=10) as response:
                status, raw = response.status, response.read()
        except HTTPError as error:
            status, raw = error.code, error.read()
        except URLError as error:
            raise WorkflowError("Local API is unavailable; start the loopback demo server first.") from error
        require(status == expected, f"{method} {path}: expected HTTP {expected}, received {status}.")
        try:
            return json.loads(raw)
        except (ValueError, UnicodeError) as error:
            raise WorkflowError("Local API returned invalid JSON.") from error

    require(request("GET", "/health") == {"status": "ok"}, "Unexpected health response.")
    run_id = "operator-lab-" + uuid.uuid4().hex
    before = {
        "id": run_id + "-before",
        "source": "synthetic.operator-lab",
        "signal_type": "support",
        "observed_at": (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat(),
        "metric": "open_urgent_items",
        "value": 4,
        "entity_ref": run_id,
        "metadata": {},
    }
    brief = request("POST", "/analyze/episodes", [before])
    matches = [
        finding for finding in brief["findings"]
        if finding.get("episode_id")
        and any(e["signal_id"] == before["id"] for e in finding["evidence"])
    ]
    require(len(matches) == 1, "Expected exactly one episode for the fresh synthetic observation.")
    episode_id = matches[0]["episode_id"]
    route = "/episodes/" + quote(episode_id, safe="")
    episodes = request("GET", "/episodes")
    require(any(e["episode_id"] == episode_id for e in episodes), "Created episode is missing from the list.")

    decision = {"event_id": run_id + "-decision", "status": "acted", "reason_code": "assigned-owner"}
    first = request("POST", route + "/dispositions", decision, 201)
    replay = request("POST", route + "/dispositions", decision, 201)
    require(first == replay, "Exact disposition replay must return the original event.")
    request("POST", route + "/dispositions", {**decision, "status": "dismissed"}, 409)

    after = {
        **before,
        "id": run_id + "-after",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "value": 1,
    }
    outcome = {"event_id": run_id + "-outcome", "disposition_event_id": decision["event_id"], "signal": after}
    observed = request("POST", route + "/outcomes", outcome, 201)
    require(observed["interpretation"] == "observation-only", "Outcome must remain observational.")
    require(request("POST", route + "/outcomes", outcome, 201) == observed, "Outcome replay changed the event.")
    feedback = request("GET", route + "/feedback")
    require(len(feedback["dispositions"]) == len(feedback["outcomes"]) == 1, "Replay created duplicate feedback.")
    require(feedback["episode"]["current_status"] == "open", "Feedback must not automatically resolve the episode.")
    require("not proof" in feedback["interpretation_note"], "Feedback is missing its causality limitation.")
    request("GET", "/episodes/" + run_id + "-missing/feedback", expected=404)

    resolved = request("POST", route + "/resolve", {"reason_code": "synthetic-lab-complete"})
    require(resolved["current_status"] == "resolved", "Explicit resolution did not persist.")
    final = request("GET", route + "/feedback")
    require(final["episode"]["current_status"] == "resolved", "Reload lost the explicit resolution.")
    require(final["dispositions"] == feedback["dispositions"], "Resolution changed decision history.")
    require(final["outcomes"] == feedback["outcomes"], "Resolution changed outcome history.")
    return {
        "result": "PASS",
        "scope": "synthetic local API only",
        "episode_id": episode_id,
        "feedback_url": base_url + route + "/feedback",
        "checks": [
            "create and list using returned episode_id", "valid disposition and exact replay",
            "conflicting event rejected with 409", "post-action outcome and exact replay",
            "feedback remains observation-only and open", "unknown episode rejected with 404",
            "explicit resolution and feedback reload preserve history",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    try:
        report = run_lab(args.base_url)
    except (WorkflowError, KeyError, TypeError) as error:
        print(f"Operator lab FAIL: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
