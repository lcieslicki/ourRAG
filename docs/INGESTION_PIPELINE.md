# Ingestion Pipeline

## Scope

MVP supports only Markdown (`.md`) files as document input.

Future planned input types:

- PDF,
- TXT,
- DOCX.

The architecture must remain parser-pluggable from day one.

## Pipeline stages

### 1. Upload
An admin uploads a file to a selected workspace.

Backend actions:

- validate workspace permission,
- create logical document if needed,
- create document version,
- store original file on local filesystem,
- enqueue asynchronous processing job.

### 2. Parse
Worker selects parser by file type.

For MVP:
- `MarkdownParser`

Parser output:
- normalized text,
- structural hints such as headings.

### 3. Normalize
Normalize parsed text:

- standardize line endings,
- remove redundant empty lines where useful,
- preserve meaningful markdown hierarchy,
- preserve headings and list structure where possible.

### 4. Chunk
Use structure-aware chunking instead of naive fixed slicing.

Recommended behavior:

- prefer heading boundaries,
- keep chunks semantically coherent,
- preserve `section_path`,
- keep chunk size bounded,
- apply overlap between chunks.

### 5. Embed
Generate embeddings for each chunk using the configured embedding model.

### 6. Index
Insert chunk vectors and payload metadata into Qdrant.

### 7. Finalize
Mark document version as indexed and ready.

## Recommended chunking strategy for Markdown

### Principles
- prefer semantic boundaries over raw character counts,
- avoid chunks that span unrelated sections,
- preserve section hierarchy for source attribution,
- keep chunk sizes stable enough for retrieval quality.

### Initial recommended defaults
- `chunk_size`: 1000–1400 characters or equivalent token-aware approximation,
- `chunk_overlap`: 100–200 characters,
- split first by headings,
- then by paragraph boundaries,
- only fall back to hard splitting if sections are too large.

### Example metadata per chunk
- `chunk_index`
- `section_path`
- `heading`
- `workspace_id`
- `document_id`
- `document_version_id`
- `language`
- `is_active`

## Version-aware ingestion

When a new document version is uploaded:

- it creates a new `document_version`,
- it does not automatically erase older versions,
- admin decides activation / invalidation policy,
- retrieval should use active versions only by default.

## Reindex triggers

Reindex may be required when:

- embedding model changes,
- chunking strategy changes,
- parser changes,
- payload schema changes,
- active version status changes.

## Async processing requirements

Processing must be asynchronous.

Suggested job types:

- `parse_document`
- `chunk_document`
- `embed_document`
- `index_document`
- `cleanup_document_vectors`
- `reindex_document_version`

## Idempotency requirements

Every ingestion step should be idempotent where feasible.

Examples:

- duplicate indexing should not create duplicate active vectors,
- repeated failed jobs should not corrupt document status,
- cleanup should tolerate partially indexed versions.

## Future extensions

The pipeline should reserve interfaces for future parsers:

- `PdfParser`
- `TxtParser`
- `DocxParser`

Future enhancements may include:

- OCR fallback for PDFs when absolutely needed,
- table extraction,
- attachment metadata extraction,
- language detection,
- content classification,
- checksum-based duplicate detection.
