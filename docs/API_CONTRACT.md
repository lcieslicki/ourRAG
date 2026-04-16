# API Contract

## API design principles

- Backend is the source of truth.
- Frontend is a thin client.
- All operations are workspace-aware.
- Access must be validated server-side.
- Responses should include source metadata where relevant.

## Authentication
Authentication strategy is implementation-specific, but all protected endpoints require authenticated user context.

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
        "score": 0.92
      }
    ]
  },
  "usage": {
    "retrieval_latency_ms": 42,
    "llm_latency_ms": 810
  }
}
```

## Document endpoints

### POST /api/documents/upload
Upload a file version.

Example request:
multipart file upload plus metadata:
- workspace_id
- optional document_id
- title
- category
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

Suggested uniform shape:

```json
{
  "error": {
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
