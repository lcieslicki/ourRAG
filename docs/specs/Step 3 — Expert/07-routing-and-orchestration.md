# Spec: Routing and Orchestration

## Goal
Introduce a request router that chooses the correct backend capability for each user request instead of sending every turn through the same Q&A path.

## Baseline assumption
The MVP chat flow always performs retrieval + prompt build + answer generation. Expert mode adds mode selection across multiple capabilities while preserving the existing Q&A path as the default.

## Scope

### In scope
- backend request router
- mode selection logic
- orchestrator for QA, summarization, extraction, and admin-like lookups
- structured response metadata for selected mode
- safe fallback to baseline QA path

### Out of scope
- autonomous multi-agent planning
- uncontrolled tool execution
- user-invisible speculative branching across many expensive paths in v1

## Functional requirements

### FR-1 Supported modes
Initial recommended modes:
- `qa`
- `summarization`
- `structured_extraction`
- `admin_lookup`
- `refuse_out_of_scope`

### FR-2 Routing inputs
Router may use:
- current user message
- query classifier outputs
- explicit user-selected mode if the UI later exposes one
- conversation context and memory metadata

### FR-3 Backend authority
Routing decisions must be made in the backend. The frontend may suggest a mode, but must not be authoritative.

### FR-4 Safe default
If routing confidence is weak or the mode is unsupported, the system must fall back to baseline `qa` safely.

### FR-5 Response envelope
Every response should include:
- `selected_mode`
- `router_reason` or `router_strategy`
- capability-specific payload
- source metadata where applicable

## Suggested interfaces
- `RequestRouter.route(request_context) -> RouteDecision`
- `CapabilityOrchestrator.execute(route_decision, request_context) -> ResponseEnvelope`

## Configuration
- `ROUTING_ENABLED=true`
- `ROUTING_DEFAULT_MODE=qa`
- `ROUTING_ALLOW_UI_MODE_HINT=true`
- `ROUTING_MIN_CONFIDENCE=0.7`

## Testing

### Unit
- route decision normalization
- weak-confidence fallback to QA
- unsupported mode handling

### Integration
- summary-intent query chooses summarization
- extraction-intent query chooses extraction
- low-confidence query falls back to QA
- out-of-scope query routes to refusal path safely

### E2E
- user asks for summary/checklist/extraction in one workspace and receives the correct mode response

## Definition of Done
- backend routing exists as a distinct layer
- multiple capabilities can be executed through one entrypoint
- fallback behavior is explicit, safe, and tested
