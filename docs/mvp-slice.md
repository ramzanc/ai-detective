# MVP Vertical Slice

This is the one complete path the project must support before any other
feature work is considered in-scope. Every day of the build guide either
builds a piece of this slice or hardens it. Nothing outside this slice
belongs in the MVP backlog.

## The slice

1. **Start** — player creates a guest session for case `ashcroft-manor-v1`.
2. **Inspect the watch** — player explores a location, inspects the broken
   watch, and it's added to their evidence inventory.
3. **Interview Maya** — player opens an interrogation with suspect Maya and
   asks about her alibi; she gives a scoped, validated, in-character
   response (terrace claim).
4. **Present the door log** — player presents evidence that contradicts
   Maya's terrace claim; her behavior shifts (denial -> partial admission)
   under deterministic evidence-pressure rules.
5. **Accuse** — player submits a structured accusation (culprit, motive,
   weapon, time, supporting evidence).
6. **Verdict** — backend scores the accusation deterministically against
   the pinned case rubric and returns a reproducible result.

## Why this slice, specifically

It touches every architectural seam in one path:
- deterministic content (the case package)
- server-owned state (the event log)
- async-capable but sync-shaped work (evidence discovery)
- the AI boundary (interrogation) with its full pipeline: knowledge
  scoping -> behavior selection -> generation -> validation -> fallback
- deterministic scoring untouched by AI (the verdict)

If this slice works end to end, the hardest architectural problems in the
whole project are proven out. Everything after (Milestones 5-7) is depth,
not new categories of risk.

## Explicitly out of scope for MVP

- Procedural/generated case content — cases are hand-authored and versioned.
- Multiplayer or shared sessions.
- Voice input/output.
- 3D or game-engine rendering — this is a web app.

## Traceability

This slice is the basis for the Day 14 deterministic milestone (no AI) and
the Day 28 AI milestone (interrogation added). See the build guide's
roadmap section for the full day-by-day breakdown.