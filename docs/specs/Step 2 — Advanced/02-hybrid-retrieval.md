# Spec: Hybrid Retrieval

## Goal
Improve retrieval quality by combining semantic vector retrieval with lexical retrieval for exact-match heavy queries such as procedure names, acronyms, identifiers, and document titles.

## Baseline assumption
The MVP already has vector retrieval using embeddings and Qdrant, with workspace and active-version filtering enforced in the backend.

## Scope

### In scope
- lexical retrieval path
- hybrid merge strategy
- per-channel score metadata
- config-driven retrieval modes
- comparison support for evaluation

### Out of scope
- external search engines
- ML-trained merge model
- OCR-specific retrieval logic

## Functional requirements

### FR-1 Dual retrieval paths
The backend must support:
- `vector_only`
- `hybrid`

In hybrid mode it must execute:
- semantic retrieval via embeddings and Qdrant
- lexical retrieval via relational search

### FR-2 Lexical retrieval source
Recommended first implementation: PostgreSQL full-text search over persisted chunk/searchable text.

Searchable fields:
- chunk text
- heading
- section path text
- document title
- optional category

### FR-3 Mandatory filters on both channels
Both semantic and lexical retrieval must enforce:
- `workspace_id`
- active document versions only
- optional filters already supported by MVP: `category`, `selected_document_ids`, `language`

### FR-4 Merge behavior
Hybrid retrieval must:
1. fetch semantic top `K_semantic`
2. fetch lexical top `K_lexical`
3. normalize scores per channel
4. merge by `chunk_id`
5. return final candidate list for reranking or direct prompt use

### FR-5 Retrieval provenance
Each returned candidate should expose:
- `retrieval_channels`: `semantic`, `lexical`, or both
- raw channel scores if available
- merged score

### FR-6 Graceful degradation
If lexical retrieval is unavailable or disabled, the system must fall back to vector-only retrieval without breaking chat flow.

## Suggested data/index impact
Add or reuse relational searchable chunk storage with:
- `chunk_id`
- `workspace_id`
- `document_id`
- `document_version_id`
- `document_title`
- `heading`
- `section_path_text`
- `chunk_text`
- `language`
- `category`
- `is_active`
- full-text search vector/index

## Score normalization and merge
Recommended v1 merge:
- min-max normalize semantic scores to `[0,1]`
- min-max normalize lexical scores to `[0,1]`
- merged score = `semantic_weight * semantic_norm + lexical_weight * lexical_norm`

Default weights:
- `semantic_weight = 0.65`
- `lexical_weight = 0.35`

Tie-breakers:
1. merged score descending
2. semantic score descending
3. lexical score descending
4. chunk ID ascending for deterministic ordering

## Suggested interfaces
- `SemanticRetriever.retrieve(request) -> list[Candidate]`
- `LexicalRetriever.retrieve(request) -> list[Candidate]`
- `HybridRetrievalService.retrieve(request) -> list[Candidate]`

## Configuration
- `RETRIEVAL_MODE=vector_only|hybrid`
- `RETRIEVAL_HYBRID_SEMANTIC_TOP_K=20`
- `RETRIEVAL_HYBRID_LEXICAL_TOP_K=20`
- `RETRIEVAL_HYBRID_FINAL_TOP_K=12`
- `RETRIEVAL_HYBRID_SEMANTIC_WEIGHT=0.65`
- `RETRIEVAL_HYBRID_LEXICAL_WEIGHT=0.35`

## Testing

### Unit
- score normalization
- merge deduplication by chunk ID
- deterministic ordering

### Integration
- exact title query improves over vector-only baseline
- category/document/language filters work on both channels
- lexical failure falls back safely

### Evaluation
- compare vector-only vs hybrid on benchmark fixture set

## Definition of Done
- retrieval mode can be toggled by config
- hybrid returns deterministic merged candidates
- exact-match scenarios improve measurably on benchmark set
- fallback behavior is explicit and tested
