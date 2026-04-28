# Spec: Observability and Tracing

## Goal
Make chat and ingestion flows diagnosable through structured logs, correlation IDs, stage timings, and terminal outcomes.

## Baseline assumption
The MVP already has some observability expectations referenced in documentation and hardening prompts. Advanced mode standardizes and enriches them.

## Scope

### In scope
- correlation IDs
- structured logging for key flows
- stage timing capture
- terminal outcomes for success/failure/degraded paths
- local-Docker-friendly inspection

### Out of scope
- full distributed tracing backend
- external hosted APM
- sensitive payload logging

## Functional requirements

### FR-1 Correlation IDs
Every chat request must carry or generate a correlation/request ID.
Ingestion jobs should carry a job correlation ID and link to document version IDs.

### FR-2 Structured event families
Emit structured logs for at least:
- chat request lifecycle
- retrieval start/finish
- hybrid retrieval merge
- reranking start/finish/fallback
- guardrail decision
- prompt build start/finish
- model call start/finish/error
- ingestion job state transitions

### FR-3 Stage timings
Capture durations for main stages such as:
- memory assembly
- retrieval
- reranking
- prompt build
- generation
- total chat latency

### FR-4 Terminal outcome logging
Always log final result state:
- success
- fallback
- refused_out_of_scope
- insufficient_context
- provider_timeout
- ingestion_failed

### FR-5 Secret hygiene
Logs must not leak secrets, raw credentials, or unnecessary full prompts by default.

## Suggested event payload shape
```json
{
  "event": "chat.completed",
  "request_id": "req_123",
  "workspace_id": "ws_001",
  "conversation_id": "conv_321",
  "retrieval_mode": "hybrid",
  "reranking_enabled": true,
  "response_mode": "answer_from_context",
  "latency_ms": {
    "retrieval": 104,
    "reranking": 57,
    "prompt_build": 8,
    "generation": 1420,
    "total": 1618
  },
  "status": "success"
}
```

## Suggested implementation points
- request middleware for correlation ID
- logger context binding helper
- stage timer utility/context manager
- ingestion worker logging wrapper

## Configuration
- `OBSERVABILITY_JSON_LOGS=true`
- `OBSERVABILITY_CHAT_TRACE_ENABLED=true`
- `OBSERVABILITY_RETRIEVAL_TRACE_ENABLED=true`
- `OBSERVABILITY_INGESTION_TRACE_ENABLED=true`
- `OBSERVABILITY_INCLUDE_DEBUG_FIELDS=false`

## Testing

### Unit
- correlation ID generation and propagation helpers
- logger context payload schema
- stage timer utility

### Integration
- chat request emits correlated event family
- ingestion job emits state transitions
- reranking failure emits fallback event

## Definition of Done
- main flows emit structured logs
- correlation IDs are propagated end-to-end
- timings are available for critical stages
- local debugging is materially easier
