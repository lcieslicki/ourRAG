# Domain Model

## Core domain concepts

### Workspace
A workspace is the primary knowledge and access boundary.

A workspace may represent:

- a company,
- a department,
- a subsidiary,
- another isolated internal knowledge scope.

### User
A human actor authenticated into the system.

A user may belong to multiple workspaces.

### Membership
Represents a user's access to a workspace and the assigned role.

### Document
A logical document entity.

A document is stable across versions.

### DocumentVersion
A concrete uploaded version of a document.

A document can have many versions, but standard retrieval should use active versions only.

### Chunk
A retrievable unit of text extracted from a document version.

### Conversation
A chat thread between a user and the system.

A conversation belongs to exactly one user and exactly one workspace.

### Message
A user or assistant message inside a conversation.

### ConversationSummary
A rolling summary used to compress older conversation history.

### ScopeFilter
A structured retrieval constraint applied inside the active workspace.

Examples:

- all active documents,
- a specific category such as HR,
- selected documents only.

## Domain invariants

The following invariants are mandatory:

- A conversation belongs to exactly one workspace.
- A document belongs to exactly one workspace.
- A document version belongs to exactly one document.
- A chunk belongs to exactly one document version.
- Retrieval must always be scoped to the active workspace.
- A user must not access a workspace without membership.
- Standard answers must use active document versions only.
- Memory must never mix content from different workspaces.
- Frontend-provided workspace identifiers are never trusted blindly.
- The backend is responsible for enforcing access scope.

## Domain relationships

```text
User
  -> has many Memberships
  -> has many Conversations

Workspace
  -> has many Memberships
  -> has many Documents
  -> has many Conversations

Document
  -> belongs to one Workspace
  -> has many DocumentVersions

DocumentVersion
  -> belongs to one Document
  -> has many Chunks

Conversation
  -> belongs to one User
  -> belongs to one Workspace
  -> has many Messages
  -> has one current ConversationSummary
```

## Roles

Suggested initial roles:

- `owner`
- `admin`
- `member`
- `viewer`

### Owner
Can manage the workspace fully.

### Admin
Can manage documents, versions, indexing, and workspace content.

### Member
Can chat with the system and access allowed documents.

### Viewer
Optional low-permission role for limited read-only use cases.

## Lifecycle overview

### Document lifecycle
1. Document created.
2. Document version uploaded.
3. Version processed asynchronously.
4. Version becomes active or remains pending.
5. Old version may be invalidated or archived.

### Conversation lifecycle
1. User creates or opens conversation.
2. User sends messages in one workspace.
3. Assistant responds using retrieval and memory.
4. Conversation summary is periodically refreshed.

## Future-friendly modeling choice

Use `workspace` as the bounded context name instead of `company`.

This keeps the product flexible without redesign when customers need:

- departments instead of companies,
- subsidiaries,
- regional business units,
- client-specific partitions.
