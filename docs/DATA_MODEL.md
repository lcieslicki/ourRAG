# Data Model

## Data storage responsibilities

### PostgreSQL
Stores:

- users,
- workspaces,
- memberships,
- documents,
- document versions,
- ingestion job status,
- conversations,
- messages,
- conversation summaries,
- partial local admin audit data,
- indexing metadata.

### Qdrant
Stores:

- chunk vectors,
- chunk payload metadata for retrieval filtering and source attribution.

### Local filesystem
Stores:

- original uploaded files,
- derived artifacts if needed.

## Suggested relational entities

## users
Fields:

- `id`
- `email`
- `password_hash` or external auth reference
- `display_name`
- `status`
- `created_at`
- `updated_at`

## workspaces
Fields:

- `id`
- `name`
- `slug`
- `status`
- `default_language`
- `system_prompt_override` (nullable)
- `llm_model_override` (nullable)
- `embedding_model_override` (nullable)
- `settings_json`
- `created_at`
- `updated_at`

## workspace_users
Fields:

- `id`
- `workspace_id`
- `user_id`
- `role`
- `created_at`

Unique constraint:
- `(workspace_id, user_id)`

## documents
Logical business document.

Fields:

- `id`
- `workspace_id`
- `title`
- `slug`
- `category`
- `tags_json`
- `created_by_user_id`
- `status`
- `created_at`
- `updated_at`
- `deleted_at` (nullable)

## document_versions
Concrete uploaded version.

Fields:

- `id`
- `document_id`
- `version_number`
- `file_name`
- `file_extension`
- `mime_type`
- `storage_path`
- `checksum`
- `language`
- `is_active`
- `is_invalidated`
- `invalidated_reason` (nullable)
- `processing_status`
- `parsed_text_path` (nullable)
- `chunk_count`
- `embedding_model_name`
- `embedding_model_version`
- `chunking_strategy_version`
- `indexed_at` (nullable)
- `created_by_user_id`
- `created_at`
- `updated_at`

Recommended rule:
- only one active version per document.

## document_processing_jobs
Fields:

- `id`
- `document_version_id`
- `job_type`
- `status`
- `attempts`
- `error_message` (nullable)
- `started_at` (nullable)
- `finished_at` (nullable)
- `created_at`

## conversations
Fields:

- `id`
- `workspace_id`
- `user_id`
- `title` (nullable)
- `status`
- `selected_scope_json` (nullable)
- `created_at`
- `updated_at`
- `archived_at` (nullable)

## messages
Fields:

- `id`
- `conversation_id`
- `workspace_id`
- `user_id` (nullable for assistant)
- `role`
- `content_text`
- `response_metadata_json` (nullable)
- `created_at`

## conversation_summaries
Fields:

- `id`
- `conversation_id`
- `summary_text`
- `summary_version`
- `last_message_id`
- `created_at`
- `updated_at`

## audits
Fields:

- `id`
- `workspace_id` (nullable where applicable)
- `user_id` (nullable)
- `event_type`
- `entity_type`
- `entity_id`
- `payload_json`
- `created_at`

Current audit coverage is partial. It records selected local admin and document lifecycle events, not every bootstrap operation or denied action.

## Qdrant payload model

Each indexed chunk should include payload fields such as:

- `workspace_id`
- `document_id`
- `document_version_id`
- `chunk_id`
- `chunk_index`
- `title`
- `category`
- `tags`
- `section_path`
- `language`
- `is_active`
- `created_at`

## Qdrant collection strategy

### MVP recommendation
Use a single collection for all workspaces.

Reasons:

- simpler operations,
- simpler migrations,
- easier monitoring,
- enough for low-scale MVP.

Mandatory filter:
- `workspace_id`

Additional filters:
- `is_active = true`
- optional `category`
- optional selected `document_id` list
- optional `language`

## Filesystem layout recommendation

```text
/storage
  /workspaces
    /{workspace_id}
      /documents
        /{document_id}
          /versions
            /{document_version_id}
              /original
              /parsed
```

This layout makes cleanup and debugging easier.

## Versioning rules

- Each upload creates a new `document_version`.
- Active status is explicit.
- Invalidated versions remain stored for audit and rollback.
- Standard retrieval excludes invalidated versions.
- Admin can decide whether hard delete is allowed.

## Soft delete vs hard delete

Both modes should be supported.

### Soft delete
Recommended default for documents and versions.
Use when:
- audit trail matters,
- rollback matters,
- accidental deletion risk exists.

### Hard delete
Admin-controlled operation.
Requires:
- filesystem cleanup,
- Qdrant vector cleanup,
- relational cleanup or archival record.
