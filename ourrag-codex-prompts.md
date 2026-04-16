# ourRAG — Codex Prompt Series

This document contains a phased prompt sequence for implementing the `ourRAG` MVP with Codex.

## How to use this document

- Run the prompts in order.
- Do not skip the planning phase.
- Keep each Codex task limited to one phase unless explicitly stated otherwise.
- After each phase, review the diff before moving on.
- Prefer a clean Git checkpoint before every major phase.
- Keep `AGENTS.md` in the repository root and keep the `docs/` directory committed before starting.

## General usage rules for Codex

Use these rules repeatedly across phases:

- Read `README.md` and all files in `docs/` before making implementation decisions.
- Treat the documentation as the source of truth.
- Keep the frontend thin.
- Keep authorization and retrieval logic in the backend.
- Keep changes small and reviewable.
- Add tests as you go.
- Report ambiguities instead of silently inventing architecture.
- Do not implement future features unless explicitly requested.
- Use environment-based configuration only.
- Support `.env` and `.env.<environment>` patterns.
- Keep local development Docker-based.

---

# Phase 0 — Repository guidance and implementation plan

## Prompt 0.1 — Create `AGENTS.md`

```text
Create a root-level AGENTS.md for this repository.

Requirements:
- Read README.md and all files in docs/ first.
- The AGENTS.md must treat the documentation as the source of truth.
- It must include project rules for:
  - architecture
  - implementation boundaries
  - testing expectations
  - environment configuration
  - delivery style
- It must explicitly state:
  - backend is Python
  - frontend is React
  - assistant-ui is the chat UI layer
  - PostgreSQL is the relational source of truth
  - Qdrant is the vector store
  - Ollama is the local model runtime
  - Bielik is the generation model
  - workspace is the tenant isolation boundary
  - retrieval must always be scoped by workspace_id
  - standard retrieval uses active document versions only
- Add guidance that Codex should first produce a short plan before large implementation tasks.
- Keep it practical and concise, not generic.

After writing AGENTS.md:
- summarize the file
- explain any assumptions you made
```

## Prompt 0.2 — Create the implementation plan only

```text
Read README.md, AGENTS.md, and all files in docs/ first.

Produce an implementation plan for the ourRAG MVP.

Rules:
- Do not write code yet.
- Break the work into phases.
- For each phase include:
  - goal
  - modules/services to create
  - likely files/directories
  - dependencies on earlier phases
  - tests to add
  - risks and open questions
- Keep the plan implementation-oriented.
- Explicitly separate MVP scope from future-planned features.
- Call out any inconsistencies or missing decisions in the docs.

At the end:
- recommend the best phase order
- identify the minimum backend-first slice that can be built and tested locally
```

---

# Phase 1 — Monorepo / project skeleton

## Prompt 1.1 — Create the repository skeleton

```text
Implement Phase 1 only.

Goal:
Create the initial repository skeleton for the ourRAG MVP.

Requirements:
- Read README.md, AGENTS.md, and docs/ first.
- Create a clean top-level structure for:
  - backend
  - frontend
  - infra or docker-related local setup
  - tests
  - docs already exist and must remain untouched unless needed
- Keep the structure pragmatic and suitable for:
  - Python backend
  - React frontend
  - Docker-based local development
- Add placeholder README files only where useful.
- Do not implement business logic yet.
- Do not implement retrieval, indexing, or chat behavior yet.

Also:
- add basic ignore files where needed
- add a top-level Makefile or task runner only if it clearly helps local development

At the end:
- summarize created files and directories
- explain the intended purpose of each major directory
```

## Prompt 1.2 — Add Docker-based local environment

```text
Implement the local Docker development foundation only.

Requirements:
- Read docs/ARCHITECTURE.md, docs/CONFIGURATION.md, and docs/DEPLOYMENT.md first.
- Add Docker Compose for local development.
- Include services for:
  - backend
  - frontend
  - postgres
  - qdrant
  - redis
  - ollama
- Keep the setup suitable for local development and testing.
- Use persistent volumes where appropriate.
- Do not expose internal services publicly unless needed for local development.
- Do not overengineer reverse proxying yet unless necessary.

Also:
- create environment variable templates
- support `.env` and environment-specific overrides
- make sure service names align with documented config assumptions

At the end:
- list all created files
- explain how to boot the stack locally
- mention any commands still missing
```

## Prompt 1.3 — Add configuration loading scaffolding

```text
Implement configuration scaffolding for both backend and frontend.

Requirements:
- Follow docs/CONFIGURATION.md strictly.
- All runtime configuration must come from environment variables.
- Support `.env` and `.env.<environment>` patterns.
- Add typed or validated config loading where practical.
- Fail fast on invalid configuration.
- Separate config by subsystem:
  - app
  - postgres
  - qdrant
  - ollama
  - embeddings
  - storage
  - queue
  - retrieval
  - chat memory

Do not:
- hardcode secrets
- hardcode hostnames or model names outside config defaults
- implement deep business logic

At the end:
- summarize config modules
- list required env variables
- explain how local vs test vs production config would differ
```

---

# Phase 2 — Domain model and persistence foundation

## Prompt 2.1 — Implement core domain and persistence scaffolding

```text
Implement the first backend domain/persistence slice.

Requirements:
- Read docs/DOMAIN_MODEL.md and docs/DATA_MODEL.md first.
- Implement initial backend structures for:
  - workspace
  - user
  - workspace membership
  - document
  - document version
  - conversation
  - message
  - conversation summary
- Keep the implementation clean and aligned with the documented invariants.
- Add initial database models and migrations.
- Add explicit constraints where possible.
- Keep roles and statuses pragmatic and extensible.
- Prefer small, reviewable modules.

Do not implement:
- vector indexing
- retrieval logic
- prompt building
- LLM calls
- frontend UI

At the end:
- summarize created models and migrations
- list enforced invariants
- mention any invariants that still need application-layer enforcement
```

## Prompt 2.2 — Add tests for domain invariants

```text
Add tests for the domain and persistence foundation.

Requirements:
- Follow docs/TESTING.md.
- Add unit and integration tests for:
  - workspace membership access logic
  - conversation belongs to exactly one workspace
  - document version belongs to exactly one document
  - only one active version per document, if enforced now
  - invalid document/workspace access is rejected at the domain/service layer
- Keep tests deterministic.
- Prefer fixtures/helpers over repetitive setup.

At the end:
- list added tests
- explain what remains untested in this phase
```

---

# Phase 3 — Document upload, storage, and versioning

## Prompt 3.1 — Implement local file storage and upload flow

```text
Implement document upload and local filesystem storage.

Requirements:
- Read docs/INGESTION_PIPELINE.md, docs/DATA_MODEL.md, docs/SECURITY.md, and docs/API_CONTRACT.md first.
- Implement backend support for:
  - creating a logical document
  - uploading a new document version
  - storing the uploaded file on local filesystem
  - persisting file metadata
  - workspace-scoped storage paths
- Follow the documented versioning model.
- Keep the storage layer abstract enough for future replacement.
- Add the relevant API endpoint(s).
- Reject unsupported file types for now, except Markdown.
- Keep security and workspace ownership checks in the backend.

Do not implement:
- parsing
- chunking
- embeddings
- Qdrant indexing

At the end:
- summarize the upload flow
- list created API routes
- explain file path strategy
```

## Prompt 3.2 — Add version activation and invalidation flows

```text
Implement document version lifecycle actions.

Requirements:
- Use docs/DATA_MODEL.md, docs/API_CONTRACT.md, and docs/SECURITY.md as source of truth.
- Add backend support for:
  - activating a document version
  - invalidating a document version
  - preventing invalid retrieval eligibility for invalidated versions
- Add admin-facing API endpoints for these actions.
- Enforce permission checks.
- Preserve auditability where practical.
- Keep the implementation consistent with the documented rule that standard retrieval uses active document versions only.

At the end:
- summarize the lifecycle rules as implemented
- mention any assumptions you made
```

## Prompt 3.3 — Add tests for upload and versioning

```text
Add tests for upload, storage, and document versioning.

Requirements:
- Follow docs/TESTING.md and docs/FAILURE_MODES.md.
- Add tests for:
  - Markdown upload success
  - unsupported file type rejection
  - correct workspace-scoped storage
  - creating a new document version
  - activating a version
  - invalidating a version
  - preventing invalid access across workspaces
- Add integration coverage for local filesystem storage.

At the end:
- summarize test coverage
- mention remaining gaps
```

---

# Phase 4 — Parser and chunking

## Prompt 4.1 — Add parser interface and Markdown parser

```text
Implement the parser foundation and Markdown parser.

Requirements:
- Read docs/INGESTION_PIPELINE.md and docs/COMPONENTS.md first.
- Create a parser interface/contract suitable for future:
  - Markdown
  - PDF
  - TXT
  - DOCX
- Implement Markdown parser only for MVP.
- Preserve useful structure such as headings and paragraphs.
- Normalize text carefully without destroying semantic structure.
- Keep the code testable and modular.

Do not implement non-Markdown parsers yet.

At the end:
- summarize the parser interface
- describe what parser output looks like
```

## Prompt 4.2 — Implement structure-aware chunking

```text
Implement the chunking module for Markdown documents.

Requirements:
- Follow docs/INGESTION_PIPELINE.md strictly.
- Use structure-aware chunking instead of naive fixed slicing.
- Preserve useful metadata such as:
  - chunk_index
  - heading
  - section_path
  - document_version_id
  - workspace_id
  - language
- Use configurable chunk size and overlap.
- Keep the implementation deterministic and easy to test.
- Add versioning or naming for the chunking strategy where practical.

At the end:
- summarize the chunking algorithm
- list its configuration points
```

## Prompt 4.3 — Add parser and chunking tests

```text
Add tests for parsing and chunking.

Requirements:
- Follow docs/TESTING.md.
- Add tests for:
  - heading extraction
  - empty markdown handling
  - malformed markdown handling
  - preserving semantic chunk order
  - overlap behavior
  - deterministic output
  - section_path generation
- Use small but representative markdown fixtures.

At the end:
- list created fixtures
- summarize what chunking edge cases are covered
```

---

# Phase 5 — Async jobs and ingestion pipeline orchestration

## Prompt 5.1 — Add worker/job scaffolding

```text
Implement the asynchronous job foundation for ingestion.

Requirements:
- Read docs/INGESTION_PIPELINE.md, docs/COMPONENTS.md, and docs/TESTING.md first.
- Add worker/job scaffolding for:
  - parse_document
  - chunk_document
  - embed_document
  - index_document
  - reindex_document_version
- Keep jobs idempotent where feasible.
- Track job state in the database if consistent with the docs.
- Make failure handling observable and retry-friendly.
- Do not implement embeddings or indexing deeply yet; this step should establish orchestration structure.

At the end:
- summarize job flow
- explain retry and failure state handling
```

## Prompt 5.2 — Connect upload to async ingestion pipeline

```text
Connect document upload to the async ingestion pipeline.

Requirements:
- After successful Markdown upload, enqueue the appropriate processing jobs.
- Update document version processing status across the lifecycle.
- Keep the processing flow aligned with docs/INGESTION_PIPELINE.md.
- Ensure failures do not incorrectly mark a version as ready.
- Keep the implementation explicit and testable.

At the end:
- summarize the upload-to-ready pipeline state machine
- mention which stages are fully implemented vs scaffolded
```

## Prompt 5.3 — Add tests for worker orchestration

```text
Add tests for ingestion orchestration.

Requirements:
- Follow docs/TESTING.md and docs/FAILURE_MODES.md.
- Cover:
  - upload triggers processing
  - status transitions
  - failed job remains failed
  - retries are possible
  - idempotency expectations where implemented
- Keep tests reliable in local development.

At the end:
- summarize orchestration test coverage
```

---

# Phase 6 — Embeddings and vector indexing

## Prompt 6.1 — Add embedding abstraction and initial implementation

```text
Implement the embedding service abstraction and an initial local embedding integration.

Requirements:
- Read docs/ARCHITECTURE.md, docs/INGESTION_PIPELINE.md, docs/RETRIEVAL.md, and docs/CONFIGURATION.md first.
- Create an embedding interface that is independent of the generation model.
- Implement one concrete embedding provider suitable for local runtime and documented config.
- Ensure embeddings can be generated for:
  - document chunks
  - user queries
- Store enough metadata to support future model/version changes.
- Keep the implementation testable.

Do not implement retrieval orchestration yet beyond what is required to validate the abstraction.

At the end:
- summarize the embedding abstraction
- list the configuration needed
```

## Prompt 6.2 — Add Qdrant indexing layer

```text
Implement the vector index layer with Qdrant.

Requirements:
- Follow docs/DATA_MODEL.md, docs/RETRIEVAL.md, and docs/SECURITY.md.
- Create the Qdrant collection access layer.
- Implement:
  - upsert chunk vectors
  - delete vectors for a document version
  - query support needed later for retrieval
- Use a single collection strategy for MVP.
- Ensure payload includes:
  - workspace_id
  - document_id
  - document_version_id
  - chunk_id
  - section_path
  - category if available
  - language
  - is_active
- Keep workspace filtering central and explicit.

At the end:
- summarize Qdrant payload design
- list all mandatory filters
```

## Prompt 6.3 — Connect embeddings and indexing to the ingestion pipeline

```text
Complete the document indexing path.

Requirements:
- Connect parsed/chunked document versions to:
  - embedding generation
  - Qdrant indexing
- Mark document version as ready only after successful indexing.
- Persist indexing metadata where documented.
- Ensure invalidated or inactive versions are handled correctly.
- Keep the implementation aligned with the documented versioning model.

At the end:
- summarize the end-to-end indexing flow
- explain how reindexing would work from this design
```

## Prompt 6.4 — Add tests for embeddings and indexing

```text
Add tests for embeddings and Qdrant indexing.

Requirements:
- Follow docs/TESTING.md.
- Add integration tests for:
  - chunk embedding generation
  - indexing into Qdrant
  - deleting/replacing vectors
  - workspace filter correctness
  - active-version indexing assumptions
- Use stubs or fakes where practical, but include at least one realistic integration path if feasible.

At the end:
- summarize indexing coverage
- identify what still needs a higher-level retrieval test
```

---

# Phase 7 — Retrieval layer

## Prompt 7.1 — Implement retrieval service

```text
Implement the retrieval service for MVP.

Requirements:
- Read docs/RETRIEVAL.md, docs/SECURITY.md, docs/DOMAIN_MODEL.md, and docs/COMPONENTS.md first.
- Retrieval must:
  - validate workspace access
  - embed the user query
  - query Qdrant with strict mandatory filters
  - support optional filters for:
    - category
    - selected document IDs
    - language
  - return top-k chunks for prompt assembly
- Keep hybrid search and reranking out of scope for now, but preserve extension points.
- Keep the implementation explicit and testable.

At the end:
- summarize retrieval flow
- explain exactly where workspace and active-version filtering are enforced
```

## Prompt 7.2 — Add retrieval quality tests

```text
Add retrieval tests using fixture-based documents.

Requirements:
- Follow docs/TESTING.md and docs/FIXTURES.md.
- Build a small controlled fixture set that can verify:
  - correct top-k behavior
  - workspace isolation
  - category-restricted retrieval
  - selected-document retrieval
  - active-version correctness
- Keep the assertions practical and deterministic.

At the end:
- summarize the fixtures
- summarize the quality checks implemented
```

---

# Phase 8 — Prompt builder and LLM gateway

## Prompt 8.1 — Implement prompt builder

```text
Implement the prompt builder.

Requirements:
- Read docs/CHAT_MEMORY.md, docs/RETRIEVAL.md, and docs/COMPONENTS.md first.
- The prompt builder must assemble:
  - system instructions
  - workspace context if needed
  - conversation summary
  - recent messages
  - retrieved chunks
  - current user message
- It must instruct the model to answer only from available context and say it does not know when context is insufficient.
- Keep the structure explicit and versionable.
- Do not overfit to one exact prompt string; create a maintainable prompt-building module.

At the end:
- summarize prompt composition
- explain how no-context behavior is handled
```

## Prompt 8.2 — Implement Ollama / Bielik gateway

```text
Implement the LLM gateway for local Ollama with Bielik.

Requirements:
- Follow docs/ARCHITECTURE.md, docs/CONFIGURATION.md, and docs/COMPONENTS.md.
- Add an abstraction for the generation model gateway.
- Implement Ollama as the first provider.
- Support:
  - model configuration by env
  - timeout handling
  - simple retry handling where appropriate
  - concurrency control if practical
- Keep streaming out of scope for the first implementation unless trivial.
- Keep the code easy to replace later if the provider changes.

At the end:
- summarize the gateway interface
- list runtime assumptions
```

## Prompt 8.3 — Add tests for prompt builder and LLM gateway

```text
Add tests for prompt building and LLM gateway behavior.

Requirements:
- Follow docs/TESTING.md and docs/FAILURE_MODES.md.
- Add tests for:
  - prompt includes summary and recent messages
  - prompt includes retrieved chunks
  - no-context prompt behavior
  - Ollama gateway request mapping
  - timeout handling
  - malformed provider response handling
- Prefer stubs for most tests.

At the end:
- summarize test coverage
```

---

# Phase 9 — Conversations, messages, and memory

## Prompt 9.1 — Implement conversation and message APIs

```text
Implement the conversation and message API layer.

Requirements:
- Follow docs/API_CONTRACT.md, docs/DOMAIN_MODEL.md, and docs/SECURITY.md.
- Add endpoints/services for:
  - listing conversations for a workspace
  - creating a conversation
  - retrieving a conversation with messages
  - appending user and assistant messages through the chat flow
- Ensure a conversation belongs to exactly one workspace.
- Enforce workspace-scoped access checks.
- Keep the conversation model ready for memory support.

At the end:
- summarize the API endpoints
- explain access-control enforcement
```

## Prompt 9.2 — Implement chat memory service

```text
Implement the memory service for conversations.

Requirements:
- Follow docs/CHAT_MEMORY.md and docs/COMPONENTS.md.
- Implement:
  - recent-message window selection
  - rolling conversation summary persistence
  - memory package generation for prompt builder
- Keep summary generation simple and pragmatic for MVP.
- Do not dump entire conversation history into every prompt.
- Ensure memory remains scoped to one conversation and one workspace.

At the end:
- summarize the memory strategy as implemented
- mention any shortcuts taken for MVP
```

## Prompt 9.3 — Wire full chat flow backend

```text
Implement the backend chat orchestration flow.

Requirements:
- Use docs/ARCHITECTURE.md, docs/API_CONTRACT.md, docs/CHAT_MEMORY.md, docs/RETRIEVAL.md, and docs/SECURITY.md as source of truth.
- On chat request, the backend must:
  - validate workspace access
  - load conversation
  - apply scope filters
  - load memory package
  - run retrieval
  - build prompt
  - call Bielik through Ollama
  - store assistant response
  - return answer and sources
- Keep the frontend thin by keeping all decision-making in the backend.

At the end:
- summarize the full chat pipeline
- identify any parts still stubbed or simplified
```

## Prompt 9.4 — Add tests for conversations and memory

```text
Add tests for conversations, memory, and chat orchestration.

Requirements:
- Follow docs/TESTING.md.
- Cover:
  - conversation belongs to one workspace
  - multi-workspace user isolation
  - recent-message memory
  - rolling summary behavior
  - follow-up question continuity
  - no cross-workspace memory leakage
- Keep deterministic tests where possible.

At the end:
- summarize memory-related coverage
```

---

# Phase 10 — Admin APIs and management flows

## Prompt 10.1 — Implement admin API surface

```text
Implement the MVP admin backend surface.

Requirements:
- Follow docs/API_CONTRACT.md, docs/COMPONENTS.md, docs/SECURITY.md, and docs/ROADMAP.md.
- Add admin capabilities for:
  - listing documents and versions
  - reading processing status
  - activating versions
  - invalidating versions
  - requesting reindex
  - reading/updating workspace-level settings where already supported
- Enforce role checks.
- Keep auditability in mind.

At the end:
- summarize admin capabilities implemented
- list any operations intentionally left for later
```

## Prompt 10.2 — Add admin and audit tests

```text
Add tests for admin actions and audit-sensitive flows.

Requirements:
- Follow docs/TESTING.md and docs/SECURITY.md.
- Cover:
  - admin can manage versions in allowed workspace
  - non-admin cannot perform admin actions
  - reindex request path works
  - audit or event logging occurs where implemented
- Keep tests concise and valuable.

At the end:
- summarize admin test coverage
```

---

# Phase 11 — React frontend and assistant-ui integration

## Prompt 11.1 — Bootstrap React frontend and chat shell

```text
Implement the initial React frontend shell.

Requirements:
- Read docs/ARCHITECTURE.md, docs/API_CONTRACT.md, and docs/COMPONENTS.md first.
- Use React for the frontend.
- Integrate assistant-ui as the chat UI foundation.
- Keep the frontend thin.
- Build only the initial shell:
  - app layout
  - workspace switcher placeholder
  - chat page shell
  - API client structure
- Do not move retrieval or authorization logic into the frontend.
- Keep styling minimal and pragmatic for now.

At the end:
- summarize the frontend structure
- explain where assistant-ui is integrated
```

## Prompt 11.2 — Implement workspace switcher and chat integration

```text
Implement the frontend workspace-aware chat flow.

Requirements:
- Follow docs/API_CONTRACT.md and docs/SECURITY.md.
- Add:
  - workspace selection UI
  - conversation list UI
  - chat input and message rendering
  - backend API integration for chat
- The active workspace must be explicit in the UI and reflected in API calls.
- Do not trust frontend scope state for security; backend remains authoritative.
- Keep the frontend state model simple and predictable.

At the end:
- summarize user flow from workspace selection to chat answer
```

## Prompt 11.3 — Render citations and scope filters

```text
Implement source rendering and explicit scope filters in the frontend.

Requirements:
- Follow docs/RETRIEVAL.md and docs/API_CONTRACT.md.
- Add UI support for:
  - answer source rendering
  - optional category filter
  - optional selected-document filter if practical at this phase
- Keep the UI clear and lightweight.
- Do not expose internal-only identifiers unnecessarily.

At the end:
- summarize the source rendering and filtering UX
```

## Prompt 11.4 — Add frontend tests

```text
Add frontend tests for the MVP chat UI.

Requirements:
- Focus on practical coverage:
  - workspace selection state
  - conversation loading
  - answer rendering
  - source rendering
  - basic error states
- Keep tests aligned with the current MVP behavior.
- Avoid brittle snapshots unless they add clear value.

At the end:
- summarize frontend test coverage
```

---

# Phase 12 — End-to-end coverage and hardening

## Prompt 12.1 — Add E2E tests for the happy path

```text
Add end-to-end tests for the MVP happy path.

Requirements:
- Follow docs/TESTING.md and docs/FIXTURES.md.
- Cover:
  - upload markdown document
  - async processing to ready state
  - ask a question in the correct workspace
  - receive answer with sources
- Keep the scenario reproducible in local Docker development.

At the end:
- summarize the E2E setup
- list any manual prerequisites
```

## Prompt 12.2 — Add E2E tests for tenant isolation and versioning

```text
Add end-to-end tests for:
- tenant isolation
- version invalidation
- category filtering
- multi-workspace user switching
- follow-up memory continuity

Requirements:
- Use docs/TESTING.md as the source of truth.
- Keep the tests readable and directly tied to documented product behavior.
- Prefer a small but high-value E2E suite over broad flaky coverage.

At the end:
- summarize all implemented E2E scenarios
- identify any still better suited to integration tests instead of E2E
```

## Prompt 12.3 — Hardening pass

```text
Perform a hardening pass on the existing implementation.

Requirements:
- Read docs/SECURITY.md, docs/OBSERVABILITY.md, docs/FAILURE_MODES.md, and docs/TESTING.md first.
- Review the existing code for:
  - missing workspace scoping
  - missing active-version checks
  - weak failure handling
  - missing configuration validation
  - poor observability hooks
  - weak test coverage in critical areas
- Make small, high-confidence fixes only.
- Do not introduce future features.

At the end:
- summarize findings
- summarize fixes made
- list remaining risks
```

---

# Final consolidation prompts

## Prompt F.1 — Documentation sync check

```text
Review the implementation against:
- README.md
- all files in docs/

Tasks:
- identify mismatches between implementation and documentation
- propose the smallest set of documentation or code changes needed
- if the implementation diverged intentionally, explain why
- do not make changes yet

Return the result as a concise gap analysis.
```

## Prompt F.2 — Final MVP readiness report

```text
Review the repository and produce an MVP readiness report.

Requirements:
- Evaluate backend completeness
- evaluate frontend completeness
- evaluate ingestion pipeline completeness
- evaluate retrieval and memory completeness
- evaluate security-critical areas
- evaluate testing coverage
- evaluate local developer experience
- list blockers vs non-blockers

Return:
- completed
- partial
- missing
for each major subsystem, with brief justification.
```

---

# Optional prompts

## Optional prompt — Backend-first vertical slice

```text
Implement only the smallest backend-first vertical slice that can demonstrate the core product value locally.

Target slice:
- workspace membership
- markdown upload
- chunking
- indexing
- one chat endpoint
- retrieval scoped to workspace
- answer generation with Bielik
- source attribution
- minimal tests

Do not implement the full frontend yet.
Do not implement future features.
Keep the slice runnable in Docker locally.
```

## Optional prompt — Repo refactor control

```text
Before changing anything, inspect the current repository and identify if the requested work can be completed without major refactoring.

If major refactoring is needed:
- explain why
- propose the smallest safe refactor plan
- do not execute it yet
```

## Optional prompt — Subagent exploration only

```text
Use subagents only for analysis, not for coding.

Create:
- one subagent to inspect backend needs
- one subagent to inspect frontend needs
- one subagent to inspect testing needs

Then consolidate the results into one implementation proposal aligned with the docs.

Do not write code in this step.
```

---

# Recommended execution order

1. Prompt 0.1
2. Prompt 0.2
3. Prompt 1.1
4. Prompt 1.2
5. Prompt 1.3
6. Prompt 2.1
7. Prompt 2.2
8. Prompt 3.1
9. Prompt 3.2
10. Prompt 3.3
11. Prompt 4.1
12. Prompt 4.2
13. Prompt 4.3
14. Prompt 5.1
15. Prompt 5.2
16. Prompt 5.3
17. Prompt 6.1
18. Prompt 6.2
19. Prompt 6.3
20. Prompt 6.4
21. Prompt 7.1
22. Prompt 7.2
23. Prompt 8.1
24. Prompt 8.2
25. Prompt 8.3
26. Prompt 9.1
27. Prompt 9.2
28. Prompt 9.3
29. Prompt 9.4
30. Prompt 10.1
31. Prompt 10.2
32. Prompt 11.1
33. Prompt 11.2
34. Prompt 11.3
35. Prompt 11.4
36. Prompt 12.1
37. Prompt 12.2
38. Prompt 12.3
39. Prompt F.1
40. Prompt F.2

---

# Final recommendation

For best results, use Codex in this pattern for each phase:

1. ask for the phase plan,
2. let it implement one phase only,
3. review the diff,
4. run tests,
5. only then move to the next prompt.

This is more reliable than asking Codex to build the whole system in one pass.
