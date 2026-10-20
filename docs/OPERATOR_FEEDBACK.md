# Project 7 — Operator decisions and outcomes (local demo)

This milestone adds an append-only operator feedback trail. The system may record an
operator's disposition and an observed result, but must **not** infer that a recorded
action caused an observed change.

## What is implemented

- `POST /episodes/{episode_id}/dispositions`: append an `acted`, `dismissed`,
  `deferred`, or `needs-more-info` human decision with a reason code.
- `POST /episodes/{episode_id}/outcomes`: append a new, provenance-linked
  `BusinessSignal` recorded after a referenced `acted` disposition. Its metric
  and entity must match the episode's latest source evidence.
- `GET /episodes/{episode_id}/feedback`: reconstruct the current episode, all
  decisions and post-action observations in stable recorded order.
- Client-provided event IDs are idempotent: exact retries return the original
  recorded event; changed or cross-type IDs produce HTTP 409.
- A single `(source, signal ID)` cannot create multiple outcomes by changing
  `event_id`. Materially future-dated outcomes are rejected using the same
  five-minute source-clock tolerance as evidence quality checks; exact accepted
  event replays remain idempotent.
- Invalid or unsupported feedback cannot silently resolve episodes, change rule
  severity, edit action queues, or claim customer value. Existing `/analyze`
  remains stateless and unchanged.

## One-command synthetic verification

An episode ID is the identifier returned by `POST /analyze/episodes` or
`GET /episodes`. It is not an episode name or a finding title.
`/demo/brief` and `/analyze` are stateless; they do not create an episode
that can receive feedback. An unknown ID returning 404 tests rejection only,
not the valid episode workflow.

In your activated environment, start a loopback server in one terminal:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal in this repository, using the same Python environment:

```powershell
python scripts/demo_operator_feedback.py
```

The lab creates one uniquely named synthetic support episode, obtains its
actual ID, records an acted decision and post-action observation, checks exact
replays and conflicting/unknown IDs, and explicitly resolves that synthetic
episode. It prints PASS only after feedback reload preserves the complete
trail. The printed feedback URL can be opened in your browser.

This appends synthetic local records; it does not reset/delete existing data.
Use a disposable local demo instance. The helper refuses remote URLs,
credentials, redirects and environment proxies. A failure exits with code 1;
it does not claim partial completion as PASS.

For a different local port, use
`python scripts/demo_operator_feedback.py --base-url http://127.0.0.1:8001`.

## Hands-on experiment

1. Launch locally with `uvicorn app.main:app --host 127.0.0.1 --port 8000`.
2. Open `http://127.0.0.1:8000/docs` and POST fresh synthetic support evidence
   to `/analyze/episodes`. Copy the returned `episode_id`.
3. POST a disposition with `event_id: "demo-action-1"`,
   `status: "acted"`, and `reason_code: "assigned-owner"`.
4. Repeat the same request: the original event and timestamp should be returned
   without a duplicate.
5. POST an outcome with `event_id: "demo-outcome-1"`,
   `disposition_event_id: "demo-action-1"`, and a **new** synthetic support
   signal for the same metric/entity, observed after the action.
6. GET `/episodes/{episode_id}/feedback` to examine the evidence trail. The
   episode remains open until a human explicitly resolves it; the outcome is an
   observation, not proof of the action's effect.

The REST schema validates identifiers, timestamps, metric shape and the
post-action provenance boundary. It does not verify that a human actually took
the action or that an external source is authentic; this must be handled by
future authenticated connectors and explicit source policy.

## Non-negotiable boundaries

**Synthetic/local use only.** The API has no authentication, organization
authorization, tenant isolation, source verification, personal-data retention
policy, or commercial access controls. Do not expose it publicly, connect
customer accounts, use actual credentials, or ingest customer data. Do not
interpret an outcome as causal impact or count it as commercial validation.
Deployment, production persistence, and real integrations remain gated by
`docs/COMMERCIAL_GATES.md`.
