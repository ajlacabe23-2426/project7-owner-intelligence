# October 31 commercial demo — Owner Intelligence

**Status:** synthetic demo and buyer-discovery guide, not production/ROI proof. **Candidate dependency:** [integration PR #26](https://github.com/ajlacabe23-2426/project7-owner-intelligence/pull/26) at `674b4be935dcafb8753128caf2be16c3723023d8`; any newer unmerged test branch needs its own exact-head CI result.

## Product framing

“Owner Intelligence makes scattered operating signals easier to inspect, prioritize and respond to, with an evidence trail.”

The current engine demonstrates local source normalization, explicit rule logic, linked evidence, operator decision logging and persisted feedback. All standard demo inputs are **synthetic**. No real company API credentials, owner data, connected ERP/CRM, hosted tenant isolation, or production authentication exist here.

## Repeatable 4-minute demo

1. **Show source facts:** in a local, isolated environment open `/demo/signals`. State that the accounting/support/sales/calendar/reviews data is fictional. No production account connected.
2. **Show brief:** open `/demo/brief` or `/docs`. Show the highest-priority finding, its rule and specific evidence ID, observed value and timestamp.
3. **Show action boundary:** explain that the action queue is a proposed operator priority, not a claim that automation took action.
4. **Demonstrate human response:** run `python scripts/demo_operator_feedback.py --base-url http://127.0.0.1:8000` against the owner-approved loopback-only service. Capture the returned synthetic episode ID, its explicit operator disposition and outcome observation; explain the post-action value is not causality or realized ROI.
5. **Restart/persist:** use the existing regression `tests/test_restart_acceptance.py` to verify that feedback survives an actual stop/start. Do not call memory-only state durable.
6. **Negative example:** show that a future-dated synthetic support observation is flagged and cannot create an action. Explain staleness/source quality limitations.

## Before claiming meeting readiness

- [ ] CI green at final candidate SHA; tests include the explicit meeting evidence gate
- [ ] Synthetic evidence sources and time visible (no ambiguous “real-time business data” claim)
- [ ] Trace the visible recommendation to exact synthetic source IDs and deterministic rule
- [ ] Operator outcome explicitly marked observation-only, never “the AI improved results”
- [ ] Actual localhost/device demonstration or recorded non-secret fallback tested
- [ ] No real customer's data and no hosted auth/integrations implied
- [ ] Business problem interviews and measurable baseline defined

## Five discovery questions for the investor/client

1. Which operating decision is delayed because information lives in multiple systems?
2. Who is accountable for that decision today, and how often does the delay happen?
3. What would a genuinely useful daily or weekly owner brief need to contain?
4. Which sources could you **authorize** for a narrow pilot (and can you provide sanitized sample data first)?
5. What measurable improvement would justify paying for this? E.g., time spent finding overdue items, not a fabricated revenue uplift.

## Narrow potential pilot offer (not yet sold)

One authorized operational signal category and one actionable brief reviewed by a human over a mutually agreed observation period. Track baseline response time / review minutes before and during the pilot; confirm instrumentation and resource/hosting cost first. Product-market fit, pricing and data rights must be validated separately.

**Hard stop:** do not accept real client data or present this as authenticated, multi-tenant SaaS. Follow [commercial gates](COMMERCIAL_GATES.md). No deployment, merges or hosted changes by this document.
