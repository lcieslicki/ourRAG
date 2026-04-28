# Spec: Summarization and Briefing

## Goal
Add a document-aware summarization mode that can produce concise, structured briefings instead of only direct Q&A responses.

## Baseline assumption
The current system supports chat Q&A over retrieved context. Summarization is a new output mode that may operate on selected documents, search results, or retrieved sections.

## Scope

### In scope
- document summary mode
- section summary mode
- checklist/briefing output formats
- source-backed summarization
- long-document map/reduce style summarization when needed

### Out of scope
- abstractive summaries with no source visibility
- presentation generation
- multilingual translation workflows unless already supported elsewhere

## Functional requirements

### FR-1 Summary scopes
Support at least:
- single selected document summary
- selected section summary
- answer-adjacent briefing from retrieved chunks

### FR-2 Output formats
Initial recommended formats:
- `plain_summary`
- `bullet_brief`
- `checklist`
- `key_points_and_risks`

### FR-3 Source attribution
Summaries must include sources/citations just like chat answers or extraction outputs.

### FR-4 Long-document strategy
For large documents the backend should support a bounded summarization flow such as:
1. segment document or section set
2. generate partial summaries
3. reduce into final briefing

### FR-5 Deterministic response envelope
Suggested envelope:
```json
{
  "mode": "summarization",
  "format": "bullet_brief",
  "scope": {
    "document_id": "doc_123",
    "section_path": ["2. Rodzaje szkoleń"]
  },
  "summary": "...",
  "sources": [...]
}
```

## Suggested modules
- summarization request contract
- summary prompt builder
- long-document summarization orchestrator
- format renderer/normalizer

## Configuration
- `SUMMARIZATION_ENABLED=true`
- `SUMMARIZATION_MAX_SOURCE_CHUNKS=12`
- `SUMMARIZATION_LONG_DOC_MAP_REDUCE_ENABLED=true`
- `SUMMARIZATION_TIMEOUT_MS=6000`

## Testing

### Unit
- scope validation
- format normalization
- response envelope building

### Integration
- summary from selected document works
- section summary preserves section scope
- long-document mode performs bounded map/reduce flow

### E2E
- user requests a checklist from a selected policy document and receives sourced output

## Definition of Done
- summarization is a first-class mode
- at least two output formats are supported
- large document handling is bounded and testable
- summaries remain source-backed
