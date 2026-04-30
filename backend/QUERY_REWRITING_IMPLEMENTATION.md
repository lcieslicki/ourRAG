# Query Rewriting and Multi-Query Retrieval Implementation (E1)

## Overview
This implementation adds query rewriting and multi-query retrieval capabilities to the ourRAG FastAPI backend. The feature enables LLM-powered query expansion and multi-perspective retrieval while maintaining safety through workspace scoping and gradual rollout.

## Architecture

### Core Components

#### 1. **QueryRewriteConfig** (`app/core/config/query_rewrite_config.py`)
- Pydantic BaseModel for configuration
- Fields:
  - `query_rewrite_mode`: "disabled" (default), "single_rewrite", or "multi_query"
  - `query_rewrite_max_queries`: Max rewrites to generate (default: 3)
  - `query_rewrite_include_summary`: Include summary in context (default: True)
  - `query_rewrite_include_recent_messages`: Include recent turns (default: True)
  - `query_rewrite_model_provider`: LLM provider (default: "ollama")
  - `query_rewrite_timeout_ms`: Timeout in ms (default: 3000)
- Validator ensures mode is in allowed set

#### 2. **Models** (`app/domain/query_rewriting/models.py`)

**QueryRewriteMode** (Enum)
- `DISABLED`: No rewriting
- `SINGLE_REWRITE`: One alternative phrasing
- `MULTI_QUERY`: Multiple alternative phrasings

**RewritePlan** (BaseModel)
- `original_query`: Original user query
- `contextualized_query`: Query after contextualization (optional)
- `rewritten_queries`: List of alternative phrasings
- `mode`: Current rewrite mode
- `was_contextualized`: Whether contextualization occurred
- Property `all_queries`: Returns deduplicated list of all queries to search with

**QueryRewriteRequest** (BaseModel)
- `query`: User query to rewrite
- `workspace_id`: Workspace scope
- `recent_turns`: Recent conversation history
- `summary`: Conversation summary (optional)
- `active_filters`: Filters to preserve

#### 3. **QueryRewriteService** (`app/domain/query_rewriting/service.py`)
- Async service for query rewriting
- Flow:
  1. Returns original if mode is disabled (safe default)
  2. Contextualizes query if contextualizer available
  3. Generates rewrites based on mode (1 or N)
  4. Returns RewritePlan with all queries
  5. Falls back gracefully on timeout/error
- Methods:
  - `async rewrite(request)`: Main entry point
  - `async _generate_rewrites()`: LLM-powered generation
  - `_build_rewrite_prompt()`: Prompt engineering for rewrites

#### 4. **MultiQueryRetrievalService** (`app/domain/query_rewriting/multi_query_retrieval.py`)
- Service for multi-query retrieval
- Flow:
  1. Takes RewritePlan with multiple query phrasings
  2. Retrieves independently for each query
  3. Merges results by chunk_id, keeping highest score
  4. Tracks which queries matched each chunk
  5. Returns deduplicated, sorted results
- Methods:
  - `async retrieve()`: Main entry point with merging logic
  - `_chunk_to_dict()`: Convert RetrievedChunk to dict
  - `_deduplicate()`: Keep highest score per chunk_id

#### 5. **RetrievalService Extension** (`app/domain/services/retrieval.py`)
- Added `retrieve_with_rewrite_plan()` method
- Accepts optional RewritePlan parameter
- If plan is None or disabled mode: uses standard retrieve()
- If multi-query: merges results from all rewrite queries
- Maintains all existing security and filtering
- No breaking changes to existing API

## Design Decisions

### Safety First
- Default mode is "disabled" — no behavior change unless explicitly configured
- All rewrites preserve workspace_id scope — never cross workspace boundaries
- Existing security filters are preserved and passed to all retrieval calls
- Timeout/error fallback ensures graceful degradation

### Workspace Isolation
- QueryRewriteRequest includes workspace_id
- All retrieval calls in multi-query flow use same workspace_id
- RetrievalService validates workspace membership as before

### Timeout Handling
- Single timeout per rewrite operation (3000ms default)
- Contextualization timeout: uses rewrite timeout
- Rewrite generation timeout: uses rewrite timeout
- On timeout: returns original query only, continues safely

### Contextualization Integration
- Integrates with existing ConversationContextualizer
- Reuses advanced memory infrastructure (E2 feature)
- Optional: works even if contextualizer is None
- Contextualizer timeouts don't block rewrite generation

### Deduplication
- Merges by chunk_id, keeping highest similarity score
- Preserves original chunk order for scoring
- Sorts final results by score descending
- Tracks which queries matched each chunk for debugging

## Testing

### Unit Tests (`tests/unit/test_query_rewriting.py`)
- TestQueryRewriteModels: Model behavior tests
  - `all_queries` deduplication
  - Contextualized query ordering
- TestQueryRewriteService: Service behavior
  - Disabled mode returns original only
  - Single_rewrite generates one alternative
  - Multi_query respects max_queries limit
  - Timeout fallback to original
  - Contextualization integration
  - Error handling

### Integration Tests (`tests/integration/test_multi_query_retrieval.py`)
- Disabled mode preserves baseline behavior
- Multi-query deduplicates by chunk_id correctly
- Workspace scope is maintained across queries
- Timeout/error handling doesn't break retrieval

## File Structure

```
app/
├── core/
│   └── config/
│       └── query_rewrite_config.py          (NEW)
└── domain/
    └── query_rewriting/                     (NEW PACKAGE)
        ├── __init__.py
        ├── models.py
        ├── service.py
        └── multi_query_retrieval.py
        
services/
└── retrieval.py                             (MODIFIED: added retrieve_with_rewrite_plan)

tests/
├── unit/
│   └── test_query_rewriting.py              (NEW)
└── integration/
    └── test_multi_query_retrieval.py        (NEW)
```

## Configuration

To enable query rewriting, set environment variables:

```bash
# Enable single rewrite mode
QUERY_REWRITE_MODE=single_rewrite

# Or enable multi-query mode (default: 3 queries)
QUERY_REWRITE_MODE=multi_query
QUERY_REWRITE_MAX_QUERIES=5

# Optionally tune timeouts
QUERY_REWRITE_TIMEOUT_MS=5000
```

## Usage Examples

### 1. Query Rewriting Service (Standalone)
```python
from app.domain.query_rewriting.service import QueryRewriteService
from app.domain.query_rewriting.models import QueryRewriteRequest

service = QueryRewriteService(llm=llm_gateway, contextualizer=None, settings=config)

request = QueryRewriteRequest(
    query="vacation policy",
    workspace_id="workspace-1",
    recent_turns=[...],
    summary="...",
)

plan = await service.rewrite(request)
print(plan.all_queries)  # [original, rewrite1, rewrite2, ...]
```

### 2. Multi-Query Retrieval (with RetrievalService)
```python
from app.domain.query_rewriting.models import RewritePlan

# Create a rewrite plan
plan = RewritePlan(
    original_query="vacation policy",
    rewritten_queries=["time off rules", "leave policy"],
    mode=QueryRewriteMode.MULTI_QUERY,
)

# Use extended retrieval API
response = retrieval_service.retrieve_with_rewrite_plan(
    user_id="user-1",
    workspace_id="workspace-1",
    query="vacation policy",
    rewrite_plan=plan,
)

# Results merged by chunk_id, sorted by score
print(len(response.chunks))  # Deduplicated chunks
```

### 3. MultiQueryRetrievalService (Orchestrated)
```python
from app.domain.query_rewriting.multi_query_retrieval import MultiQueryRetrievalService

service = MultiQueryRetrievalService(retrieval_service, settings)

result = await service.retrieve(
    rewrite_plan=plan,
    user_id="user-1",
    workspace_id="workspace-1",
)

# Returns dict with:
# - chunks: list of merged chunks with which_query_matched tracking
# - debug: rewrite plan metadata
```

## Backward Compatibility

- Existing `RetrievalService.retrieve()` method is unchanged
- New `retrieve_with_rewrite_plan()` is additive, optional
- Default config mode is "disabled" — no changes unless configured
- All existing tests continue to pass

## Future Enhancements

1. **Reranking Integration**: Apply reranking after merging multi-query results
2. **Query Validity Checking**: Validate rewrites don't diverge from original intent
3. **Telemetry**: Track rewrite effectiveness, timeout rates
4. **User Feedback**: Collect explicit feedback on rewritten queries
5. **Hybrid Mode**: Combine hybrid retrieval with multi-query expansion
6. **Caching**: Cache rewrite plans for identical queries within session
