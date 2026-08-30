# Project 7 — Owner Intelligence

Project 7 is an evidence-linked owner/operator intelligence system.

It is designed to turn fragmented business signals into a concise, prioritized operating brief without pretending that AI is the source of truth.

## V1 flow

```text
Source adapters
    ↓
Normalized business signals
    ↓
Deterministic priority / risk rules
    ↓
Evidence-linked findings
    ↓
Owner brief + action queue
```

## Current V1 capabilities

- Synthetic/local source adapter for reproducible demos
- Normalized signal schema
- Deterministic rule engine
- Priority levels: critical / high / medium / low
- Evidence references attached to every finding
- Owner brief generator
- Action queue
- FastAPI endpoints for health, analysis, and demo data
- Regression tests
- GitHub Actions CI

## Important product boundary

This repository is **not** evidence that businesses will pay for this product.

Technical validation and commercial validation are intentionally separated.

V1 answers: **Can we build a trustworthy, testable intelligence pipeline?**

Commercial discovery must separately answer: **Which owner/operator problem is valuable enough to pay to solve, what data sources matter, and what measurable outcome improves?**

## Why deterministic rules first?

The system should be able to explain why something was prioritized. AI can later help summarize or contextualize information, but it should not silently invent operational facts or become the sole authority for business-critical prioritization.

## Run locally

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation.

## Test

```bash
pytest -q
```

## Career-builder evidence

The project is intentionally structured to demonstrate:

- API/backend design
- data normalization
- adapter architecture
- rules engines
- explainability
- evidence provenance
- testing and CI
- security boundaries
- future AI orchestration without making AI the authority

## Project status

**Stage:** technical V1 foundation in progress.

See `docs/PROJECT_CHECKPOINT.md`, `docs/ARCHITECTURE.md`, and `docs/COMMERCIAL_GATES.md`.
