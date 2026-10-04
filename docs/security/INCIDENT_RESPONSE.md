# Project 7 Incident Response

Updated: 2026-10-02

## Priorities

1. Freeze promotion when evidence integrity or access boundaries are uncertain.
2. Protect credentials and business evidence.
3. Preserve exact source identifiers, timestamps, and commit evidence without exposing secrets.
4. Restore a known-good candidate and rerun deterministic verification.

## Credential exposure

- Never paste the suspected value into issues, commits, CI logs, or chat.
- Identify provider and affected scope.
- Revoke/rotate through the provider control plane when applicable.
- Scan reachable Git history and relevant artifacts.
- Verify the old credential is invalid before closing the incident.

## Evidence-integrity incident

Unexpected supersession behavior, mutated finding history, cross-episode contamination, stale evidence driving current actions, or inferred causality must block promotion. Preserve the input evidence and exact commit, reproduce locally, and do not present the affected finding as current until consistency is restored.

## Repository/workflow incident

Review Action SHAs, token permissions, checkout credential handling, dependency changes, evidence adapters, storage paths, and API exposure. Rerun history secret scan, repository baseline, dependency audit, compile checks, and the complete test suite.

## Recovery evidence

Record affected commit, corrected commit, passing verification runs, known limitations, and any external action still requiring owner approval.
