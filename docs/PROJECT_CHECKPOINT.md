# Project 7 — Project Checkpoint

## Verified repository state

Repository initialized with a V1 owner-intelligence backend foundation.

## Implemented

- normalized business signal schema
- severity model
- evidence references
- deterministic rules for receivables, support backlog, ratings, revenue variance, and unassigned appointments
- owner brief generator
- action queue
- synthetic demo source
- FastAPI API
- regression tests
- GitHub Actions CI definition
- architecture documentation
- commercial validation gates

## Current technical boundary

This V1 intentionally uses synthetic data only.

No real Gmail, calendar, accounting, CRM, support, review, or banking credentials are required or accepted by the current implementation.

## Verification required

- confirm GitHub Actions workflow result
- if green, record test count and run evidence
- if red, inspect job logs and repair

## Manual evidence later

When AJ is at a computer:

1. clone repository
2. create virtual environment
3. install requirements
4. run `pytest -q`
5. run `uvicorn app.main:app --reload`
6. open `/docs`
7. call `/demo/brief`
8. capture screenshots showing the evidence-linked findings and action queue

These screenshots are portfolio evidence, not commercial validation.

## NEXT

- harden the technical V1 only where justified by tests/security
- investigate specific owner/operator information failures before selecting real integrations
- compare existing dashboards/BI/CRM reporting against any discovered pain
- define a pilot only after a measurable problem is established

## LATER

- validated production source adapter
- organization configuration
- persistence
- auth/authz and tenant isolation
- observability
- optional AI synthesis layer

## DO NOT DO YET

- connect random APIs because they are available
- claim the system saves money without baseline evidence
- claim owners need a morning brief without discovery evidence
- introduce multi-tenant production data before isolation/security controls exist
- let an LLM invent findings that are not supported by source evidence
