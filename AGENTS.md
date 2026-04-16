# AGENTS.md

## Project rules

- Read the documentation in `README.md` and all files in `docs/` before making implementation decisions.
- Treat the documentation as the source of truth.
- If code and docs conflict, report the conflict and follow the docs unless the user explicitly says otherwise.

## Architecture rules

- Backend: Python, freamwork FastAPI
- Frontend: React.
- Chat UI: assistant-ui.
- PostgreSQL is the source of truth for relational data.
- Qdrant is the vector store.
- Ollama is the local model runtime.
- Generation model: Bielik.
- Workspace is the primary tenant isolation boundary.
- A conversation belongs to exactly one workspace.
- Retrieval must always be scoped to workspace_id.
- Standard retrieval must use active document versions only.

## Implementation rules

- Keep the frontend thin.
- Do not put retrieval or authorization logic in the frontend.
- Prefer small, reviewable commits.
- Prefer explicit types and clear boundaries between modules.
- Use dependency injection where useful.
- Design components for testability.
- All runtime configuration must come from environment variables.
- Support `.env` and `.env.<environment>` patterns.
- Do not hardcode secrets, hosts, ports, model names, or collection names.

## Testing rules

- Add unit tests for domain logic.
- Add integration tests for storage, Qdrant, Ollama gateway, and workers.
- Add end-to-end tests for the full ingestion and chat flow.
- Add tenant isolation tests for every sensitive area.
- Do not mark implementation complete unless tests pass or limitations are clearly reported.

## Delivery rules

- Before coding, produce a short implementation plan.
- Implement in phases.
- After each phase, summarize:
  - files created/changed
  - what is complete
  - what remains
  - risks or open questions