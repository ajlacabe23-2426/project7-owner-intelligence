# Project 7 Architecture

## Purpose

Project 7 converts fragmented business signals into an evidence-linked owner/operator brief.

The architecture intentionally separates data ingestion, normalization, decision logic, synthesis, and presentation so that integrations can change without rewriting the intelligence core.

## V1 components

### 1. Source adapters

Adapters translate source-specific data into `BusinessSignal` records.

Current V1 uses synthetic data only. Future adapters may target accounting, CRM, calendar, support, review, or sales systems **only after a validated use case requires them**.

### 2. Normalized signal model

Every signal includes:

- stable signal ID
- source identifier
- signal type
- observation timestamp
- metric name
- observed value
- optional baseline
- optional unit
- optional entity reference
- source metadata

Normalization prevents downstream logic from becoming coupled to vendor APIs.

### 3. Deterministic rule engine

V1 rules convert normalized signals into findings.

Every finding contains:

- severity
- explanation
- recommended action
- exact evidence references

The system must be able to answer: **Why was this surfaced?**

### 4. Brief generator

The brief generator sorts findings by severity, produces a headline, and creates an action queue from critical/high findings.

### 5. API layer

FastAPI exposes:

- `GET /health`
- `GET /demo/signals`
- `GET /demo/brief`
- `POST /analyze`

## AI boundary

AI is not required for V1 correctness.

Future AI may:

- summarize verified findings
- explain context in natural language
- cluster related evidence
- generate owner-facing wording

AI must not silently fabricate metrics, evidence, source records, or business-critical findings.

## Security boundary

The current demo contains synthetic data only and is not production-ready.

Before real customer data:

- authentication and authorization
- tenant isolation
- secret management
- source-level least privilege
- encryption in transit/at rest
- audit logs
- retention/deletion controls
- PII minimization
- rate limiting
- connector failure handling
- provenance validation

must be designed and tested.

## Scalability principle

A commercial system should be mostly configuration + adapters, not customer-specific rewrites.

Target future decomposition:

```text
adapter package
    -> normalized schema
    -> reusable rule framework
    -> organization configuration
    -> reusable brief/action API
```

If a customer requires a completely different core pipeline, that is evidence of consulting work rather than a scalable product pattern.
