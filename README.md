# AI Detective Game

A backend-first, AI-engineered detective game. The player explores a manor,
interrogates suspects powered by a constrained LLM, gathers evidence, and
submits a final accusation that is scored deterministically.

## Why this project exists

This is an engineering portfolio project. The interesting problem isn't
"call an LLM" — it's building a system where an LLM can generate natural,
in-character dialogue *without* ever being trusted to decide facts, state,
or the outcome of the game. The backend owns the truth. The AI narrates
within limits the backend enforces.

## Core invariant

> The backend owns canon. The browser never receives hidden truth.
> An LLM never decides the culprit, evidence fact, confession threshold,
> unlock, or verdict.

Every architectural decision in this repo traces back to that sentence.
See `docs/architecture.md` for how it's enforced in code.

## Repository layout

backend/ Python 3.12 / FastAPI / SQLAlchemy async — game logic, AI boundary, API
frontend/ Next.js / TypeScript — player-facing UI, no game logic
cases/ Versioned, immutable mystery content (data, not code)
infra/ Docker Compose, deployment config
docs/ Architecture decisions, runbooks, playtest results
scripts/ One-off and demo scripts

## Local development

Prerequisites: Docker, Python 3.12+, Node 20+.

```bash
docker compose -f infra/docker-compose.yml up -d   # Postgres, Redis, RabbitMQ (added Day 5+)
cd backend && uvicorn app.main:app --reload         # added Day 4
cd frontend && npm run dev                          # added Day 15
```

## Status

Early scaffold — see `docs/mvp-slice.md` for the one vertical slice this
project is currently scoped to.