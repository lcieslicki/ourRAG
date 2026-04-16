# Configuration

## Configuration principles

- All configuration must be environment-driven.
- No hard-coded runtime values in application code.
- Every subsystem must expose explicit configuration.
- `.env` and environment-specific overrides are mandatory.

## Environment file strategy

Recommended files:

- `.env`
- `.env.local`
- `.env.test`
- `.env.docker`
- `.env.production`

The exact loader implementation may vary, but the system must support:

- base config,
- environment-specific overrides,
- secret injection outside repository when needed.

## Example configuration groups

### App
```env
APP_ENV=local
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8000
APP_LOG_LEVEL=info
```

### PostgreSQL
```env
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=ourrag
POSTGRES_USER=ourrag
POSTGRES_PASSWORD=secret
```

### Qdrant
```env
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=document_chunks
QDRANT_TIMEOUT=10
```

### Ollama
```env
OLLAMA_HOST=ollama
OLLAMA_PORT=11434
OLLAMA_MODEL=bielik
OLLAMA_TIMEOUT_SECONDS=60
OLLAMA_KEEP_ALIVE=5m
OLLAMA_MAX_CONCURRENCY=2
```

### Embeddings
```env
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_TIMEOUT_SECONDS=30
```

### Filesystem storage
```env
FILES_STORAGE_DRIVER=local
FILES_STORAGE_ROOT=/data/storage
```

### Queue / workers
```env
QUEUE_DRIVER=redis
REDIS_HOST=redis
REDIS_PORT=6379
WORKER_CONCURRENCY=2
```

### Retrieval defaults
```env
RAG_TOP_K=5
RAG_MAX_CONTEXT_CHUNKS=5
RAG_MIN_SCORE_THRESHOLD=
```

### Chunking defaults
```env
RAG_CHUNK_SIZE=1200
RAG_CHUNK_OVERLAP=150
RAG_CHUNKING_STRATEGY=markdown_semantic_v1
```

### Chat memory
```env
CHAT_RECENT_MESSAGES_LIMIT=8
CHAT_SUMMARY_ENABLED=true
CHAT_SUMMARY_REFRESH_EVERY_N_MESSAGES=8
```

## Workspace-level overrides

The data model supports future per-workspace configuration overrides.

Examples:
- prompt override,
- generation model override,
- embedding model override,
- language defaults,
- retrieval defaults.

MVP may keep most values global, but the schema should be future-safe.

## Configuration validation

Application startup should fail fast on invalid configuration.

Validate:
- required variables,
- numeric ranges,
- enum-like values,
- host/port consistency.

## Secrets

Secrets should not be committed.
Production secrets should be injected via secure deployment configuration, not repository `.env.production`.

## Local development requirement

The full local stack must be bootstrappable from documented environment configuration and Docker Compose.
