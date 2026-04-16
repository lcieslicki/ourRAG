# Architecture

## High-level architecture

`ourRAG` is a multi-tenant RAG platform composed of:

- React frontend with `assistant-ui`,
- Python backend API,
- background workers,
- PostgreSQL,
- Qdrant,
- Ollama with Bielik,
- local filesystem storage.

## High-level component diagram

```text
[ React Frontend ]
        |
        v
[ Python API ]
   |      |      |        |
   |      |      |        +--> [ Ollama + Bielik ]
   |      |      |
   |      |      +------------> [ Qdrant ]
   |      |
   |      +-------------------> [ PostgreSQL ]
   |
   +---------------------------> [ Local File Storage ]

[ Workers ]
   |--> parse documents
   |--> chunk content
   |--> generate embeddings
   |--> index Qdrant
   |--> generate chat summaries
   |--> cleanup / reindex
```

## Architectural decisions

### 1. Multi-tenant by workspace
The primary isolation unit is `workspace`.

A workspace may represent:

- a company,
- a department,
- a subsidiary,
- any other bounded knowledge scope.

This avoids hard-coding the product to one organizational model.

### 2. Explicit workspace selection
Users must explicitly select the active workspace before starting or continuing a conversation.

This decision improves:

- safety,
- retrieval precision,
- UI clarity,
- backend authorization.

### 3. Thin frontend
The frontend is intentionally thin.

The frontend must not decide:

- retrieval strategy,
- authorization,
- workspace access rules,
- source eligibility,
- document version validity.

The backend remains the source of truth.

### 4. Single-instance deployment
The platform is designed for a single VPS deployment in MVP, using Docker for all core services.

### 5. Local LLM runtime
Ollama runs locally in Docker and serves Bielik for answer generation.

### 6. Separate embedding and generation responsibilities
The generation model and embedding model are separate concerns.

- generation: Bielik through Ollama,
- embeddings: a dedicated embedding model chosen independently.

### 7. Async ingestion
Document processing is asynchronous from the start.

This includes:

- parsing,
- chunking,
- embedding generation,
- vector indexing,
- summary regeneration.

### 8. Versioned documents
Document versioning is a first-class feature.

The system distinguishes between:

- logical document,
- concrete document version.

### 9. Scoped conversation memory
Conversation memory exists only inside a single conversation and a single workspace.

### 10. Planned extension points
The architecture reserves explicit extension points for:

- PDF / TXT / DOCX ingestion,
- English language support,
- hybrid search,
- reranking,
- richer admin tooling,
- voice input/output,
- mobile client integration.

## Main runtime flows

### Chat flow
1. User selects workspace.
2. User sends a message.
3. Backend validates workspace membership.
4. Backend loads conversation memory.
5. Backend performs retrieval scoped to workspace and optional filters.
6. Backend builds the prompt.
7. Backend queries Bielik via Ollama.
8. Backend stores assistant response and sources.
9. Frontend renders answer and citations.

### Ingestion flow
1. Admin uploads file.
2. Backend stores file and metadata.
3. Worker parses file.
4. Worker chunks parsed content.
5. Worker generates embeddings.
6. Worker indexes chunks into Qdrant.
7. Worker marks document version as ready.

## Non-goals for MVP

The MVP does not require:

- multi-region infrastructure,
- per-tenant infrastructure isolation,
- GPU scheduling,
- cross-workspace conversations,
- document sharing across workspaces,
- hybrid search,
- reranking,
- real-time voice mode,
- public API exposure.
