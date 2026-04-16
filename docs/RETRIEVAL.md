# Retrieval

## Retrieval goals

The retrieval layer must:

- find relevant chunks for the user's question,
- respect strict workspace isolation,
- support explicit scope restrictions,
- return source-rich context for final answer generation,
- avoid mixing inactive or invalid document versions into normal answers.

## MVP retrieval model

### Search type
MVP uses semantic vector search with Qdrant.

### Planned future enhancements
Explicitly planned, but not part of MVP:

- hybrid search,
- reranking,
- query expansion.

## Retrieval flow

1. Validate user's workspace access.
2. Resolve active workspace.
3. Load optional explicit scope filters.
4. Generate embedding for user query.
5. Query Qdrant with mandatory filters.
6. Deduplicate and rank top-k chunks.
7. Pass results to prompt builder.

## Required filters

Mandatory filters:

- `workspace_id`
- `is_active = true`

Optional filters:

- `category`
- selected document IDs
- `language`

## Scope filtering

The system should support three main retrieval scopes:

### 1. Entire active workspace
Search all active documents inside the workspace.

### 2. Category-restricted scope
Examples:
- HR only,
- IT only,
- Legal only.

### 3. Selected-document scope
Useful when the user wants the answer from specific documents only.

## Guardrails

The retrieval layer must enforce:

- no cross-workspace retrieval,
- no inactive document versions in standard mode,
- no frontend-only security assumptions,
- no trust in raw user-provided workspace IDs without backend validation.

## Retrieval result packaging

Each retrieval result should include:

- chunk text,
- document title,
- section path,
- document version identifier,
- retrieval score,
- category,
- active status.

## Recommended top-k defaults

Suggested initial values:

- vector search candidate count: 5–8
- final prompt context chunks: 4–6

These should be environment-configurable.

## Threshold strategy

MVP can start with a simple threshold strategy:

- return top-k within workspace,
- optionally drop low-score outliers if score gap is obvious,
- if retrieval is weak, answer with uncertainty rather than forcing hallucinated output.

Recommended principle:
if the available context is weak or absent, the assistant should say it does not know.

## No-answer behavior

When retrieval finds no usable context:

- assistant should clearly state that the answer is not available in the current workspace documents,
- response should not invent facts,
- response may suggest narrowing or broadening scope if appropriate.

## Planned retrieval evolution

### Hybrid search
Future version may combine:

- semantic vector search,
- lexical keyword search,
- metadata filters.

### Reranking
Future version may:

- retrieve a broader candidate set,
- rerank with a dedicated reranker model,
- keep only strongest contexts for prompt assembly.

## Evaluation guidance

Retrieval quality should be measured with fixture-based questions covering:

- correct section hits,
- category scoping,
- multi-workspace isolation,
- version validity,
- follow-up questions supported by memory context.
