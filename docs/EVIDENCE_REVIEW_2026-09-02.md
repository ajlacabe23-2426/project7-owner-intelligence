# Owner Intelligence evidence review — 2026-09-02

## Result

Implemented validated rule inputs, source-scoped observation deduplication,
conflict rejection, reproducible finding IDs and expanded evidence provenance.
This implements a bounded part of the existing decision-provenance roadmap.

## Confirmed defects

Baseline reproduction proved that nonnumeric support counts caused HTTP 500,
duplicate observations produced duplicate alerts, and replay generated new UUIDs.
Receivable amount and revenue baseline were used to reach conclusions but absent
from returned evidence. Missing receivable amounts were silently treated as zero.

## Contract

- Known numeric metrics require finite, non-negative numbers; counts/days require
  whole numbers and ratings must fall within 0–5. Boolean metrics cannot stand in
  for counts. Receivables require a valid `metadata.amount`.
- Observation timestamps require a timezone. Evidence timestamps are returned in UTC.
- `(source, id)` identifies an immutable observation within a batch. Identical
  repeats are evaluated once. Conflicting content under that identity returns
  HTTP 422; neither input order nor last-write-wins chooses an answer.
- Different sources may reuse IDs. A changed observation should receive a new ID.
- Finding identity derives from rule version and canonical observation contents;
  input ordering does not change the ordered findings. `generated_at` remains the
  actual analysis time. `signal_count` continues to count submitted records.
- Evidence includes observed time, baseline, unit, entity reference and the amount
  used by receivable rules. Existing score/severity thresholds are unchanged.
- Analysis accepts at most 1,000 observations per batch. Unknown metrics remain
  representable but produce no invented rule result.

## Validation

`python -m pytest -q`: 34 tests passed.
`python -m compileall -q app tests` and `git diff --check`: passed.
Coverage includes invalid numeric values, missing amounts, source ID collisions,
reversed input order, exact duplicates, equivalent timestamp offsets, evidence
completeness, invalid baselines and maximum batch length.

## Remaining boundaries

This is a synthetic/demo service. Authentication, tenant isolation, durable
observations, finding episodes, operator dispositions and outcome tracking remain
unfinished. Reproducible IDs do not themselves provide durable episode tracking.

Freshness policies and contradictions between different observations/sources are
not evaluated yet. UTC timestamps expose age; they do not establish freshness.
Descriptions now attribute open counts to the supplied observation instead of
claiming those counts are current. Baselines still lack independent source
verification. Rule version identifies current fixed logic, not a calibration claim.

## Manual check

Submit the same signal twice and replay the batch; verify one unchanged finding.
Change the value while retaining its source/ID in the same batch; expect 422.
Inspect an overdue invoice finding for amount, observation time and entity reference.
