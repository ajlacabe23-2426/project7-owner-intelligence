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
- Invalid or unsupported feedback cannot silently resolve episodes, change rule
  severity, edit action queues, or claim customer value. Existing `/analyze`
  remains stateless and unchanged.

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
