# ourRAG — Advanced Step 2 Specs Pack

This package contains implementation specs for all features planned in **Step 2 — Advanced**.

## Source alignment used for this pack

These specs were aligned against:
- the uploaded Codex execution log showing phases `0` through `12` completed for the MVP
- the uploaded docs index showing the current documentation set and filenames

## Important limitation

The uploaded `docs` artifact available in this conversation is an HTML directory index, not the full text of every documentation file. Because of that, the specs below are synchronized primarily with the implemented MVP surface visible from the Codex prompt log and with the documented file structure visible in the docs index.

## Included files

- `01-citations-and-source-attribution.md`
- `02-hybrid-retrieval.md`
- `03-reranking.md`
- `04-guardrails-and-answer-policy.md`
- `05-evaluation-suite.md`
- `06-observability-and-tracing.md`
- `07-chunking-lab.md`
- `08-codex-implementation-prompts.md`

## Recommended implementation order

1. Citations hardening
2. Hybrid retrieval
3. Reranking
4. Guardrails and answer policy
5. Evaluation suite
6. Observability and tracing
7. Chunking lab
