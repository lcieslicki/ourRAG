# Observability

## Goals

The platform should provide enough visibility to:

- debug retrieval failures,
- debug document processing failures,
- understand answer latency,
- detect tenant-isolation regressions early,
- identify low-quality retrieval cases.

## Metrics to track

The lists below describe desired observability. Current local implementation has structured logs, chat processing events over WebSocket, processing job state, and selected audit records. It does not yet expose a metrics endpoint or tracing backend.

### API
- request count
- error rate
- p95 latency
- p99 latency

### Chat pipeline
- retrieval latency
- prompt build latency
- LLM latency
- end-to-end response latency

### Ingestion
- upload count
- processing queue depth
- processing failure rate
- indexing latency

### Retrieval quality signals
- empty retrieval count
- no-answer response rate
- average source count per answer
- low-score retrieval rate

### Worker health
- job retry count
- failed jobs
- stuck jobs
- average processing duration

## Logs

Log structured events for:

- chat request started,
- workspace resolved,
- retrieval completed,
- LLM call completed,
- answer stored,
- document processing started,
- document processing failed,
- version activated or invalidated.

Avoid logging sensitive raw content unnecessarily.

Current chat processing events intentionally redact raw prompts, messages, query text, summaries, and chunk text before sending them to the frontend event stream.

## Correlation
Attach correlation identifiers to request and worker flows when possible.

Current implementation has per-conversation and per-message event metadata, but no general request correlation ID middleware yet.

## Audit visibility
Admin-facing events should be inspectable for:

- uploads,
- invalidations,
- reindex operations,
- destructive actions.

Current audit visibility is partial and focused on version lifecycle, reindex requests, workspace settings changes, and selected destructive bootstrap actions.

## Future options
This document intentionally leaves room for future integration with centralized logging and tracing tooling.
