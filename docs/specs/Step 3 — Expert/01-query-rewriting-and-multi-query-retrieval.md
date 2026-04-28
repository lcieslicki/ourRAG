# Spec: Query Rewriting and Multi-Query Retrieval

## Goal
Improve retrieval recall for ambiguous, short, underspecified, or terminology-mismatched user questions by generating one or more rewritten retrieval queries before the normal retrieval pipeline runs.

## Baseline assumption
The system already supports workspace-scoped retrieval with optional hybrid search, reranking, and guardrails. This feature extends retrieval without replacing the existing single-query path.

## Scope

### In scope
- query rewriting abstraction
- one local query-rewrite strategy using the existing generation stack
- multi-query retrieval orchestration
- candidate merge and deduplication
- debug metadata and evaluation support

### Out of scope
- autonomous web search
- user-visible chain-of-thought
- aggressive query expansion that bypasses workspace filters
- external search providers

## Functional requirements

### FR-1 Rewrite modes
The backend must support:
- `disabled`
- `single_rewrite`
- `multi_query`

### FR-2 Input sources
Rewrite generation may use:
- current user message
- selected recent conversation turns
- conversation summary
- optional active filters such as category, document selection, and language

### FR-3 Rewrite safety
Every rewritten query must remain in the same authorized workspace scope and must preserve existing security and active-version filtering applied later in retrieval.

### FR-4 Multi-query retrieval flow
Recommended v1 flow:
1. contextualize the user question if needed
2. generate up to `N` rewritten retrieval queries
3. execute retrieval per query with existing filters
4. merge and deduplicate candidates by `chunk_id`
5. pass merged candidates to reranking or directly to prompt assembly

### FR-5 Rewrite quality rules
Rewrites should:
- expand synonyms or alternate phrasings
- resolve pronouns or vague references when supported by conversation context
- preserve user intent
- avoid inventing entities, document titles, or policy names not implied by the conversation

### FR-6 Provenance metadata
The retrieval debug payload should expose:
- original query
- contextualized query if produced
- generated retrieval rewrites
- retrieval query count
- which query matched each returned candidate if practical

## Suggested interfaces
- `QueryRewriteService.rewrite(request) -> RewritePlan`
- `MultiQueryRetrievalService.retrieve(request, rewrite_plan) -> list[Candidate]`

## Suggested rewrite payload
```json
{
  "original_query": "A kto to zatwierdza?",
  "contextualized_query": "Kto zatwierdza wniosek o szkolenie rozwojowe?",
  "rewritten_queries": [
    "kto zatwierdza wniosek o szkolenie rozwojowe",
    "akceptacja szkolenia rozwojowego",
    "approval path for development training request"
  ]
}
```

## Configuration
- `QUERY_REWRITE_MODE=disabled|single_rewrite|multi_query`
- `QUERY_REWRITE_MAX_QUERIES=3`
- `QUERY_REWRITE_INCLUDE_SUMMARY=true`
- `QUERY_REWRITE_INCLUDE_RECENT_MESSAGES=true`
- `QUERY_REWRITE_MODEL_PROVIDER=ollama`
- `QUERY_REWRITE_MODEL_NAME=<local model>`
- `QUERY_REWRITE_TIMEOUT_MS=3000`

## Testing

### Unit
- rewrite plan validation
- deduplication of duplicate rewrites
- deterministic merge ordering

### Integration
- short ambiguous query improves recall
- follow-up question uses conversation context safely
- disabled mode preserves baseline behavior
- timeout/failure falls back to original query only

### Evaluation
- compare baseline vs rewrite-enabled retrieval on benchmark questions that require paraphrase handling

## Definition of Done
- rewrite mode is configurable
- retrieval can operate on multiple generated queries
- fallback behavior is explicit and tested
- benchmark shows measurable improvement on underspecified queries
