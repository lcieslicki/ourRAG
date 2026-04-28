# Spec: Evaluation Suite

## Goal
Provide a practical local evaluation framework for comparing retrieval and answer quality across baseline and advanced modes.

## Scope

### In scope
- benchmark dataset schema
- offline evaluation runner
- retrieval metrics
- answer-signal and citation checks
- guardrail mode accuracy checks
- machine-readable and human-readable reports

### Out of scope
- human annotation web app
- LLM-as-a-judge dependency on external APIs
- large-scale experiment orchestration

## Functional requirements

### FR-1 Benchmark dataset format
Support a local dataset format with one file per scenario or a single JSONL/JSON dataset.

Required fields per case:
- `case_id`
- `workspace_fixture`
- `question`
- `expected_source_documents`
- `expected_source_chunks` (optional)
- `expected_answer_signals`
- `expected_response_mode`

Optional fields:
- `filters`
- `notes`
- `tags`

### FR-2 Offline runner
Provide a CLI or scriptable runner that can execute benchmark cases against configurable retrieval/chat modes.

### FR-3 Required metrics
Compute at least:
- `hit@k`
- `mrr`
- `answer_signal_coverage`
- `citation_presence`
- `response_mode_accuracy`

Optional useful metrics:
- exact document match
- top-1 chunk hit
- average latency

### FR-4 Comparison mode
The runner must make it easy to compare:
- vector-only vs hybrid
- reranking off vs on
- different chunking strategies if available

### FR-5 Reports
Produce:
- machine-readable report (`json`)
- human-readable summary (`md` or console table)

## Suggested dataset example
```json
{
  "case_id": "training_financing_001",
  "workspace_fixture": "hr_training_docs",
  "question": "Kto finansuje szkolenia obowiązkowe?",
  "expected_source_documents": ["training_policy.md"],
  "expected_answer_signals": ["100%", "firma"],
  "expected_response_mode": "answer_from_context"
}
```

## Suggested runner options
- dataset path
- workspace fixture selector
- retrieval mode
- reranking enabled/disabled
- output directory
- optional max cases

## Fixture guidance
Include a small but representative seed dataset covering:
- exact title lookup
- acronym/procedure code lookup
- normal semantic question
- insufficient-context case
- out-of-scope case

## Configuration
- `EVAL_DEFAULT_TOP_K=10`
- `EVAL_OUTPUT_DIR=./artifacts/eval`
- `EVAL_INCLUDE_LATENCY=true`

## Testing

### Unit
- dataset schema validation
- metric computation
- report writer

### Integration
- local runner executes fixture dataset end-to-end
- report files are produced
- comparison mode works for baseline vs advanced toggles

## Definition of Done
- benchmark cases can be stored in repo
- offline runner works locally and in CI smoke mode
- metrics are sufficient to compare advanced features
- reports are easy to inspect and diff
