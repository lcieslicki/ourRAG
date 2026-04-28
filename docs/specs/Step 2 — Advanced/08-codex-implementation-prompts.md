# Codex Prompt Set — Advanced Step 2

Run these prompts in order. Keep each task limited to one feature area. Review the diff after each step.

## Prompt A1 — Citations hardening

```text
Read README.md, AGENTS.md, and all files in docs/ first.
Also read the attached spec file: 01-citations-and-source-attribution.md.

Implement the citations/source-attribution enhancement only.

Requirements:
- treat the current implementation as the baseline
- do not rewrite chat orchestration from scratch
- normalize the backend citation payload
- distinguish between retrieved_sources and cited_sources
- update prompt building so the model is instructed to stay grounded in the provided chunks
- keep workspace_id and active-version safety enforced
- update the frontend source rendering only as much as needed for the new payload
- add tests for citation payload correctness, workspace/version safety, and prompt behavior

At the end:
- summarize files changed
- summarize API payload changes
- mention any assumptions made
```

## Prompt A2 — Hybrid retrieval

```text
Read README.md, AGENTS.md, docs/, and 02-hybrid-retrieval.md first.

Implement hybrid retrieval only.

Requirements:
- preserve the existing retrieval service as a clear baseline path
- add a lexical retrieval path suitable for local-first development
- combine semantic and lexical retrieval into a hybrid retrieval service
- keep strict workspace_id and active-version filtering in both paths
- support existing optional filters such as category, selected document IDs, and language
- add configuration flags so vector-only and hybrid modes can be compared
- expose retrieval debug metadata only where appropriate
- add tests for exact-match improvements, filter correctness, fallback behavior, and deterministic merge ordering

At the end:
- summarize architectural changes
- summarize config added
- explain fallback behavior
```

## Prompt A3 — Reranking

```text
Read README.md, AGENTS.md, docs/, 02-hybrid-retrieval.md, and 03-reranking.md first.

Implement reranking only.

Requirements:
- add a reranker abstraction independent of retrieval and generation providers
- implement one local reranker provider suitable for local development
- place reranking after retrieval and before prompt assembly
- do not let reranking introduce new chunks; it may only reorder the candidate set
- add safe timeout/failure fallback to upstream retrieval ordering
- keep the feature configurable and easy to disable
- add tests for ordering, fallback behavior, and workspace-safe integration

At the end:
- summarize provider/runtime assumptions
- summarize config added
- explain how reranking changes the final prompt chunk set
```

## Prompt A4 — Guardrails and answer policy

```text
Read README.md, AGENTS.md, docs/, and 04-guardrails-and-answer-policy.md first.

Implement guardrails and answer policy only.

Requirements:
- enforce guardrail decisions in the backend
- support at least these response modes:
  - answer_from_context
  - refuse_out_of_scope
  - insufficient_context
- add a pragmatic scope check and retrieval sufficiency gate
- avoid making the frontend authoritative for any policy decisions
- update prompt behavior only for the answer_from_context path
- return structured response metadata for response_mode and guardrail_reason
- add tests for out-of-scope refusal, insufficient-context handling, and normal answer flow

At the end:
- summarize response modes
- summarize thresholds/config added
- explain any MVP-compatible shortcuts taken
```

## Prompt A5 — Evaluation suite

```text
Read README.md, AGENTS.md, docs/, and 05-evaluation-suite.md first.

Implement the evaluation suite only.

Requirements:
- add a benchmark dataset format for retrieval and answer evaluation
- implement a local offline runner
- compute at least hit@k, MRR, answer signal coverage, citation presence, and guardrail mode accuracy
- produce machine-readable and human-readable reports
- include a small but representative sample dataset/fixtures
- make it easy to compare baseline vector retrieval vs hybrid and/or reranking
- keep the implementation practical for local Docker development and CI smoke usage

At the end:
- summarize the dataset schema
- summarize available metrics
- explain how to run the evaluation locally
```

## Prompt A6 — Observability and tracing

```text
Read README.md, AGENTS.md, docs/, and 06-observability-and-tracing.md first.

Implement the observability and tracing improvements only.

Requirements:
- add correlation IDs for chat requests and ingestion flows where practical
- add structured logs for retrieval, reranking, chat orchestration, and ingestion jobs
- include stage timings and terminal outcomes
- avoid leaking secrets or adding noisy logs by default
- keep the logging useful in local Docker development
- add tests for correlation ID propagation and structured event emission where practical

At the end:
- summarize logged event families
- summarize new config or middleware
- explain how to inspect logs locally
```

## Prompt A7 — Chunking lab

```text
Read README.md, AGENTS.md, docs/, 05-evaluation-suite.md, and 07-chunking-lab.md first.

Implement the chunking lab only.

Requirements:
- preserve the current chunking implementation as the baseline strategy
- introduce a strategy registry and explicit strategy metadata
- add at least one table-aware markdown strategy
- support reindexing by selected strategy
- integrate with the evaluation suite so strategies can be compared
- keep production defaults stable and predictable
- add tests for deterministic strategy output, metadata persistence, and table-aware behavior

At the end:
- summarize implemented strategies
- summarize reindex/evaluation workflow
- list any experimental areas kept behind flags
```
