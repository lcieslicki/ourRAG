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
- `.env.production` (reserved for a future production deployment)

The current loader supports:

- base config,
- environment-specific overrides via `.env.<APP_ENV>`,
- local Docker overrides through Compose env files.

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

`OLLAMA_HOST` depends on the chosen deployment mode:

```env
# Native Ollama, backend running directly on host
OLLAMA_HOST=localhost

# Native Ollama, backend running in Docker
OLLAMA_HOST=host.docker.internal

# Ollama in Docker (docker compose --profile ollama up)
OLLAMA_HOST=ollama
```

```env
OLLAMA_PORT=11434
OLLAMA_MODEL=SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
OLLAMA_TIMEOUT_SECONDS=180
OLLAMA_KEEP_ALIVE=5m
OLLAMA_MAX_CONCURRENCY=2
```

`OLLAMA_TIMEOUT_SECONDS` must be high enough to cover model load time on first request (typically 30–90 s on Apple Silicon).

### Embeddings
```env
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_TIMEOUT_SECONDS=30
```

### Filesystem storage
```env
FILES_STORAGE_DRIVER=local
FILES_STORAGE_ROOT=/app/data/storage
DATA_ROOT=/app/data
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

### Document parsers (E6)
```env
PARSER_INGESTION_ALLOWED_FILE_TYPES=.md,.txt,.pdf,.docx
PARSER_PDF_ENABLED=true
PARSER_DOCX_ENABLED=true
PARSER_SPREADSHEET_ENABLED=false
PARSER_OCR_ENABLED=false
```

### Classification pipeline (E5)
```env
CLASSIFICATION_ENABLED=false
CLASSIFICATION_DOCUMENT_ENABLED=false
CLASSIFICATION_QUERY_ENABLED=false
CLASSIFICATION_MIN_CONFIDENCE=0.65
CLASSIFICATION_PROVIDER=rule_based
```

### Query rewriting (E1)
```env
QUERY_REWRITE_MODE=disabled        # disabled | single_rewrite | multi_query
QUERY_REWRITE_MAX_QUERIES=3
QUERY_REWRITE_INCLUDE_SUMMARY=true
QUERY_REWRITE_INCLUDE_RECENT_MESSAGES=true
QUERY_REWRITE_MODEL_PROVIDER=ollama
QUERY_REWRITE_TIMEOUT_MS=3000
```

### Advanced memory / contextualization (E2)
```env
MEMORY_CONTEXTUALIZATION_ENABLED=true
MEMORY_RETRIEVAL_RECENT_MESSAGE_LIMIT=4
MEMORY_GENERATION_RECENT_MESSAGE_LIMIT=6
MEMORY_SUMMARY_MAX_CHARS=2000
MEMORY_CONTEXTUALIZATION_TIMEOUT_MS=2500
```

### Structured extraction (E3)
```env
EXTRACTION_ENABLED=true
EXTRACTION_MAX_SCHEMA_FIELDS=30
EXTRACTION_VALIDATION_STRICT=true
EXTRACTION_TIMEOUT_MS=5000
```

### Summarization (E4)
```env
SUMMARIZATION_ENABLED=true
SUMMARIZATION_MAX_SOURCE_CHUNKS=12
SUMMARIZATION_LONG_DOC_MAP_REDUCE_ENABLED=true
SUMMARIZATION_TIMEOUT_MS=6000
```

### Routing and orchestration (E7)
```env
ROUTING_ENABLED=true
ROUTING_DEFAULT_MODE=qa
ROUTING_ALLOW_UI_MODE_HINT=true
ROUTING_MIN_CONFIDENCE=0.7
```

### Feedback loop (E8)
```env
FEEDBACK_ENABLED=true
FEEDBACK_UI_ENABLED=true
FEEDBACK_COMMENT_MAX_CHARS=1000
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
For the current local-only app, local `.env` files are acceptable for developer setup. If production deployment is introduced later, production secrets should be injected outside the repository.

## Local development requirement

The full local stack must be bootstrappable from documented environment configuration and Docker Compose.
