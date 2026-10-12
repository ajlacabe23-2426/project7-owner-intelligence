Task ID: P7-EPISODE-OPERATOR-LAB-2026-10-12
Title: Make valid local episode feedback reproducible without guessing IDs
Status: READY_FOR_AJ
Risk Tier: TIER_2
Base SHA: c8acbbcf685bd79aa7b0f8b5bb90716de3e2c5cc

## Objective
Resolve the episode-ID usability/verification gap by providing a loopback-only synthetic walkthrough using IDs actually returned by the existing API.

## Authorized implementation paths
- `scripts/demo_operator_feedback.py`
- `docs/OPERATOR_FEEDBACK.md`
- `.codex/CURRENT_TASK.md`

## Authorized test paths
- `tests/test_operator_lab.py`

## Acceptance criteria
- Fresh synthetic evidence creates a real episode; no guessed names or IDs.
- Disposition/outcome exact replays preserve one event each; conflicting events and unknown episodes fail closed.
- Feedback stays observation-only and open until explicit synthetic resolution.
- Final feedback reload preserves resolution and complete history.
- Helper allows HTTP loopback literals only, bypasses proxies and refuses redirects; no reset/delete or remote requests.
- Real HTTP regression uses a temporary database and checks a second independent run.
- Existing unit/API tests, compile, pip health, dependency audit and CI/security pass at frozen candidate.
- Manual Lenovo execution remains NOT_RUN until AJ runs this candidate.

## Explicit non-goals
- No API implementation, rule, persistence schema, auth/tenant, source-provider or hosted changes.
- No real customer data, commercial claims, production deployment or merge.

## Required gates
- CI including Python compilation, pip consistency, dependency audit and pytest.
- Security monitor: repository baseline and reachable-history credential scan.
- Read-only scope/security review and exact candidate SHA report.
