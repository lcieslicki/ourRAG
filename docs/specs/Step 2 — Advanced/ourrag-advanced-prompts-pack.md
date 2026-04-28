# ourRAG — Prompt Pack for Codex Based on the New Advanced Documentation

This prompt pack is intended for implementing all features from **Step 2 — Advanced** based on the new specs package.

## How to use

- Run prompts in order.
- Keep each Codex task limited to one feature area.
- Review the diff after each step.
- Treat the current implementation as the baseline.
- Read `README.md`, `AGENTS.md`, and all files in `docs/` before making decisions.
- Read the relevant spec file for the current step before changing code.
- Update documentation continuously instead of leaving it stale until the very end.

---

## Prompt 0 — Documentation sync against current implementation

```text
Read README.md, AGENTS.md, all files in docs/, and all files from the attached advanced specs pack first.

Do not implement any new feature yet.

Task:
- compare the current implementation with the new Advanced Step 2 specs
- identify which parts of the specs are already partially covered by the MVP
- identify mismatches between existing docs and the new specs
- propose the smallest documentation updates needed before implementation starts
- create or update a single tracking document, preferably docs/ADVANCED_STEP_2_PLAN.md, containing:
  - feature list
  - current status per feature: not started / partial / implemented
  - implementation order
  - dependencies
  - risks

Rules:
- do not invent features outside the provided specs
- do not rewrite architecture without a documented reason
- keep the result concise and implementation-oriented

At the end:
- summarize findings
- list documentation files changed
- list open questions, if any
```

---

## Prompt 1 — Citations and source attribution hardening

```text
Read README.md, AGENTS.md, all files in docs/, docs/ADVANCED_STEP_2_PLAN.md if it exists, and the attached spec file 01-citations-and-source-attribution.md first.

Implement the citations/source-attribution enhancement only.

Requirements:
- treat the current implementation as the baseline
- do not rewrite chat orchestration from scratch
- normalize the backend citation payload
- clearly distinguish between retrieved_sources and cited_sources
- update prompt building so the model is explicitly instructed to stay grounded in the provided chunks
- keep workspace_id and active-version safety enforced
- update the frontend source rendering only as much as needed for the new payload
- preserve backward compatibility if the current frontend/API still expects legacy sources
- add tests for citation payload correctness, workspace/version safety, and prompt behavior
- update relevant documentation after code changes

Documentation tasks:
- update docs/API_CONTRACT.md with the new response payload
- update docs/RETRIEVAL.md with citation semantics
- update docs/CHAT_MEMORY.md or prompt-related docs if grounding instructions changed
- update docs/ADVANCED_STEP_2_PLAN.md status

At the end:
- summarize files changed
- summarize API payload changes
- mention any assumptions made
```

---

## Prompt 2 — Hybrid retrieval

```text
Read README.md, AGENTS.md, all files in docs/, docs/ADVANCED_STEP_2_PLAN.md if it exists, and the attached spec file 02-hybrid-retrieval.md first.

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
- update relevant documentation after code changes

Documentation tasks:
- update docs/RETRIEVAL.md with vector-only vs hybrid modes
- update docs/ARCHITECTURE.md if retrieval flow changes materially
- update docs/CONFIGURATION.md with new retrieval variables
- update docs/TESTING.md with hybrid retrieval coverage
- update docs/ADVANCED_STEP_2_PLAN.md status

At the end:
- summarize architectural changes
- summarize config added
- explain fallback behavior
```

---

## Prompt 3 — Reranking

```text
Read README.md, AGENTS.md, all files in docs/, docs/ADVANCED_STEP_2_PLAN.md if it exists, and the attached spec file 03-reranking.md first.

Implement reranking only.

Requirements:
- add a reranker abstraction independent of retrieval and generation providers
- implement one local reranker provider suitable for local development
- place reranking after retrieval and before prompt assembly
- do not let reranking introduce new chunks; it may only reorder the candidate set
- add safe timeout/failure fallback to upstream retrieval ordering
- keep the feature configurable and easy to disable
- add tests for ordering, fallback behavior, and workspace-safe integration
- update relevant documentation after code changes

Documentation tasks:
- update docs/RETRIEVAL.md with reranking stage and candidate flow
- update docs/ARCHITECTURE.md if the chat pipeline diagram/description changes
- update docs/CONFIGURATION.md with reranking variables
- update docs/TESTING.md with reranking coverage
- update docs/ADVANCED_STEP_2_PLAN.md status

At the end:
- summarize provider/runtime assumptions
- summarize config added
- explain how reranking changes the final prompt chunk set
```

---

## Prompt 4 — Guardrails and answer policy

```text
Read README.md, AGENTS.md, all files in docs/, docs/ADVANCED_STEP_2_PLAN.md if it exists, and the attached spec file 04-guardrails-and-answer-policy.md first.

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
- update relevant documentation after code changes

Documentation tasks:
- update docs/API_CONTRACT.md with response_mode and guardrail_reason
- update docs/SECURITY.md or equivalent policy docs if refusal behavior affects trust boundaries
- update docs/RETRIEVAL.md or chat docs where insufficient context behavior is described
- update docs/TESTING.md with guardrail test coverage
- update docs/ADVANCED_STEP_2_PLAN.md status

At the end:
- summarize response modes
- summarize thresholds/config added
- explain any MVP-compatible shortcuts taken
```

---

## Prompt 5 — Evaluation suite

```text
Read README.md, AGENTS.md, all files in docs/, docs/ADVANCED_STEP_2_PLAN.md if it exists, and the attached spec file 05-evaluation-suite.md first.

Implement the evaluation suite only.

Requirements:
- add a benchmark dataset format for retrieval and answer evaluation
- implement a local offline runner
- compute at least hit@k, MRR, answer signal coverage, citation presence, and guardrail mode accuracy
- produce machine-readable and human-readable reports
- include a small but representative sample dataset/fixtures
- make it easy to compare baseline vector retrieval vs hybrid and/or reranking
- keep the implementation practical for local Docker development and CI smoke usage
- update relevant documentation after code changes

Documentation tasks:
- add or update docs/EVALUATION.md
- update docs/TESTING.md with evaluation usage
- update docs/FIXTURES.md if new benchmark fixtures are added
- update README.md with local evaluation commands if appropriate
- update docs/ADVANCED_STEP_2_PLAN.md status

At the end:
- summarize the dataset schema
- summarize available metrics
- explain how to run the evaluation locally
```

---

## Prompt 6 — Observability and tracing

```text
Read README.md, AGENTS.md, all files in docs/, docs/ADVANCED_STEP_2_PLAN.md if it exists, and the attached spec file 06-observability-and-tracing.md first.

Implement the observability and tracing improvements only.

Requirements:
- add correlation IDs for chat requests and ingestion flows where practical
- add structured logs for retrieval, reranking, chat orchestration, and ingestion jobs
- include stage timings and terminal outcomes
- avoid leaking secrets or adding noisy logs by default
- keep the logging useful in local Docker development
- add tests for correlation ID propagation and structured event emission where practical
- update relevant documentation after code changes

Documentation tasks:
- add or update docs/OBSERVABILITY.md
- update docs/FAILURE_MODES.md if failure events or fallbacks are now observable
- update docs/TESTING.md with tracing/logging validation where relevant
- update docs/CONFIGURATION.md with observability variables
- update docs/ADVANCED_STEP_2_PLAN.md status

At the end:
- summarize logged event families
- summarize new config or middleware
- explain how to inspect logs locally
```

---

## Prompt 7 — Chunking lab

```text
Read README.md, AGENTS.md, all files in docs/, docs/ADVANCED_STEP_2_PLAN.md if it exists, and the attached spec files 05-evaluation-suite.md and 07-chunking-lab.md first.

Implement the chunking lab only.

Requirements:
- preserve the current chunking implementation as the baseline strategy
- introduce a strategy registry and explicit strategy metadata
- add at least one table-aware markdown strategy
- support reindexing by selected strategy
- integrate with the evaluation suite so strategies can be compared
- keep production defaults stable and predictable
- add tests for deterministic strategy output, metadata persistence, and table-aware behavior
- update relevant documentation after code changes

Documentation tasks:
- update docs/INGESTION_PIPELINE.md with chunking strategy support
- update docs/RETRIEVAL.md if chunk metadata affects retrieval behavior
- update docs/EVALUATION.md with chunking-comparison workflow
- update docs/CONFIGURATION.md with chunking strategy variables
- update docs/ADVANCED_STEP_2_PLAN.md status

At the end:
- summarize implemented strategies
- summarize reindex/evaluation workflow
- list any experimental areas kept behind flags
```

---

## Prompt 8 — Final documentation consolidation after Advanced Step 2

```text
Read README.md, AGENTS.md, all files in docs/, docs/ADVANCED_STEP_2_PLAN.md, and all Advanced Step 2 spec files first.

Do not implement new features in this step unless a tiny code change is strictly required to resolve a documentation mismatch.

Tasks:
- review the implementation against the full Advanced Step 2 scope
- update README.md and docs/ so they reflect the current implementation accurately
- make sure every newly added configuration variable is documented
- make sure every new response shape and response mode is documented
- make sure retrieval flow, reranking, guardrails, evaluation, observability, and chunking strategy support are described consistently
- mark anything intentionally not implemented yet as planned or experimental
- update docs/ADVANCED_STEP_2_PLAN.md so it becomes a completed status record
- optionally create docs/ADVANCED_STEP_2_GAP_ANALYSIS.md for anything still missing

Rules:
- prefer minimal, precise documentation updates over broad rewrites
- do not silently document features that do not exist
- explicitly mark assumptions and partial implementations

At the end:
- summarize documentation files changed
- list remaining gaps, if any
- state whether the docs now match the implementation
```

---

## Optional Prompt 9 — Prompt catalog sync for the next phase

```text
Read README.md, AGENTS.md, all files in docs/, docs/ADVANCED_STEP_2_PLAN.md, and the implemented Advanced Step 2 code first.

Task:
- create or update docs/PROMPTS_CATALOG.md
- document the main system prompts and policy prompts currently used in the codebase
- include prompts or prompt templates for:
  - grounded answer generation
  - insufficient_context handling
  - out_of_scope refusal
  - query rewriting if implemented later
  - evaluation usage if prompt-based checks exist
- separate implemented prompts from future/planned prompts

Rules:
- document only prompts that exist or are explicitly planned
- avoid adding speculative prompt text that is not represented in code or specs

At the end:
- summarize the catalog structure
- list implemented vs planned prompt templates
```
