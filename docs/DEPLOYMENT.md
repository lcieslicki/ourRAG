# Deployment

## MVP deployment target

Local machine using Docker Compose.

The project is currently intended for local use only. Production deployment, public exposure, and hardened admin security are not active goals.

## Core services

Always started:

- frontend
- backend API
- PostgreSQL
- Qdrant
- Redis

Optional (profile-based):

- Ollama (see below)

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

## Ollama deployment modes

Ollama can run in two modes. Choose based on available hardware.

### Native (recommended for development on Apple Silicon)

Ollama installed directly on the host machine uses the Metal GPU, which is significantly faster than CPU-only Docker.
The Ollama container is excluded from Compose by default.

```bash
# Start infrastructure only (Ollama not included)
docker compose up

# OLLAMA_HOST must point to the host from inside Docker
OLLAMA_HOST=host.docker.internal   # backend in Docker
OLLAMA_HOST=localhost               # backend running directly
```

### Dockerized

Use when GPU access is not a concern (CI, CPU-only machines, or NVIDIA GPU with Docker GPU passthrough).

```bash
# Start infrastructure including Ollama container
docker compose --profile ollama up

OLLAMA_HOST=ollama
```

## Model recommendation

Use `SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M` for development.

| Quantization | RAM  | Quality | Speed on Apple Silicon |
|---|---|---|---|
| Q8_0         | ~12GB | best    | slow on CPU            |
| Q4_K_M       | ~6GB  | good    | fast with Metal GPU    |

Pull the model before first use:

```bash
ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
```

Set `OLLAMA_TIMEOUT_SECONDS=180` to accommodate model load time on first request.

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
ollama   ← only with --profile ollama
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
