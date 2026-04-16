# Testing

## Testing principles

- Every component must be testable in isolation.
- Tenant isolation is a non-negotiable regression boundary.
- Retrieval quality must be tested with controlled fixtures.
- Chat memory must be tested independently from retrieval.
- Full E2E coverage must include the async ingestion pipeline.

## Test layers

### 1. Unit tests
Fast tests for pure business logic.

#### Areas
- workspace authorization
- document versioning
- markdown parsing
- chunking
- prompt building
- scope filtering
- memory packaging
- admin rules

### 2. Integration tests
Real component collaboration tests.

#### Areas
- PostgreSQL persistence
- filesystem storage
- Qdrant indexing and search
- Ollama gateway integration
- embedding pipeline
- queue and worker orchestration

### 3. Contract tests
Ensure service adapters and interfaces remain stable.

#### Areas
- parser interface
- storage interface
- Qdrant client mapping
- Ollama request/response mapping
- configuration loader

### 4. Retrieval quality tests
Fixture-based semantic search evaluation.

#### Verify
- correct top-k chunks,
- workspace isolation,
- category filtering,
- selected-document filtering,
- active-version correctness.

### 5. Memory tests
Verify conversation continuity behavior.

#### Verify
- recent window selection,
- rolling summary updates,
- follow-up question handling,
- token-budget truncation,
- workspace-safe memory boundaries.

### 6. Security tests
Verify tenant isolation and authorization.

#### Verify
- unauthorized workspace access is denied,
- cross-workspace retrieval cannot happen,
- document operations are correctly scoped,
- conversation access is correctly scoped.

### 7. End-to-end tests
Full system tests from API/UI through ingestion and chat.

## Detailed component test plan

### Workspace and auth
- user with workspace access can chat,
- user without access is rejected,
- user with multiple workspaces must explicitly select correct one.

### Document versioning
- creating a new version,
- activating a version,
- invalidating a version,
- ensuring inactive versions are excluded from normal retrieval.

### Markdown parser
- headings preserved,
- empty file handling,
- malformed markdown handling,
- list structure handling.

### Chunking
- semantic boundaries retained,
- overlap works,
- deterministic chunk order,
- large sections split safely.

### Prompt builder
- includes summary,
- includes recent messages,
- includes retrieved chunks,
- respects no-context fallback behavior.

### Retrieval
- correct workspace filter,
- correct category filter,
- selected-document filter works,
- no result case behaves safely.

### Memory
- summary refresh after threshold,
- summary and recent window combined correctly,
- follow-up references remain coherent.

### Worker pipeline
- upload triggers processing,
- retries work,
- idempotency holds,
- partial failure does not corrupt readiness state.

## E2E scenarios

### E2E 1: Upload and answer
1. Admin uploads markdown document.
2. Async pipeline finishes.
3. User asks a question.
4. Assistant answers with source attribution.

### E2E 2: Tenant isolation
1. Two workspaces have similar documents.
2. User from workspace A asks question.
3. Only A sources appear.

### E2E 3: Version invalidation
1. Upload version 1.
2. Ask question.
3. Upload version 2 and invalidate version 1.
4. Ask question again.
5. Response reflects version 2 only.

### E2E 4: Scope filtering
1. Workspace contains HR and IT documents.
2. User asks with HR-only scope.
3. Response uses HR only.

### E2E 5: Multi-workspace user
1. Same user belongs to A and B.
2. User chats in A.
3. User switches to B.
4. Workspace contexts remain isolated.

### E2E 6: Memory continuity
1. User asks topic A.
2. User asks follow-up question.
3. System preserves short-term context.

### E2E 7: Failed processing and retry
1. Upload problematic file.
2. Processing fails.
3. Admin sees failure.
4. Retry after correction succeeds.

## Real-model testing guidance

Not all tests should call a real local model.

Recommended approach:
- unit tests: no real model,
- most integration tests: mocked or stubbed LLM,
- selected smoke tests: real Ollama + Bielik,
- dedicated retrieval and fixture quality tests: deterministic fixture-based assertions.

## Recommended test directory layout

```text
tests/
  unit/
  integration/
  contracts/
  quality/
  e2e/
```
