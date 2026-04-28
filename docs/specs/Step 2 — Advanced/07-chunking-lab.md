# Spec: Chunking Lab

## Goal
Create an experimentation framework for comparing chunking strategies against benchmark questions and measuring their impact on retrieval and answer quality.

## Baseline assumption
The MVP already has structure-aware markdown chunking. Advanced mode must make chunking strategy explicit, versioned, and comparable.

## Scope

### In scope
- multiple named chunking strategies
- chunking strategy metadata persistence
- reindexing by strategy
- evaluation-suite comparison support
- table-aware chunking strategy

### Out of scope
- automatic ML optimization of chunking
- production-time auto-selection per document type in v1

## Functional requirements

### FR-1 Strategy registry
The ingestion/indexing pipeline must support multiple named chunking strategies behind a stable interface.

Initial recommended strategies:
- `markdown_structure_v1` (baseline)
- `markdown_structure_v2_smaller_chunks`
- `markdown_structure_v3_larger_context`
- `markdown_table_aware_v1`
- `parent_child_experimental_v1` (optional)

### FR-2 Strategy metadata persistence
Persist, per chunk and/or index record:
- `chunking_strategy_name`
- `chunking_strategy_version`
- `chunk_size_config`
- `chunk_overlap_config`

### FR-3 Reindex support
A document version must be reindexable with a chosen chunking strategy for evaluation and comparison.

### FR-4 Evaluation integration
Chunking lab must integrate with the evaluation suite so benchmark results can be compared across strategies.

### FR-5 Table-aware strategy
At least one strategy must improve markdown table handling.
Recommended first behavior:
- preserve header row with every table sub-chunk
- avoid splitting row semantics arbitrarily
- keep surrounding heading context
- persist table context metadata if useful

## Suggested interface
- `chunk(document, config) -> list[Chunk]`

## Suggested experiment flow
1. select representative document fixture set
2. reindex with strategy A
3. run benchmark
4. reindex with strategy B
5. compare reports

## Comparison dimensions
- hit@k
- MRR
- citation usefulness
- answer signal coverage
- average chunk size
- number of chunks
- indexing latency
- storage impact

## Configuration
- `CHUNKING_DEFAULT_STRATEGY=markdown_structure_v1`
- `CHUNKING_EXPERIMENT_ENABLED=false`
- `CHUNKING_TABLE_HEADER_REPEAT=true`
- `CHUNKING_TABLE_MAX_ROWS_PER_CHUNK=20`

## Testing

### Unit
- strategy registry lookup
- deterministic output per strategy
- table-aware chunk preservation

### Integration
- reindex with chosen strategy
- metadata persisted correctly
- evaluation runner can compare strategies

## Definition of Done
- multiple chunking strategies exist behind stable interface
- at least one table-aware strategy is implemented
- reindex-and-compare workflow is possible
- chunking metadata is persisted and observable
