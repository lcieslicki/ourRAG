# Components

## Backend API
Responsibilities:

- authenticate users,
- validate workspace access,
- expose chat APIs,
- expose document APIs,
- expose admin APIs,
- orchestrate retrieval and prompt building.

Does not:

- perform heavy ingestion inline,
- allow frontend to enforce authorization.

## Ingestion Job Runner
Responsibilities:

- parse uploaded files,
- chunk text,
- generate embeddings,
- index vectors,
- refresh conversation summaries,
- run cleanup and reindex jobs.

Does not:

- serve user-facing APIs.

Current status:
- jobs are persisted in PostgreSQL,
- upload creates queued processing jobs,
- the runner can process jobs until idle,
- local admin upload/folder indexing can trigger processing through backend background tasks,
- a separate long-running worker container is not wired into Docker Compose yet.

## WorkspaceContextService
Responsibilities:

- resolve active workspace,
- validate membership,
- enforce workspace scoping in downstream services.

## DocumentService
Responsibilities:

- create logical documents,
- create versions,
- manage active/invalidated status,
- expose admin operations.

## ParserRegistry
Responsibilities:

- select parser implementation by file type,
- keep parser interface pluggable.

## MarkdownParser
Responsibilities:

- parse `.md`,
- normalize text,
- preserve useful structure such as headings and lists.

## PdfParser
Responsibilities:

- extract text from PDF pages,
- detect headings heuristically (ALL CAPS, numbered),
- preserve page numbers in block metadata,
- return `ParseFailure` for encrypted, corrupt, or empty PDFs.

## DocxParser
Responsibilities:

- extract text and headings from `.docx` via `python-docx`,
- return `ParseFailure` for corrupt or unreadable files.

## PlainTextParser
Responsibilities:

- parse `.txt` into paragraph blocks,
- handle encoding gracefully.

## ChunkingService
Responsibilities:

- split parsed text into structure-aware chunks,
- produce chunk metadata such as section path and index.

## EmbeddingService
Responsibilities:

- generate embeddings for chunks and user queries,
- expose a stable interface independent of provider choice.

## VectorIndexService
Responsibilities:

- insert vectors into Qdrant,
- delete vectors,
- reindex versions,
- run scoped queries.

## RetrievalService
Responsibilities:

- embed user query,
- query Qdrant with strict filters,
- deduplicate results,
- return top-k chunks for prompt assembly.

Does not:

- build final prompt,
- call the generation model directly.

## PromptBuilder
Responsibilities:

- combine system instructions,
- conversation memory,
- retrieved chunks,
- user question,
- scope guidance.

## LlmGateway
Responsibilities:

- call Ollama,
- select runtime model,
- handle timeouts,
- handle retries,
- apply runtime options.

Implementation notes:

- Uses a single persistent `httpx.Client` (connection pooling, created at gateway init).
- Generation call is dispatched via `asyncio.run_in_executor` to avoid blocking the FastAPI event loop during LLM inference.

## MemoryService
Responsibilities:

- fetch recent messages,
- maintain rolling summary,
- produce memory package for prompt builder.

## ConversationContextualizer (E2)
Responsibilities:

- transform follow-up questions into standalone queries,
- resolve pronouns and vague references using recent turns and summary,
- produce `retrieval_memory` and `generation_memory` as separate packages,
- fall back to original message on timeout or error.

## QueryRewriteService (E1)
Responsibilities:

- generate alternative query phrasings for broader retrieval recall,
- support `disabled`, `single_rewrite`, and `multi_query` modes,
- use conversation context for better rewrites,
- fall back to original query on failure.

## MultiQueryRetrievalService (E1)
Responsibilities:

- run retrieval for each rewritten query,
- merge and deduplicate candidate chunks by `chunk_id`,
- preserve deterministic ordering.

## ClassificationService (E5)
Responsibilities:

- classify document type at ingestion time (`procedure`, `policy`, `instruction`, `faq`, `form`, `other`),
- classify query intent for routing (`qa`, `summary`, `extraction`, `admin_lookup`, `other`),
- expose confidence score with each result,
- never block pipeline — failures are advisory.

## RequestRouter (E7)
Responsibilities:

- select the appropriate capability mode for each chat turn,
- use query classification and conversation context as signals,
- fall back to `qa` when confidence is below threshold,
- remain the backend's authoritative routing decision.

## CapabilityOrchestrator (E7)
Responsibilities:

- execute the selected capability based on routing decision,
- dispatch to QA, summarization, extraction, admin lookup, or refusal handlers,
- short-circuit LLM call for `refuse_out_of_scope` mode.

## ExtractionService (E3)
Responsibilities:

- extract structured JSON data from document context,
- validate output against a predefined schema,
- return typed failure envelope when validation fails,
- support schemas: `procedure_metadata_v1`, `approval_path_v1`, `document_brief_v1`, `deadline_and_required_documents_v1`.

## SummarizationService (E4)
Responsibilities:

- generate document or section summaries in configurable formats,
- support `plain_summary`, `bullet_brief`, `checklist`, `key_points_and_risks`,
- orchestrate map/reduce for long documents (> `SUMMARIZATION_MAX_SOURCE_CHUNKS` chunks),
- include source attribution in every summary response.

## FeedbackService (E8)
Responsibilities:

- persist structured user feedback linked to `workspace_id`, `conversation_id`, `message_id`,
- support helpfulness, source quality, and answer completeness ratings with optional comment,
- upsert on repeated feedback for the same message,
- expose aggregated feedback for admin analysis.

## CitationService
Responsibilities:

- map retrieved chunks into user-visible sources,
- hide internal implementation details from UI.

## AdminPanel
Responsibilities:

- manage documents,
- manage versions,
- trigger reindex,
- show processing status,
- manage workspace-level configuration.

Current status:
- the admin surface is optimized for local bootstrap and testing,
- some admin/bootstrap endpoints are intentionally relaxed,
- production-grade role hardening is out of scope for the local-only MVP.

## React Frontend
Responsibilities:

- render chat,
- render sources,
- let user select workspace,
- let user apply explicit scope filters,
- call backend APIs,
- keep UI state.

Does not:

- decide data eligibility,
- bypass backend security,
- own retrieval logic.

## assistant-ui integration
Responsibilities:

- provide chat layout and chat interaction primitives,
- support custom renderers for sources and metadata.

## Local filesystem storage
Responsibilities:

- store original file artifacts,
- keep file paths versioned and workspace-scoped.

## PostgreSQL
Responsibilities:

- store source-of-truth application state.

## Qdrant
Responsibilities:

- store and query vector representations.

## Ollama + Bielik
Responsibilities:

- generate final answers in Polish.

Deployment:

- Can run natively on the host (recommended on Apple Silicon — uses Metal GPU) or as a Docker container (`--profile ollama`).
- Recommended model: `SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M` (~6 GB RAM, good quality/speed tradeoff).
- `OLLAMA_HOST` must be set to match the chosen mode (see CONFIGURATION.md).
