# Spec: Citations and Source Attribution Hardening

## Goal
Harden the existing MVP source rendering into a precise, structured citation system that is deterministic, workspace-safe, and audit-friendly.

## Baseline assumption
The MVP already returns answer sources and renders them in the frontend. This feature extends that behavior without replacing the current chat architecture.

## Scope

### In scope
- normalized citation payload
- clear split between retrieved sources and cited sources
- prompt grounding updates
- backend citation selection rules
- frontend rendering updates for richer citations
- integration and E2E coverage

### Out of scope
- token-level provenance
- PDF page coordinates
- legal export format
- editable citations

## Functional requirements

### FR-1 Structured citation payload
Every assistant answer must return a stable citation schema.

Required fields per citation:
- `citation_id`
- `workspace_id`
- `document_id`
- `document_version_id`
- `chunk_id`
- `chunk_index`
- `document_title`
- `heading`
- `section_path`
- `excerpt`
- `language`
- `retrieval_score`
- `rank`

Optional fields:
- `category`
- `filename`
- `storage_uri`
- `version_label`

### FR-2 Separate source collections
Chat responses must distinguish between:
- `retrieved_sources`: all chunks that reached the final prompt context
- `cited_sources`: the subset exposed to the user as explicit support

### FR-3 Deterministic citation selection
The backend must choose `cited_sources` deterministically.

Recommended v1 rule:
- start from the final prompt chunk set after retrieval and reranking
- keep top `N` support chunks in final ordering
- deduplicate by `chunk_id`
- preserve rank order

### FR-4 Excerpt generation
`excerpt` must be generated in the backend from stored chunk text, safely truncated to configurable length.

### FR-5 Prompt grounding rule
Prompt builder must instruct the model to:
- answer only from supplied context
- avoid unsupported claims
- admit uncertainty if support is insufficient
- avoid pretending to know missing details

### FR-6 Workspace and active-version safety
All returned citations must belong to the authorized `workspace_id` and to active document versions only.

### FR-7 API compatibility
The API must evolve in a backward-aware way. If the existing frontend expects `sources`, either:
- map `sources` to `cited_sources` temporarily, or
- return both during a transition period.

## Suggested response shape
```json
{
  "answer": "...",
  "response_mode": "answer_from_context",
  "retrieved_sources": [
    {
      "citation_id": "cit_001",
      "document_title": "Training Policy",
      "heading": "Rodzaje szkoleń",
      "section_path": ["2. Rodzaje szkoleń"],
      "excerpt": "Szkolenia obowiązkowe są finansowane...",
      "chunk_index": 14,
      "retrieval_score": 0.913,
      "rank": 1
    }
  ],
  "cited_sources": [
    {
      "citation_id": "cit_001",
      "document_title": "Training Policy",
      "heading": "Rodzaje szkoleń",
      "section_path": ["2. Rodzaje szkoleń"],
      "excerpt": "Szkolenia obowiązkowe są finansowane...",
      "chunk_index": 14,
      "retrieval_score": 0.913,
      "rank": 1
    }
  ]
}
```

## Backend design

### Modules to add or update
- citation DTO/schema
- citation selection service
- chat response assembler
- prompt builder grounding section

### Suggested service contract
- `build_retrieved_sources(final_chunks) -> list[CitationDTO]`
- `select_cited_sources(final_chunks, config) -> list[CitationDTO]`

## Frontend design
- render compact source cards below assistant answer
- show document title, heading, section path, and excerpt
- allow expand/collapse for excerpt
- optionally badge cited sources as “used in answer”

## Configuration
- `CHAT_MAX_EXPOSED_CITATIONS=3`
- `CHAT_CITATION_EXCERPT_MAX_CHARS=300`
- `CHAT_INCLUDE_RETRIEVED_SOURCES=true`
- `CHAT_INCLUDE_CITED_SOURCES=true`
- `CHAT_CITATION_TRANSITION_INCLUDE_LEGACY_SOURCES=true`

## Testing

### Unit
- citation DTO validation
- excerpt truncation
- deterministic deduplication by chunk ID

### Integration
- chat response contains correct citation payload
- citations stay within workspace boundary
- inactive versions are never cited
- prompt contains grounding rule

### E2E
- answer shows citations in UI
- filters do not break citation rendering

## Definition of Done
- chat responses return normalized citations
- frontend renders them correctly
- citations are deterministic and workspace-safe
- backward compatibility is handled explicitly
