# Security Policy

Project 7 is a local/synthetic owner-intelligence research and portfolio project, not a production business-operations service.

## Reporting a vulnerability

Do not publish credentials, private business data, exploit payloads, database contents, or other sensitive evidence in a public issue. If GitHub private vulnerability reporting is available, use it; otherwise contact the repository owner privately with the minimum non-destructive reproduction information needed.

## Current safety boundaries

- Demo and evidence sources are synthetic/local.
- Deterministic rules remain the authority for prioritization; AI is not the source of operational facts.
- Main is not an authenticated or publicly deployable multi-tenant service.
- CI and the scheduled security monitor scan reachable Git history, repository workflow posture, and Python dependency advisories.
- Local environment files and secret-like key material must not be tracked.

## Before production use

Production use requires authenticated operator access, tenant isolation, managed persistence and backups, data-source authentication, privacy/retention controls, network abuse protection, auditable provider integrations, recovery testing, and independent security review.

Security testing does not authorize access to systems or data you do not own.
