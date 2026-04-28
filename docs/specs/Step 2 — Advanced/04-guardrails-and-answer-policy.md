# Spec: Guardrails and Answer Policy

## Goal
Ensure the assistant only answers when the request is in scope and supported by sufficient retrieved context.

## Baseline assumption
The MVP prompt already tells the model to answer from context and say it does not know when context is insufficient. Advanced mode moves the main gating decisions into explicit backend policy.

## Scope

### In scope
- backend response modes
- scope check
- retrieval sufficiency check
- structured refusal metadata
- prompt branching for answer path

### Out of scope
- comprehensive safety classifier for all abuse categories
- user-specific compliance/legal policies
- frontend-side decision logic

## Response modes
The backend must support at least:
- `answer_from_context`
- `refuse_out_of_scope`
- `insufficient_context`

Optional future mode:
- `degraded_answer_with_warning`

## Functional requirements

### FR-1 Backend-authoritative decision
Guardrail decisions must be made in the backend before generation.

### FR-2 In-scope check
The system must implement a pragmatic in-scope detector.
Recommended first version:
- rule-based domain heuristics using workspace/document domain language
- optional classifier hook for future evolution

### FR-3 Retrieval sufficiency gate
The backend must evaluate whether retrieved evidence is strong enough to justify generation.
Suggested initial signals:
- top retrieval score threshold
- minimum number of usable chunks
- optional lexical exact-match bonus
- optional reranker confidence threshold if available

### FR-4 Structured response metadata
Every chat response must include:
- `response_mode`
- `guardrail_reason` (nullable)
- optionally `guardrail_signals`

### FR-5 Prompt branching
Only `answer_from_context` should proceed to normal prompt construction and generation.
For refusal or insufficient-context modes, the backend may:
- return a templated response directly, or
- use a very small constrained prompt for formatting only

### FR-6 Citation behavior by mode
- `answer_from_context`: may include citations
- `refuse_out_of_scope`: no citations required
- `insufficient_context`: may include retrieved sources for transparency, but no unsupported claims

## Suggested decision order
1. validate workspace access
2. load memory package
3. run retrieval
4. evaluate in-scope
5. evaluate retrieval sufficiency
6. choose response mode
7. only for `answer_from_context`, build prompt and generate

## Suggested thresholds
Initial configurable thresholds:
- `GUARDRAILS_MIN_TOP_SCORE`
- `GUARDRAILS_MIN_USABLE_CHUNKS`
- `GUARDRAILS_IN_SCOPE_REQUIRED=true`

## Example response shape
```json
{
  "answer": "Nie mam wystarczających informacji w udostępnionej dokumentacji, aby odpowiedzieć pewnie.",
  "response_mode": "insufficient_context",
  "guardrail_reason": "retrieval_below_threshold",
  "cited_sources": []
}
```

## Configuration
- `GUARDRAILS_ENABLED=true`
- `GUARDRAILS_IN_SCOPE_REQUIRED=true`
- `GUARDRAILS_MIN_TOP_SCORE=0.72`
- `GUARDRAILS_MIN_USABLE_CHUNKS=2`
- `GUARDRAILS_USE_TEMPLATE_RESPONSES=true`

## Testing

### Unit
- in-scope rule evaluation
- sufficiency threshold evaluation
- response mode selection

### Integration
- out-of-scope request returns refusal mode
- weak retrieval returns insufficient-context mode
- strong retrieval returns normal answer mode
- frontend receives mode metadata

### E2E
- out-of-domain question is refused
- ambiguous question with weak evidence does not hallucinate

## Definition of Done
- backend enforces response modes
- weak or out-of-scope requests do not follow normal generation path
- mode metadata is visible to callers
- behavior is configurable and tested
