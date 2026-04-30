# Ingestion Pipeline

## Scope

The pipeline supports the following document input types:

- `.md` — Markdown (baseline)
- `.txt` — plain text
- `.pdf` — PDF (text-based; encrypted or corrupted PDFs are rejected with a typed failure)
- `.docx` — Word documents

Additional types can be enabled via `ParserConfig`. Spreadsheet support (`.xlsx`) and OCR are available as feature-flagged extensions.

The parser layer is pluggable from the start — all parsers share a stable `ParsedDocument` contract consumed by downstream chunking.

## Pipeline stages

### 1. Upload
A local admin uploads a file to a selected workspace.

Backend actions:

- validate workspace permission,
- create logical document if needed,
- create document version,
- store original file on local filesystem,
- enqueue asynchronous processing job.

The standard document upload endpoint enqueues jobs. Local admin upload and folder indexing may also trigger the ingestion runner through backend background tasks.

### 2. Parse
The ingestion runner selects parser by file type via `ParserRegistry`.

Available parsers:
- `MarkdownParser` — `.md`, heading-aware
- `PlainTextParser` — `.txt`, paragraph-based
- `PdfParser` — `.pdf`, page-by-page extraction with heading heuristics, preserves page numbers
- `DocxParser` — `.docx`, heading and table extraction via `python-docx`

If the parser returns a `ParseFailure` (encrypted, corrupt, empty), the document version is marked as `failed` with a typed reason. No garbage is indexed.

Parser output:
- `normalized_text` — merged plain text
- `blocks` — structured list of headings and paragraphs with section paths
- `parser_name` and `parser_version` — for auditability

### 2b. Classify (optional)
If `CLASSIFICATION_ENABLED=true`, after parsing the ingestion runner classifies the document:

- `RuleBasedDocumentClassifier` assigns a document type: `procedure`, `policy`, `instruction`, `faq`, `form`, or `other`
- result stored in `document_version.inferred_doc_type` and `inferred_doc_type_confidence`
- classification never blocks ingestion — failures are logged and skipped

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

Current implementation note:
- jobs are tracked in PostgreSQL,
- job execution is handled by the backend ingestion runner,
- Docker Compose does not yet include a separate long-running worker service.

## Idempotency requirements

Every ingestion step should be idempotent where feasible.

Examples:

- duplicate indexing should not create duplicate active vectors,
- repeated failed jobs should not corrupt document status,
- cleanup should tolerate partially indexed versions.

## Parse failure handling

If a document cannot be parsed:

- `document_version.processing_status` is set to `failed`
- `ParseFailure.reason` is one of: `encrypted`, `corrupt`, `empty`, `unsupported`
- downstream stages (chunk, embed, index) are not triggered
- no partial or garbage content is indexed

## Future extensions

Possible future enhancements:

- OCR adapter for scanned PDFs (behind `PARSER_OCR_ENABLED` flag)
- spreadsheet tabular extraction (`SpreadsheetParser`, behind `PARSER_SPREADSHEET_ENABLED`)
- language detection at parse time
- checksum-based duplicate detection
