# Security

## Core security objective

Prevent data leakage across workspaces while supporting a shared application instance.

This document describes the current local-only security posture. The app is not designed for public exposure or production authentication.

## Security principles

- Workspace isolation is a hard invariant.
- Backend is authoritative for access control.
- Frontend inputs are advisory, never authoritative.
- Retrieval filters are mandatory security controls, not optional UX settings.
- Active document status must be enforced server-side.

## Mandatory isolation rules

- Protected user-facing requests execute under the local `X-User-Id` development auth shim.
- Every chat request must validate user membership in the target workspace.
- Every retrieval query must filter by `workspace_id`.
- Every document operation must be workspace-scoped.
- Every conversation must be bound to one workspace.
- Every message must belong to that same workspace.

## Retrieval security

Qdrant search must always include:

- `workspace_id`
- `is_active = true` in standard mode

The backend must never allow raw unrestricted vector search for normal user requests.

## Filesystem security

File paths should be workspace-scoped and version-scoped.
Raw filesystem paths should never be exposed directly to clients.

## UI rendering security

Frontend must:

- avoid unsafe HTML rendering,
- sanitize markdown rendering,
- avoid exposing internal identifiers unnecessarily.

## API trust model

Do not trust:
- user-supplied workspace IDs without validation,
- user-supplied document IDs without workspace ownership checks,
- frontend assumptions about allowed scope.

## Admin actions

The current admin surface is intentionally relaxed for local bootstrap, testing, and manual data management.

Some admin/bootstrap endpoints do not require authenticated user context. This is acceptable for the local-only MVP but would be unacceptable for a public or shared deployment.

Document version lifecycle operations and workspace settings updates have stronger role checks and audit records than bootstrap CRUD flows.

Examples:
- upload,
- activation,
- invalidation,
- reindex,
- hard delete.

## Audit logging

Current audit coverage includes:
- version activation/invalidation,
- reindex requests through document services,
- workspace settings updates,
- selected destructive bootstrap actions.

Not currently audited:
- local login/session selection,
- workspace switching,
- every denied admin action,
- every bootstrap CRUD action.

## Prompt injection awareness

Document content may contain malicious or misleading instructions.
The prompt builder should explicitly frame retrieved content as source material, not trusted executable instructions.

## Future security areas

Planned later hardening may include:
- real authentication,
- strict admin authorization,
- complete audit coverage,
- rate limiting,
- CSP hardening,
- per-workspace retention policies,
- SSO integration,
- malware scanning for uploaded files,
- secure object storage instead of local filesystem.
