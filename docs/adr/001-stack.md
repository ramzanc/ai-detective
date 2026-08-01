# ADR-001: Core technology stack

Status: Accepted
Date: 2026-08-01

## Context

We're building a backend-heavy, AI-integrated game where the primary
engineering risk is trust boundaries (server vs. LLM vs. client), not UI
polish. The author has strong existing Node.js/Postgres/Redis/RabbitMQ
experience and is learning Python for AI-engineering roles.

## Decision

- Backend: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic
- Database: PostgreSQL 16 with pgvector
- Cache/coordination: Redis
- Async jobs: RabbitMQ, durable queues, manual ACK, retry + DLQ
- Frontend: Next.js + TypeScript, desktop-first responsive UI
- Testing: pytest, pytest-asyncio, Testcontainers/Docker Compose, Playwright
- AI boundary: provider-abstracted client, typed structured output,
  backend-selected behavior, scoped retrieval, validation, deterministic
  fallback
- Observability: OpenTelemetry traces, structured logs, Prometheus-style
  metrics
- Local dev: Docker Compose for Postgres/Redis/RabbitMQ; apps run locally

## Consequences

- Easier: direct transfer of async/queue/cache mental models from Node;
  pgvector keeps retrieval in the same database as everything else instead
  of a separate vector store; FastAPI's typed DTOs give the same safety as
  a well-typed Express+Zod stack.
- Harder: Python async ecosystem has more sharp edges than Node's (e.g.
  SQLAlchemy async session scoping); team (of one) is still ramping on
  idiomatic Python.
- We're explicitly choosing "one more thing to learn" (Python/FastAPI)
  because the target skill this project demonstrates is AI-engineering in
  Python, not backend engineering in general.

## Alternatives considered

- **Node.js + Express/Nest, LangChain.js**: rejected — would demonstrate
  skills the author already has, not the skills this project is meant to
  prove.
- **A managed vector DB (Pinecone, Weaviate) instead of pgvector**:
  rejected for MVP — adds an operational dependency without a clear
  benefit at this scale; pgvector keeps retrieval consistent with the rest
  of the transactional data.
- **Firebase/Supabase-style BaaS instead of a custom backend**: rejected —
  the whole point of the project is demonstrating custom trust-boundary
  and state-machine design, which a BaaS would abstract away.