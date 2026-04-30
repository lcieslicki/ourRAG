# Retrieval

## Retrieval goals

The retrieval layer must:

- find relevant chunks for the user's question,
- respect strict workspace isolation,
- support explicit scope restrictions,
- return source-rich context for final answer generation,
- avoid mixing inactive or invalid document versions into normal answers.

## Retrieval model

### Search type
Default: semantic vector search with Qdrant.

Optional modes (configured via env):
- **hybrid** — combines semantic vector search + BM25 lexical search with configurable weights (`RETRIEVAL_MODE=hybrid`)
- **reranking** — a cross-encoder reranker applied after retrieval to improve ranking precision (`RERANKING_ENABLED=true`)
- **query rewriting** — one or more alternative queries generated before retrieval (`QUERY_REWRITE_MODE`)

### Query rewriting
Controlled by `QUERY_REWRITE_MODE`:

- `disabled` — original query is used as-is (default)
- `single_rewrite` — one alternative phrasing is generated
- `multi_query` — up to `QUERY_REWRITE_MAX_QUERIES` alternatives generated; retrieval runs per query and results are merged and deduplicated by `chunk_id`

Rewrites are generated using the local LLM. Contextualization (E2) may resolve pronouns or vague references before rewriting. On timeout or error, the system falls back to the original query.

## Retrieval flow

1. Validate user's workspace access.
2. Resolve active workspace.
3. Load optional explicit scope filters.
4. *(optional)* Contextualize query using conversation memory (E2).
5. *(optional)* Generate rewritten queries via `QueryRewriteService` (E1).
6. Embed query (or each rewritten query).
7. Query Qdrant with mandatory workspace and active-version filters.
8. *(multi-query)* Merge and deduplicate candidates across all queries.
9. *(optional)* Rerank candidates with cross-encoder.
10. Pass top-k chunks to prompt builder.

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

## Routing and mode selection

The backend router (`RequestRouter`) classifies each incoming chat turn before retrieval runs:

| Mode | Trigger | Behavior |
|------|---------|----------|
| `qa` | default | standard retrieval + generation |
| `summarization` | summary intent detected | routes to `SummarizationService` |
| `structured_extraction` | extraction intent detected | routes to `ExtractionService` |
| `admin_lookup` | admin query detected | metadata lookup without LLM |
| `refuse_out_of_scope` | out-of-scope detected | template refusal, no LLM call |

Routing decisions are advisory when confidence is below `ROUTING_MIN_CONFIDENCE` — system falls back to `qa`.

## Evaluation guidance

Retrieval quality should be measured with fixture-based questions covering:

- correct section hits,
- category scoping,
- multi-workspace isolation,
- version validity,
- follow-up questions supported by memory context.
