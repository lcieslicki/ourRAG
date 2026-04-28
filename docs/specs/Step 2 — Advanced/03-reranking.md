# Spec: Reranking

## Goal
Improve final prompt quality by reranking retrieved candidates after retrieval and before prompt assembly.

## Baseline assumption
The MVP already retrieves top-k chunks and passes them directly into prompt building. Advanced mode inserts an optional reranking stage between retrieval and prompt assembly.

## Scope

### In scope
- reranker abstraction
- one local reranker provider
- timeout/failure fallback
- final prompt chunk reordering
- evaluation hooks

### Out of scope
- reranker training
- external hosted rerankers
- introducing new chunks not already retrieved

## Functional requirements

### FR-1 Position in pipeline
Reranking must occur after retrieval and before prompt building.

### FR-2 Candidate-set safety
Reranking may only reorder or drop chunks from the retrieved candidate set. It must never introduce new chunks.

### FR-3 Provider abstraction
The system must expose a reranker interface independent of both retrieval and generation providers.

Suggested contract:
- `rerank(query, candidates) -> list[ScoredCandidate]`

### FR-4 Local provider
Implement one provider suitable for local-first development.
Recommended options:
- cross-encoder reranker running locally
- local model served through a dedicated service if already available

### FR-5 Safe fallback
If reranking times out, fails, or is disabled, the system must fall back to upstream retrieval order.

### FR-6 Configurability
Reranking must be individually configurable and easy to disable for comparison and debugging.

## Suggested flow
1. retrieval returns top `K_candidates`
2. reranker scores or reorders candidates
3. system selects final prompt top `K_prompt`
4. citation layer uses final chunk order

## Candidate metadata
Each reranked candidate should expose:
- `original_rank`
- `rerank_score`
- `final_rank`
- `retrieval_channels`

## Configuration
- `RERANKING_ENABLED=false`
- `RERANKING_PROVIDER=local_cross_encoder`
- `RERANKING_TOP_K_CANDIDATES=20`
- `RERANKING_FINAL_TOP_K=6`
- `RERANKING_TIMEOUT_MS=800`
- `RERANKING_FAIL_OPEN=true`

## Non-functional requirements
- must not noticeably destabilize chat latency
- deterministic ordering for equal rerank scores
- fail-open by default in user-facing chat flow

## Testing

### Unit
- rerank ordering
- tie-break deterministic behavior
- provider timeout handling

### Integration
- reranking changes final prompt set ordering
- reranking disabled keeps baseline ordering
- reranking failure falls back to retrieval order
- workspace-safe candidate handling preserved end-to-end

### Evaluation
- compare retrieval-only vs retrieval-plus-reranking on benchmark set

## Definition of Done
- reranking is optional and pluggable
- one local provider works end-to-end
- failure fallback is safe and tested
- benchmark comparison is possible
