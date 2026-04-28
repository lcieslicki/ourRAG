# ourRAG — Expert Step 3 Specs Pack

This package contains implementation specs for all features planned in **Step 3 — Expert**.

## Source alignment used for this pack

These specs were aligned against:
- the uploaded Codex execution log showing phases `0` through `12` completed for the MVP
- the previously prepared Advanced Step 2 specs pack
- the current project direction for local-first RAG focused on internal company documentation

## Important alignment note

The MVP already includes:
- workspace-aware chat
- retrieval
- prompt building
- Ollama/Bielik generation
- conversation/message APIs
- basic memory service
- admin APIs
- frontend integration
- E2E coverage

Because of that, the Expert specs below focus on **extending** the current system rather than replacing MVP behavior.

## Included files

- `01-query-rewriting-and-multi-query-retrieval.md`
- `02-conversation-contextualization-and-advanced-memory.md`
- `03-structured-extraction.md`
- `04-classification-pipeline.md`
- `05-summarization-and-briefing.md`
- `06-document-parsing-beyond-markdown.md`
- `07-routing-and-orchestration.md`
- `08-feedback-loop.md`
- `09-codex-implementation-prompts.md`

## Recommended implementation order

1. Query rewriting and multi-query retrieval
2. Conversation contextualization and advanced memory
3. Structured extraction
4. Summarization and briefing
5. Classification pipeline
6. Document parsing beyond Markdown
7. Routing and orchestration
8. Feedback loop
