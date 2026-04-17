from itertools import count

from sqlalchemy.orm import Session

from app.domain.models import (
    Conversation,
    Document,
    DocumentProcessingJob,
    DocumentVersion,
    User,
    Workspace,
    WorkspaceMembership,
)

_counter = count(1)


def unique_slug(prefix: str) -> str:
    return f"{prefix}-{next(_counter)}"


def create_user(session: Session, *, email_prefix: str = "user") -> User:
    user = User(
        email=f"{unique_slug(email_prefix)}@example.test",
        display_name="Test User",
        status="active",
    )
    session.add(user)
    session.flush()
    return user


def create_workspace(session: Session, *, slug_prefix: str = "workspace") -> Workspace:
    workspace = Workspace(
        name="Test Workspace",
        slug=unique_slug(slug_prefix),
        status="active",
        default_language="pl",
        settings_json={},
    )
    session.add(workspace)
    session.flush()
    return workspace


def create_membership(session: Session, *, user: User, workspace: Workspace, role: str = "member") -> WorkspaceMembership:
    membership = WorkspaceMembership(
        user_id=user.id,
        workspace_id=workspace.id,
        role=role,
    )
    session.add(membership)
    session.flush()
    return membership


def create_document(session: Session, *, workspace: Workspace, created_by: User, slug_prefix: str = "document") -> Document:
    document = Document(
        workspace_id=workspace.id,
        title="Test Document",
        slug=unique_slug(slug_prefix),
        category="HR",
        tags_json=[],
        created_by_user_id=created_by.id,
        status="active",
    )
    session.add(document)
    session.flush()
    return document


def create_document_version(
    session: Session,
    *,
    document: Document,
    created_by: User,
    version_number: int,
    is_active: bool = False,
) -> DocumentVersion:
    version = DocumentVersion(
        document_id=document.id,
        version_number=version_number,
        file_name=f"document-v{version_number}.md",
        file_extension=".md",
        mime_type="text/markdown",
        storage_path=f"/data/storage/{document.id}/v{version_number}/original/document.md",
        checksum=unique_slug("checksum"),
        language="pl",
        is_active=is_active,
        is_invalidated=False,
        processing_status="ready",
        chunk_count=0,
        created_by_user_id=created_by.id,
    )
    session.add(version)
    session.flush()
    return version


def create_processing_job(
    session: Session,
    *,
    document_version: DocumentVersion,
    job_type: str = "parse_document",
    status: str = "queued",
    attempts: int = 0,
) -> DocumentProcessingJob:
    job = DocumentProcessingJob(
        document_version_id=document_version.id,
        job_type=job_type,
        status=status,
        attempts=attempts,
    )
    session.add(job)
    session.flush()
    return job


def create_conversation(session: Session, *, workspace: Workspace, user: User) -> Conversation:
    conversation = Conversation(
        workspace_id=workspace.id,
        user_id=user.id,
        title="Test Conversation",
        status="active",
    )
    session.add(conversation)
    session.flush()
    return conversation
