# Architecture

## 1. The one invariant everything else follows

**The backend owns reality. The browser is a view over server-authoritative state.**

Concretely:
- Game state (discovered evidence, suspect emotional state, claims,
  contradictions, verdict) lives only in PostgreSQL, as an append-only
  event log plus derived projections.
- The client never receives a fact it isn't authorized to see. There is no
  "hidden field, just don't render it" — unauthorized facts are not
  serialized into any API response in the first place.
- LLM output is *narration*, never *decision*. Whether a suspect lies,
  evades, or confesses is decided by a deterministic rule engine before
  the LLM is called. The LLM's job is to phrase that decision naturally,
  and its output is validated against an allow-list of facts before it
  ever reaches the player.

## 2. Components and responsibilities

| Component | Responsibility | Must never do |
|---|---|---|
| `backend/app/domain` | Pure business rules: case models, validation, scoring, behavior state machine | Touch the network, DB, or an LLM client |
| `backend/app/repositories` | Load/persist data (case files, sessions, events) | Contain game logic |
| `backend/app/services` | Orchestrate domain + repositories into use cases (start session, inspect object, interrogate) | Call an LLM provider SDK directly |
| `backend/app/ai` | Provider-abstracted LLM client, prompt building, knowledge scoping, output validation | Decide game facts or bypass the validator |
| `backend/app/api` | HTTP/SSE boundary, request/response DTOs, auth | Contain business logic |
| `backend/app/workers` | Async job consumers (evidence analysis, claim repair) | Be the only path to correctness (must be idempotent/replayable) |
| `frontend` | Render server-provided state, collect player input | Store or infer hidden game facts client-side |
| `cases/` | Versioned, immutable mystery content as data (JSON) | Contain code or be mutated after publish |

## 3. Sync vs. async boundaries

- **Sync (request/response):** exploration, notebook reads, accusation
  submission — anything the player is actively waiting on and that
  completes in well under a second.
- **Async (queued job):** evidence lab analysis, claim extraction repair —
  anything that can plausibly take longer or that we want to survive a
  crash mid-flight. These go through a durable queue (RabbitMQ, from Day
  11 onward) with idempotent completion handlers.
- **Streamed (SSE):** suspect dialogue generation — the player waits, but
  we want to show "thinking" status rather than a spinner, and we need
  resumability if the connection drops.

## 4. Why Python/FastAPI and not the Node.js stack

You already know Node/Postgres/Redis/RabbitMQ. The concepts transfer
almost 1:1 (async request handlers, connection pooling, pub/sub queues).
The reasons for Python here specifically:
- The AI/ML ecosystem (embeddings, pgvector clients, evaluation tooling)
  is more mature in Python.
- FastAPI + Pydantic v2 gives the same "typed request/response" experience
  as a well-typed Express + Zod setup, but with less boilerplate for
  OpenAPI generation.

## 5. Data ownership summary

| Data | Owned by | Never derived from |
|---|---|---|
| Case truth (culprit, motive, hidden facts) | `cases/*/v*/*.json`, loaded read-only at runtime | Any LLM call |
| Session state (discovered evidence, verdict) | PostgreSQL event log | Client-supplied state |
| Suspect dialogue text | LLM, but validated post-generation | — |
| Suspect *behavior* (lie/evade/reveal) | Deterministic rule engine (`behavior_policy.py`, Day 24) | LLM judgment |

## 6. Change log
- 2026-08-01: Initial architecture, Day 1.