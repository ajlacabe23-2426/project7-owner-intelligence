# Project 7 Quality-First Roadmap

## NOW — Make evidence trustworthy

1. Add evidence freshness metadata and staleness rules.
2. Add source reliability / evidence-quality representation.
3. Detect missing expected observations.
4. Detect conflicting observations for the same metric/entity/window.
5. Replace one-shot finding IDs with persistent finding episodes.
6. Store first_seen, last_seen, recurrence count, and resolution state.
7. Add explicit rule/policy version to every reasoning trace.
8. Add tests for stale, conflicting, duplicate, and out-of-order observations.

## NEXT — Temporal and cross-signal reasoning

- rolling baselines
- seasonality-aware comparisons
- trend/change-point detection
- correlated evidence sets
- causal-language guardrails
- confidence derived from evidence quality
- priority changes that can be explained

## NEXT — Human feedback loop

- acted / dismissed / deferred / needs-more-info
- reason for operator disposition
- outcome observations after action
- recurrence after action
- false-positive tracking
- recommendation usefulness metrics
- inspectable adjustment rules rather than opaque personalization

## NEXT — Security and persistence

Before real customer data:

- authenticated users
- tenant model
- row-level/tenant isolation
- source-level least privilege
- immutable reasoning/audit history
- retention/deletion controls
- secret management
- rate limits
- connector failure/replay handling
- cross-tenant negative tests

## LATER — AI synthesis

AI may summarize or explain verified reasoning traces. It should not become the source of facts or silently create unsupported findings.

## DELETE / DE-EMPHASIZE

- generic "AI chief of staff" feature expansion
- dashboard-card accumulation
- random source integrations
- more single-metric threshold rules solely to increase feature count
- monetization-driven roadmap choices

## Definition of a strong Project 7

A strong Project 7 can reconstruct how a recommendation was reached, show the quality and conflicts in its evidence, track the problem across time, record human disposition, observe subsequent outcomes, and learn through explicit verifiable mechanisms rather than merely producing a polished daily summary.
