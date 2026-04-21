# Deployment

## MVP deployment target

Local machine using Docker Compose.

The project is currently intended for local use only. Production deployment, public exposure, and hardened admin security are not active goals.

## Core services

- frontend
- backend API
- PostgreSQL
- Qdrant
- Redis
- Ollama

The documented ingestion worker exists as backend code, but the current Compose stack does not run a separate `worker` service.

## Deployment principles

- core services containerized,
- environment-driven configuration,
- internal network communication where possible,
- Ollama not publicly exposed,
- Qdrant not publicly exposed,
- frontend/API exposed on localhost for local development.

## Recommended local/prod alignment

If production deployment is revisited later, it should be derived from the local topology.
Expected differences would include:

- environment variables,
- security hardening,
- resource limits,
- optional reverse proxy.

## Ollama recommendation

Run Ollama in Docker for MVP.
This fits the overall container-managed system and avoids snowflake host setup.

## Resource notes

Bielik model selection must fit VPS CPU/RAM budget.
Start with the lighter viable Bielik setup before considering heavier variants.

## Persistent volumes

Persist at least:

- PostgreSQL data,
- Qdrant data,
- Ollama model data,
- uploaded file storage.

## Upgrade guidance

- version application containers,
- apply migrations carefully,
- keep document and vector stores persistent,
- reindex only when necessary.

## Current docker-compose shape

```text
frontend
backend
postgres
qdrant
redis
ollama
```

Potential future shape:

```text
worker
```

## Secrets and runtime config

Use environment variables and external secret injection for production-sensitive values.

## Backups

At minimum plan backups for:

- PostgreSQL,
- filesystem-stored uploaded files,
- optionally Qdrant if rebuild cost is high enough.

## Recovery expectations

The system should be able to recover by combining:

- PostgreSQL restore,
- file restore,
- reindex from persisted versions if needed.
