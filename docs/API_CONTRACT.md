# API Contract

## API design principles

- Backend is the source of truth.
- Frontend is a thin client.
- All operations are workspace-aware.
- Access must be validated server-side.
- Responses should include source metadata where relevant.

## Authentication
The current local MVP uses a lightweight development auth shim:

- protected API calls pass `X-User-Id`,
- the backend resolves that value as the current user,
- missing `X-User-Id` returns `401`.

This is not production authentication. It is sufficient for the local-only app and deterministic testing.

## Suggested endpoint groups

- auth
- workspaces
- conversations
- chat
- documents
- admin

## Workspace endpoints

### GET /api/workspaces
Returns list of workspaces available to current user.

Example response:

```json
[
  {
    "id": "ws_1",
    "name": "Acme HR",
    "role": "member"
  }
]
```

## Conversation endpoints

### GET /api/conversations?workspace_id={id}
Returns conversations for a workspace accessible to current user.

### POST /api/conversations
Create a conversation.

Example request:

```json
{
  "workspace_id": "ws_1",
  "title": "Vacation policy questions"
}
```

### GET /api/conversations/{conversation_id}
Returns conversation details, messages, and active scope metadata.

## Chat endpoint

### POST /api/chat
Primary endpoint for sending a message.

Example request:

```json
{
  "workspace_id": "ws_1",
  "conversation_id": "conv_1",
  "message": "How do I request vacation leave?",
  "scope": {
    "mode": "category",
    "category": "HR"
  }
}
```

### Chat response shape

```json
{
  "conversation_id": "conv_1",
  "assistant_message": {
    "id": "msg_2",
    "role": "assistant",
    "content": "You should submit vacation leave through the HR system.",
    "sources": [
      {
        "document_id": "doc_1",
        "document_title": "Employee Handbook",
        "document_version_id": "ver_2",
        "section_path": "HR > Vacation Leave",
        "snippet": "Vacation leave requests must be submitted in the HR system.",
        "score": 0.92,
        "category": "HR",
        "chunk_id": "ver_2:0"
      }
    ]
  },
  "usage": {}
}
```

`usage` is currently reserved for future timing and token metrics.

### GET /api/chat/ws/{conversation_id}
WebSocket stream for local chat processing events.

Query parameters:
- `user_id`

Events are intended for UI diagnostics. Sensitive text fields are redacted before being sent to the frontend.

## Document endpoints

### POST /api/documents/upload
Upload a file version.

Example request:
multipart file upload plus metadata:
- workspace_id
- optional document_id
- title
- category (accepted by the API, but the current implementation derives category from the filename prefix, for example `hr_policy.md` -> `HR`)
- tags

### GET /api/documents?workspace_id={id}
List documents.

### GET /api/documents/{document_id}
Document detail including versions.

### POST /api/documents/{document_id}/versions/{version_id}/activate
Activate a document version.

### POST /api/documents/{document_id}/versions/{version_id}/invalidate
Invalidate a document version.

### POST /api/documents/{document_id}/versions/{version_id}/reindex
Trigger reindex for a document version.

## Admin endpoints

The current admin surface is designed for local operation and bootstrap workflows. Some `/api/admin/*` endpoints are intentionally relaxed and may not require `X-User-Id`.

Admin document upload and folder indexing can trigger background processing inside the backend process. There is no separate production-grade admin authorization layer yet.

### Bootstrap and local admin endpoints

Current local endpoints include:

- `GET /api/admin/data-info`
- `GET /api/admin/users`
- `POST /api/admin/users`
- `GET /api/admin/users/{user_id}`
- `DELETE /api/admin/users/{user_id}`
- `GET /api/admin/workspaces`
- `POST /api/admin/workspaces`
- `GET /api/admin/workspaces/{workspace_id}`
- `DELETE /api/admin/workspaces/{workspace_id}`
- `PUT /api/admin/workspaces/{workspace_id}/data-folder`
- `GET /api/admin/workspaces/{workspace_id}/members`
- `POST /api/admin/workspaces/{workspace_id}/members`
- `GET /api/admin/workspaces/{workspace_id}/documents`
- `POST /api/admin/workspaces/{workspace_id}/documents/upload`
- `POST /api/admin/workspaces/{workspace_id}/documents/index-folder`
- `GET /api/admin/workspaces/{workspace_id}/documents/{document_id}/index-diagnostics`
- `DELETE /api/admin/workspaces/{workspace_id}/documents/{document_id}`
- `DELETE /api/admin/workspaces/{workspace_id}/documents`
- `POST /api/admin/workspaces/{workspace_id}/documents/reindex-all`
- `POST /api/admin/workspaces/{workspace_id}/processing-jobs/{job_id}/retry`

### GET /api/admin/workspaces/{workspace_id}/processing-jobs
List ingestion jobs.

### GET /api/admin/workspaces/{workspace_id}/settings
Read workspace settings.

### PUT /api/admin/workspaces/{workspace_id}/settings
Update workspace settings such as:
- prompt overrides,
- model overrides,
- retrieval defaults.

## Error format

Current FastAPI error shape:

```json
{
  "detail": {
    "code": "workspace_access_denied",
    "message": "You do not have access to this workspace."
  }
}
```

## Recommended error codes

- `workspace_access_denied`
- `conversation_not_found`
- `document_not_found`
- `document_version_not_ready`
- `invalid_scope_filter`
- `unsupported_file_type`
- `processing_failed`
- `llm_timeout`
- `retrieval_no_context`

## Streaming
Streaming is a future-friendly option but not required for MVP.

The initial MVP may use request/response mode only.
