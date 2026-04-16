from dataclasses import dataclass
from pathlib import Path
import re

from fastapi import UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.domain.errors import (
    DocumentAccessDenied,
    DocumentVersionInvalidated,
    DocumentVersionNotFound,
    DocumentVersionNotReady,
    UnsupportedFileType,
)
from app.domain.models import Audit, Document, DocumentVersion
from app.domain.models.common import new_id
from app.domain.services.access import WorkspaceAccessService
from app.infrastructure.storage.base import StoredFile, Storage

SUPPORTED_MARKDOWN_EXTENSIONS = {".md", ".markdown"}
MARKDOWN_MIME_TYPES = {"text/markdown", "text/x-markdown", "text/plain", "application/octet-stream"}


@dataclass(frozen=True)
class DocumentUploadResult:
    document: Document
    version: DocumentVersion
    stored_file: StoredFile


class DocumentService:
    def __init__(self, session: Session, storage: Storage) -> None:
        self.session = session
        self.storage = storage
        self.access = WorkspaceAccessService(session)

    def upload_markdown_version(
        self,
        *,
        user_id: str,
        workspace_id: str,
        file: UploadFile,
        title: str,
        category: str,
        document_id: str | None = None,
        tags: str | None = None,
    ) -> DocumentUploadResult:
        self.access.ensure_workspace_role(
            user_id=user_id,
            workspace_id=workspace_id,
            allowed_roles={"owner", "admin"},
        )
        self._validate_markdown_file(file)

        document = self._resolve_document(
            user_id=user_id,
            workspace_id=workspace_id,
            title=title,
            category=category,
            document_id=document_id,
            tags=tags,
        )
        version_number = self._next_version_number(document.id)
        version_id = new_id()
        file_name = self._safe_file_name(file.filename or "document.md")
        storage_path = self.storage.original_file_path(
            workspace_id=workspace_id,
            document_id=document.id,
            version_id=version_id,
            file_name=file_name,
        )
        stored_file = self.storage.save_upload(file=file, relative_path=storage_path)

        version = DocumentVersion(
            id=version_id,
            document_id=document.id,
            version_number=version_number,
            file_name=file_name,
            file_extension=Path(file_name).suffix.lower(),
            mime_type=file.content_type or "text/markdown",
            storage_path=stored_file.relative_path,
            checksum=stored_file.checksum,
            language="pl",
            is_active=False,
            is_invalidated=False,
            processing_status="pending",
            chunk_count=0,
            created_by_user_id=user_id,
        )
        self.session.add(version)
        self.session.flush()

        return DocumentUploadResult(document=document, version=version, stored_file=stored_file)

    def activate_version(self, *, user_id: str, document_id: str, version_id: str) -> DocumentVersion:
        document, version = self._resolve_document_version_for_admin_action(
            user_id=user_id,
            document_id=document_id,
            version_id=version_id,
        )

        if version.is_invalidated:
            raise DocumentVersionInvalidated("Invalidated document versions cannot be activated.")

        if version.processing_status != "ready":
            raise DocumentVersionNotReady("Only ready document versions can be activated.")

        self.session.execute(
            update(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .values(is_active=False)
        )
        version.is_active = True
        version.is_invalidated = False
        version.invalidated_reason = None
        self._record_audit(
            workspace_id=document.workspace_id,
            user_id=user_id,
            event_type="document_version_activated",
            entity_id=version.id,
            payload={
                "document_id": document.id,
                "version_number": version.version_number,
            },
        )
        self.session.flush()
        return version

    def invalidate_version(
        self,
        *,
        user_id: str,
        document_id: str,
        version_id: str,
        reason: str | None = None,
    ) -> DocumentVersion:
        document, version = self._resolve_document_version_for_admin_action(
            user_id=user_id,
            document_id=document_id,
            version_id=version_id,
        )
        version.is_active = False
        version.is_invalidated = True
        version.invalidated_reason = reason.strip() if reason else None
        self._record_audit(
            workspace_id=document.workspace_id,
            user_id=user_id,
            event_type="document_version_invalidated",
            entity_id=version.id,
            payload={
                "document_id": document.id,
                "version_number": version.version_number,
                "reason": version.invalidated_reason,
            },
        )
        self.session.flush()
        return version

    def _resolve_document_version_for_admin_action(
        self,
        *,
        user_id: str,
        document_id: str,
        version_id: str,
    ) -> tuple[Document, DocumentVersion]:
        document = self.session.get(Document, document_id)

        if document is None:
            raise DocumentAccessDenied("Document not found.")

        self.access.ensure_workspace_role(
            user_id=user_id,
            workspace_id=document.workspace_id,
            allowed_roles={"owner", "admin"},
        )
        version = self.session.get(DocumentVersion, version_id)

        if version is None or version.document_id != document.id:
            raise DocumentVersionNotFound("Document version not found.")

        return document, version

    def _record_audit(
        self,
        *,
        workspace_id: str,
        user_id: str,
        event_type: str,
        entity_id: str,
        payload: dict,
    ) -> None:
        self.session.add(
            Audit(
                workspace_id=workspace_id,
                user_id=user_id,
                event_type=event_type,
                entity_type="document_version",
                entity_id=entity_id,
                payload_json=payload,
            )
        )

    def _resolve_document(
        self,
        *,
        user_id: str,
        workspace_id: str,
        title: str,
        category: str,
        document_id: str | None,
        tags: str | None,
    ) -> Document:
        if document_id:
            return self.access.ensure_document_access(
                user_id=user_id,
                workspace_id=workspace_id,
                document_id=document_id,
            )

        document = Document(
            workspace_id=workspace_id,
            title=title.strip(),
            slug=self._unique_document_slug(workspace_id, title),
            category=category.strip(),
            tags_json=self._parse_tags(tags),
            created_by_user_id=user_id,
            status="active",
        )
        self.session.add(document)
        self.session.flush()
        return document

    def _next_version_number(self, document_id: str) -> int:
        current = self.session.scalar(
            select(func.max(DocumentVersion.version_number)).where(DocumentVersion.document_id == document_id)
        )
        return (current or 0) + 1

    def _unique_document_slug(self, workspace_id: str, title: str) -> str:
        base = self._slugify(title)
        slug = base
        suffix = 2

        while self.session.scalar(
            select(Document.id).where(Document.workspace_id == workspace_id, Document.slug == slug)
        ):
            slug = f"{base}-{suffix}"
            suffix += 1

        return slug

    @staticmethod
    def _parse_tags(tags: str | None) -> list[str]:
        if not tags:
            return []

        return [tag.strip() for tag in tags.split(",") if tag.strip()]

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "document"

    @staticmethod
    def _safe_file_name(file_name: str) -> str:
        name = Path(file_name).name
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
        return safe_name or "document.md"

    @staticmethod
    def _validate_markdown_file(file: UploadFile) -> None:
        file_name = file.filename or ""
        extension = Path(file_name).suffix.lower()

        if extension not in SUPPORTED_MARKDOWN_EXTENSIONS:
            raise UnsupportedFileType("Only Markdown files are supported.")

        if file.content_type and file.content_type not in MARKDOWN_MIME_TYPES:
            raise UnsupportedFileType("Only Markdown files are supported.")
