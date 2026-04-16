# Deployment

## MVP deployment target

Single VPS using Docker Compose.

## Core services

- frontend
- backend API
- worker
- PostgreSQL
- Qdrant
- Redis
- Ollama

## Deployment principles

- all services containerized,
- environment-driven configuration,
- internal network communication where possible,
- Ollama not publicly exposed,
- Qdrant not publicly exposed,
- only frontend/API entrypoint exposed externally.

## Recommended local/prod alignment

Local development should closely mirror production topology.
Differences should mostly be:

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

## Initial docker-compose shape

```text
frontend
backend
worker
postgres
qdrant
redis
ollama
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
