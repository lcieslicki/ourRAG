# Codex Prompt Set — Expert Step 3

Run these prompts in order. Keep each task limited to one feature area. Review the diff after each step.

## Prompt E0 — Documentation sync before Expert work

```text
Read README.md, AGENTS.md, all files in docs/, and all attached Expert Step 3 spec files first.

Before implementing any Expert feature:
- compare the current codebase with the current documentation
- identify mismatches that would block Expert work
- make only the smallest documentation updates needed to establish a clean baseline
- do not implement Expert features yet

At the end:
- summarize documentation/code mismatches found
- summarize documentation updates made
- list any assumptions that still remain open
```

## Prompt E1 — Query rewriting and multi-query retrieval

```text
Read README.md, AGENTS.md, docs/, and 01-query-rewriting-and-multi-query-retrieval.md first.

Implement query rewriting and multi-query retrieval only.

Requirements:
- preserve the current retrieval pipeline as the baseline path
- add a query rewrite abstraction and one local implementation
- support disabled, single_rewrite, and multi_query modes
- keep strict workspace_id, active-version, and existing scope filters enforced
- merge and deduplicate retrieved candidates across rewritten queries
- expose debug metadata only where appropriate
- add tests for recall improvement, safe fallback, and deterministic ordering

At the end:
- summarize pipeline changes
- summarize config added
- explain fallback behavior
```

## Prompt E2 — Conversation contextualization and advanced memory

```text
Read README.md, AGENTS.md, docs/, and 02-conversation-contextualization-and-advanced-memory.md first.

Implement advanced memory/contextualization only.

Requirements:
- treat the existing memory service as the baseline
- add a contextualization step for follow-up questions
- separate retrieval-facing memory from generation-facing memory
- keep prompts bounded and do not dump full history
- keep conversation and workspace isolation strict
- add tests for follow-up interpretation, bounded packaging, and no cross-workspace leakage

At the end:
- summarize memory packaging changes
- summarize config added
- explain any compatibility shortcuts taken
```

## Prompt E3 — Structured extraction

```text
Read README.md, AGENTS.md, docs/, and 03-structured-extraction.md first.

Implement structured extraction only.

Requirements:
- add extraction as a first-class backend capability
- support schema-driven extraction with validation
- return deterministic response envelopes and supporting sources
- keep extraction separate from baseline chat QA orchestration where practical
- add tests for schema validation, successful extraction, and invalid model output handling
- update docs and API contracts accordingly

At the end:
- summarize API surface added
- summarize predefined schemas added
- explain validation/failure behavior
```

## Prompt E4 — Summarization and briefing

```text
Read README.md, AGENTS.md, docs/, and 05-summarization-and-briefing.md first.

Implement summarization and briefing only.

Requirements:
- add summarization as a first-class backend capability
- support at least two output formats
- support document scope and section scope
- keep summaries source-backed
- implement a bounded long-document strategy where needed
- add tests for scope handling, output formats, and long-document orchestration
- update docs and API contracts accordingly

At the end:
- summarize supported scopes and formats
- summarize orchestration approach
- mention any constraints or shortcuts
```

## Prompt E5 — Classification pipeline

```text
Read README.md, AGENTS.md, docs/, and 04-classification-pipeline.md first.

Implement the classification pipeline only.

Requirements:
- add reusable document and query classifier abstractions
- implement at least one practical local-first strategy
- keep classifier outputs advisory by default unless explicitly configured otherwise
- integrate document classification with metadata enrichment where appropriate
- integrate query classification with routing preparation only as needed
- add tests for confidence thresholds, fallback behavior, and safe integration

At the end:
- summarize classifier interfaces
- summarize labels added
- explain where outputs are consumed
```

## Prompt E6 — Document parsing beyond Markdown

```text
Read README.md, AGENTS.md, docs/, and 06-document-parsing-beyond-markdown.md first.

Implement document parsing beyond Markdown only.

Requirements:
- preserve the existing Markdown parser as the baseline
- add at least PDF, DOCX, and TXT parser support end-to-end
- keep parser output normalized for existing chunking/indexing stages
- mark parse failures explicitly and do not let failed versions become ready
- add tests and representative fixtures for each supported file type
- update upload constraints, docs, and API contracts accordingly

At the end:
- summarize supported file types
- summarize parser modules added
- explain failure handling
```

## Prompt E7 — Routing and orchestration

```text
Read README.md, AGENTS.md, docs/, and 07-routing-and-orchestration.md first.

Implement routing and orchestration only.

Requirements:
- preserve the current QA path as the default baseline
- add a backend router for qa, summarization, structured_extraction, admin_lookup, and refusal paths
- keep backend authoritative for route decisions
- fall back safely to QA on weak-confidence or unsupported paths
- add structured response metadata for selected_mode and router strategy
- add tests for route selection, fallback behavior, and mode execution integration

At the end:
- summarize routing decisions supported
- summarize capability integration points
- explain fallback behavior
```

## Prompt E8 — Feedback loop

```text
Read README.md, AGENTS.md, docs/, and 08-feedback-loop.md first.

Implement the feedback loop only.

Requirements:
- add backend support for capturing structured feedback on assistant responses
- link feedback to relevant response/chat/retrieval artifacts
- add lightweight frontend feedback UI only if the current frontend architecture supports it cleanly
- keep feedback records workspace-safe and privacy-aware
- support update-or-replace behavior for repeated user feedback on the same response
- add tests for validation, persistence, linkage, and repeated feedback behavior

At the end:
- summarize schema and API added
- summarize any frontend changes
- explain idempotency/update behavior
```

## Prompt E9 — Final documentation consolidation for Expert step

```text
Read README.md, AGENTS.md, docs/, and all Expert Step 3 spec files first.

After the Expert features are implemented:
- review implementation against documentation
- update README.md and docs/ so they match the current architecture and capabilities
- add or refresh sections for:
  - query rewriting
  - advanced memory/contextualization
  - structured extraction
  - summarization
  - classification
  - non-Markdown parsing
  - routing/orchestration
  - feedback loop
- preserve existing documentation structure where possible
- do not invent features that were not implemented

At the end:
- summarize documentation changes
- identify any remaining gaps between docs and implementation
```
