# Roadmap

## Phase 0: Documentation and design
Deliverables:

- architecture documents,
- domain model,
- data model,
- ingestion design,
- retrieval design,
- configuration strategy,
- testing strategy.

## Phase 1: MVP backend foundation
Deliverables:

- workspace and membership model,
- authentication integration,
- document upload,
- document versioning,
- local filesystem storage,
- async processing pipeline,
- markdown parser,
- chunking,
- embeddings,
- Qdrant indexing.

## Phase 2: MVP chat
Deliverables:

- conversations,
- messages,
- retrieval orchestration,
- prompt builder,
- Ollama integration,
- Bielik-based answering,
- source attribution.

## Phase 3: Memory and admin
Deliverables:

- recent-message memory,
- rolling conversation summaries,
- admin panel,
- processing monitoring,
- version activation/invalidation,
- reindex operations.

## Phase 4: Frontend UX
Deliverables:

- React frontend,
- assistant-ui integration,
- workspace switcher,
- scope filters,
- source rendering.

## Phase 5: Hardening
Deliverables:

- stronger observability,
- richer E2E coverage,
- optional security audits if the project stops being local-only,
- performance tuning,
- deployment hardening if production deployment becomes a goal.

## Current local-only decision

The implemented MVP targets local use. Production authentication, strict admin authorization, and public deployment hardening are intentionally not priorities right now.

## Planned future features

Not MVP, but intentionally planned:

- PDF support,
- TXT support,
- DOCX support,
- English support,
- hybrid search,
- reranking,
- voice input/output,
- mobile client integration,
- richer per-workspace settings,
- object storage,
- stronger admin analytics.
