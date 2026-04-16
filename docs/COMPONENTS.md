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

## Worker
Responsibilities:

- parse uploaded files,
- chunk text,
- generate embeddings,
- index vectors,
- refresh conversation summaries,
- run cleanup and reindex jobs.

Does not:

- serve user-facing APIs.

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

## MemoryService
Responsibilities:

- fetch recent messages,
- maintain rolling summary,
- produce memory package for prompt builder.

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
