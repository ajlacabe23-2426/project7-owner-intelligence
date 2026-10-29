# Project 7: October 30 synthetic investor dashboard

This feature branch adds a **local-only, read-only visual operating brief** at `http://127.0.0.1:8000/`. It is a presentation layer over the existing synthetic data and deterministic analysis engine, not a live business integration. **No production login or multi-tenant isolation exists. Do not expose this application to the public internet or use customer data.**

## Exact rehearsal

From the Project 7 repository checkout:

```bash
python -m venv .venv
# macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`. The page loads `/demo/signals` and submits that **same snapshot** to `POST /analyze` rather than mixing independently created timestamps. It rejects non-synthetic sources, duplicate IDs and rule evidence mismatches before displaying a brief. Nothing written to disk from this visual read-only path.

### Four-minute visual story

1. Explain that every input is fictional: accounting, support, sales, calendar and reviews.
2. Point to **Observed source signals**, **Flagged exceptions**, and **Proposed priority actions**. The counts are responses from the real local API; they are not estimated.
3. Select a high-severity finding. Read its deterministic rationale, rule version, confidence, observed value and synthetic source identity. Point to the matching input in the provenance panel.
4. Show the operator queue as **suggested** actions, not automated activity or demonstrated revenue improvement.
5. Click **Refresh synthetic brief**. Verify status and results update. Then open `/docs` or run `python scripts/demo_operator_feedback.py --base-url http://127.0.0.1:8000` to demonstrate actual human decision/outcome tracking separately. That script persists synthetic episode state; use a disposable `OWNER_INTELLIGENCE_DB_PATH` and do not reuse a real database.

## Verification and fallback

Automated `tests/test_dashboard.py` checks HTML routing, synthetic-only labeling, the actual analyze-contract endpoint and evidence/source consistency. GitHub CI tests the Python API and static file availability; it **does not** constitute visual browser acceptance. On your presentation machine check screen share, responsive layout, tab/click behavior, developer-console errors and result readability. If the UI fails, show the API brief in `/docs`, together with the synthetic source record and its evidence ID.

## Boundaries

No real company source adapters; no public hosting, auth, team permissions, billing, customer data, causal ROI evidence, or unattended business actions. Any external pilot would require separate permissions, instrumentation, operational security and human approval.

## Proposed buyer questions

- Which daily decision is slowed by fragmented source systems?
- What one source could be authorized for a narrow proof of value?
- Who acts on these priorities and what is the baseline response time?
- What evidence quality and approval workflow would the buyer require?
