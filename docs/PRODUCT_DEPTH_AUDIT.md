# Project 7 — Product Depth Audit

## Quality-first standard

Project 7 is not being optimized around monetization or generic "AI chief of staff" positioning. The goal is to build a trustworthy operational reasoning system that becomes more useful because it can prove what it knows, what it does not know, what changed, and whether prior recommendations were useful.

## Audit conclusion

The current architecture has good boundaries: normalization, deterministic rules, evidence references, tests, and an explicit AI boundary.

The shallow part is the intelligence itself. Most V1 findings are independent threshold checks over one metric at a time.

### Commodity / copied patterns

- morning/owner brief
- KPI threshold alerts
- revenue-vs-baseline alerting
- overdue invoice alerting
- review-rating alerts
- support backlog alerts
- prioritized action list
- dashboard-style synthesis

These patterns are already common in BI, finance, CRM, and AI-operations tools.

## Actual technical difficulty

The deeper problem is turning messy, time-varying, partially trustworthy evidence into decisions while preserving uncertainty and learning from outcomes.

The difficult system problems are:

1. evidence freshness and provenance
2. contradictory signals from different systems
3. missing-data detection
4. baseline quality and seasonality
5. temporal reasoning across changes, not isolated snapshots
6. cross-signal correlation
7. confidence/calibration
8. deduplicating repeated findings
9. distinguishing a new problem from the same unresolved problem
10. recording whether an operator acted, ignored, or rejected advice
11. measuring what happened after an action
12. preventing recommendation loops that repeat noise
13. tenant isolation and source-level authorization

## Product pivot: Decision Provenance & Operational Reasoning

Project 7 should answer:

**What changed, what evidence supports it, how confident are we, what decision does it affect, what did we recommend before, what did the operator do, and what happened afterward?**

A "brief" becomes one presentation surface, not the product.

## New core model

Project 7 should evolve toward:

- Observation — raw normalized fact from a source
- EvidenceSet — observations used together
- EvidenceQuality — freshness, completeness, conflict state
- Baseline — historical/contextual expectation with provenance
- Finding — interpretation of evidence
- DecisionContext — why a finding matters operationally
- Recommendation — proposed action with confidence and assumptions
- OperatorDisposition — acted / dismissed / deferred / needs-more-info
- OutcomeObservation — what changed after disposition/action
- FindingEpisode — persistent issue across time, avoiding duplicate alerts
- ReasoningTrace — policy/rule/version and evidence chain

## Quality gates

A strong version should prove:

- stale evidence cannot masquerade as current evidence
- conflicting sources are surfaced rather than averaged away
- repeated observations do not create duplicate "new" problems
- recommendations cite evidence and assumptions
- confidence decreases when evidence quality decreases
- historical findings can be reopened/resolved
- operator feedback changes future prioritization only through explicit, inspectable logic
- outcome tracking distinguishes correlation from claimed causation
- the system can explain why an item moved up or down in priority
- one tenant can never access another tenant's source data or reasoning traces

## What to stop optimizing

- number of KPIs
- number of source connectors
- generic morning-brief polish
- generic LLM summaries
- arbitrary alert thresholds
- broad "run your whole business" positioning

## What makes this project worth building

The durable technical value is in temporal reasoning, data provenance, uncertainty, contradiction handling, feedback loops, episode tracking, explainability, and safe human-in-the-loop decision support.

That is the new center of Project 7.
