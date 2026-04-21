# Failure Modes

## Purpose

This document lists expected failure modes and the intended system behavior.

## Chat failures

### No retrieval context
Behavior:
- assistant responds that the answer is not available in current documents,
- no hallucinated answer should be produced.

### LLM timeout
Behavior:
- return controlled error to frontend,
- preserve conversation integrity,
- do not store partial broken assistant response.

### Invalid conversation scope
Behavior:
- reject request,
- do not continue chat under wrong workspace.

## Ingestion failures

### Unsupported file type
Behavior:
- reject upload with clear message.

### Parse failure
Behavior:
- mark version as failed,
- keep original file for admin review,
- allow retry after correction.

### Embedding failure
Behavior:
- mark job failed,
- allow retry,
- avoid partially visible "ready" state.

### Indexing failure
Behavior:
- do not mark document version ready,
- allow cleanup and retry.

## Versioning failures

### Multiple active versions accidentally enabled
Behavior:
- prevent via application rule and database constraint or transactional guard.

### Invalidated version still retrieved
Behavior:
- treated as severe bug; retrieval filters must prevent this.

## Security failures

### Cross-workspace retrieval
Behavior:
- treated as critical incident,
- should be prevented by layered tests and mandatory filters.

### Unauthorized admin action
Behavior:
- for user-facing and version lifecycle operations, reject through role checks,
- local bootstrap admin endpoints may be intentionally relaxed,
- complete denial audit is not implemented in the local-only MVP.

## Memory failures

### Summary drift
Behavior:
- treat summary as helper context, not ultimate truth,
- retrieval-backed facts should dominate.

### Excessive prompt size
Behavior:
- truncate recent history,
- rely on summary,
- keep answer quality stable rather than blindly overflowing prompt.

## Recovery strategy

For most failures:
- record structured error,
- expose status in admin view,
- support retry where safe,
- preserve audit trail.

Current implementation records ingestion failures in processing jobs and keeps document versions out of `ready` state until indexing succeeds. Full audit coverage is partial.
