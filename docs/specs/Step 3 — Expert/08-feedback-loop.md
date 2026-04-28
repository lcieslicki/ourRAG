# Spec: Feedback Loop

## Goal
Capture user feedback on answer usefulness, source quality, and response correctness so the system can support measurable improvement over time.

## Baseline assumption
The MVP provides answers and sources but does not yet persist structured end-user quality signals.

## Scope

### In scope
- feedback data model
- backend API for rating responses
- optional frontend feedback UI
- reporting-ready feedback schema
- linkage between feedback and chat/retrieval artifacts

### Out of scope
- online self-training from feedback
- ranking model training in the same phase
- complex moderation workflow

## Functional requirements

### FR-1 Feedback actions
Initial recommended actions:
- helpful / not_helpful
- source_useful / source_not_useful
- answer_complete / answer_incomplete
- optional free-text comment

### FR-2 Entity linkage
Feedback records should link, where possible, to:
- workspace_id
- conversation_id
- message_id
- response_mode
- selected_mode
- retrieval mode
- reranking enabled flag
- cited source IDs or chunk IDs

### FR-3 API surface
Add backend support for:
- submitting feedback for an assistant response
- listing/aggregating feedback for admin analysis
- optional export/report-friendly views

### FR-4 Idempotency and update rules
If the same user updates feedback on the same response, the backend should either:
- update the existing record, or
- keep a versioned audit trail explicitly

### FR-5 Privacy and safety
Do not store unnecessary secrets or oversized raw payloads in feedback records. Comments should be bounded and sanitized.

## Suggested schema
```json
{
  "workspace_id": "ws_001",
  "conversation_id": "conv_321",
  "message_id": "msg_789",
  "helpfulness": "helpful",
  "source_quality": "source_useful",
  "answer_completeness": "answer_complete",
  "comment": "Brakowało wyjątku dla stażystów."
}
```

## Configuration
- `FEEDBACK_ENABLED=true`
- `FEEDBACK_UI_ENABLED=true`
- `FEEDBACK_COMMENT_MAX_CHARS=1000`

## Testing

### Unit
- feedback payload validation
- update-vs-create behavior
- comment length enforcement

### Integration
- feedback submission links correctly to response artifacts
- admin listing/aggregation is workspace-safe
- repeated feedback updates behave as designed

### E2E
- user marks an answer as not helpful and the feedback is persisted

## Definition of Done
- structured feedback can be captured per assistant response
- records are linked to relevant retrieval/chat metadata
- admins can inspect aggregated feedback safely
