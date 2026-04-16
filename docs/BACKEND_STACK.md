# Backend Stack Recommendation

## Decision

The recommended backend framework for `ourRAG` is **FastAPI**.

## Why FastAPI is the best fit

`ourRAG` is primarily an API-first system with these backend responsibilities:

- authentication and authorization,
- workspace-scoped access control,
- document upload and version management,
- asynchronous ingestion orchestration,
- retrieval orchestration,
- chat APIs,
- integration with PostgreSQL, Qdrant, Redis, and Ollama.

FastAPI is a strong fit because it is a Python web framework for building APIs based on standard Python type hints, supports dependency-based patterns, supports settings management through Pydantic Settings with `.env` files, and has documented approaches for SQL database integration. citeturn736682search0turn736682search9turn736682search3turn736682search15turn736682search21

For this project, those properties map well to the documented architecture:

- thin React frontend,
- Python backend as the source of truth,
- explicit request/response schemas,
- environment-driven configuration,
- testable service boundaries,
- containerized local development.

## Recommended backend stack

### Web framework
- **FastAPI**

### Persistence
- **PostgreSQL**
- **SQLAlchemy 2.x**
- **Alembic** for migrations

### Validation and configuration
- **Pydantic**
- **Pydantic Settings** for environment-based config

### Queue / async jobs
- **Redis**
- worker process compatible with the chosen job runner

### AI / RAG integrations
- **Qdrant client**
- **Ollama HTTP client**
- dedicated embedding service abstraction
- dedicated LLM gateway abstraction

### Testing
- **pytest**
- integration tests against local Docker services
- E2E tests for the main product workflows

## Why not build without a framework

A custom HTTP stack would increase time spent on:

- request parsing,
- validation,
- dependency wiring,
- error handling,
- API schema consistency,
- testing boilerplate,
- startup/lifecycle wiring.

That would slow down MVP delivery without giving meaningful architectural advantages.

## Alternative 1: Django

Django is a valid alternative, especially if the primary priority is getting a built-in admin interface quickly. Django ships with an admin site enabled by the default project template and provides many hooks for customization, but its own documentation warns that when a process-centric interface is needed, it is often better to write custom views instead of relying only on admin customizations. Django also supports async views and an async-enabled request stack under ASGI. citeturn736682search1turn736682search13turn736682search16

### When Django would make sense
Choose Django if:
- the internal admin panel is the main short-term priority,
- you want more built-in auth/admin conventions,
- you are comfortable with a heavier framework.

### Why Django is not the primary recommendation here
For `ourRAG`, the central product value is not CRUD-heavy back-office behavior alone. It is:

- RAG orchestration,
- chat flow,
- retrieval,
- conversation memory,
- document pipeline integration.

That makes an API-first framework a cleaner fit than a more batteries-included web framework.

## Alternative 2: Litestar

Litestar is technically capable and includes dependency injection support, DTO support, and SQLAlchemy-related integrations in its documentation. However, for this project it is a secondary option because the implementation path should optimize for mainstream ecosystem support, easier onboarding, and lower risk when working iteratively with Codex. citeturn736682search2turn736682search8turn736682search11turn736682search20

### When Litestar would make sense
Choose Litestar if:
- you explicitly want that framework,
- the team is already comfortable with it,
- you accept a smaller ecosystem tradeoff.

## Final recommendation

For `ourRAG`, use:

- **FastAPI**
- **SQLAlchemy 2.x**
- **Alembic**
- **Pydantic / Pydantic Settings**
- **Redis-backed worker setup**
- **Qdrant client**
- **Ollama client**
- **pytest**

This stack best matches the already documented goals:

- local-first development,
- Docker-based environments,
- thin frontend,
- strong testability,
- explicit API contracts,
- pragmatic MVP implementation speed.

## Suggested backend package layout

```text
backend/
  app/
    api/
      routes/
      dependencies/
      schemas/
    core/
      config/
      logging/
      security/
    domain/
      models/
      services/
      policies/
    infrastructure/
      db/
      storage/
      qdrant/
      ollama/
      embeddings/
      queue/
    workers/
    tests/
```

## Implementation guidance for Codex

When using Codex, the backend implementation should start with:

1. FastAPI application bootstrap
2. configuration loading
3. SQLAlchemy models and Alembic migrations
4. workspace/document/conversation domain modules
5. upload and storage flow
6. ingestion workers
7. embeddings and Qdrant
8. retrieval orchestration
9. chat orchestration
10. admin and testing hardening

## Documentation integration note

This document complements:

- `docs/ARCHITECTURE.md`
- `docs/COMPONENTS.md`
- `docs/CONFIGURATION.md`
- `docs/DEPLOYMENT.md`
- `docs/API_CONTRACT.md`

It should be treated as the backend implementation recommendation and framework decision record for the MVP.
