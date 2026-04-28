# Spec: Conversation Contextualization and Advanced Memory

## Goal
Extend the MVP memory service so follow-up questions can be interpreted more reliably, while keeping prompt size bounded and workspace-safe.

## Baseline assumption
The MVP already has:
- recent-message window selection
- rolling conversation summary persistence
- prompt memory packaging

This feature enhances that baseline with contextualization and memory-quality controls.

## Scope

### In scope
- follow-up question contextualization
- memory packaging policy improvements
- explicit memory roles
- memory freshness and truncation rules
- retrieval-facing and generation-facing memory separation

### Out of scope
- long-term cross-conversation memory
- user profile memory
- cross-workspace memory reuse
- autonomous note-taking outside active conversations

## Functional requirements

### FR-1 Contextualization step
Before retrieval, the system may transform the current user message into a standalone, context-resolved question using:
- recent messages
- conversation summary
- explicit active filters

### FR-2 Memory package separation
The backend should distinguish:
- `retrieval_memory`: context needed to interpret the search intent
- `generation_memory`: context needed to shape the answer naturally

### FR-3 Freshness policy
Memory selection must prefer:
1. the current user message
2. the most recent directly relevant turns
3. the rolling summary
4. older messages only through summarized form

### FR-4 Memory bounds
The system must continue to avoid dumping entire conversation history into prompts. Memory packaging should remain bounded by configurable limits.

### FR-5 Explicit metadata
Store and expose, where useful for debugging:
- whether the current turn was contextualized
- which memory artifacts were used
- summary version or timestamp
- selected recent message count

### FR-6 Safety
Memory must remain scoped to one conversation and one workspace. Contextualization must not silently import information from other conversations or external sources.

## Suggested interfaces
- `ConversationContextualizer.contextualize(turn, memory_package) -> ContextualizedTurn`
- `MemoryPackagingService.build_for_retrieval(conversation) -> RetrievalMemoryPackage`
- `MemoryPackagingService.build_for_generation(conversation) -> GenerationMemoryPackage`

## Configuration
- `MEMORY_CONTEXTUALIZATION_ENABLED=true`
- `MEMORY_RETRIEVAL_RECENT_MESSAGE_LIMIT=4`
- `MEMORY_GENERATION_RECENT_MESSAGE_LIMIT=6`
- `MEMORY_SUMMARY_MAX_CHARS=2000`
- `MEMORY_CONTEXTUALIZATION_TIMEOUT_MS=2500`

## Testing

### Unit
- memory selection ordering
- bounded packaging behavior
- contextualization output validation

### Integration
- follow-up question becomes standalone correctly
- no cross-workspace memory leakage
- empty/weak summary falls back to recent turns safely

### E2E
- multi-turn conversation with pronouns still retrieves correct procedure details

## Definition of Done
- follow-up interpretation is improved without unbounded prompt growth
- retrieval-facing memory and generation-facing memory are separated
- contextualization decisions are observable and tested
