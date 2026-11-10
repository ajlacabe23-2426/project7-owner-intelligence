# Project 7 — Owner Intelligence roadmap

Updated: 2026-10-10
Stage: synthetic/local prototype; **not** an authenticated public service or proven commercial product.

## Product truth

The README documents synthetic source adapters, deterministic risk/priority rules, evidence-linked owner briefs and local operator dispositions/outcomes. This planning update does **not** verify current CI, deployed runtime, or business adoption.

## NOW (ordered)

1. **Reproduce evidence pipeline** — exercise synthetic ingest -> normalized signal -> finding -> owner brief. Accept only if repeated inputs yield stable evidence references and classifications, and corrupted/mismatched source IDs are rejected.
2. **Strengthen negative-case operator feedback** — regression-test duplicate dispositions, missing or conflicting outcome evidence, and inability to infer causality from observational feedback. Require deterministic replays and explicit uncertainty language.
3. **Produce an operator-demo evidence packet** — scripted synthetic dataset, steps and test log linked to an exact SHA. Record tests as NOT_RUN until executed.

## NEXT

- Authenticated organization/role identity, data-source permissions, privacy/retention, and tenant-isolation tests **before** real data/public hosting.
- Validated integration adapters and source latency/failure behavior; separate facts from estimates.
- Commercial interviews/validation separately from technical readiness.

## LATER / PARKED

- Trend dashboards, configurable policy rules, integrations, paid accounts — only after correctness and trust boundaries.

## Release gates

Unit/API integration; provenance and source consistency; synthetic/live labeling; repeatable operator feedback; security/identity before external access. Merge/deploy only with explicit approval. Do not claim revenue outcomes.
