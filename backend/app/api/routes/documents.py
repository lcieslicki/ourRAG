from typing import Annotated

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_db
from app.api.schemas.documents import (
    DocumentUploadResponse,
    DocumentVersionLifecycleResponse,
    DocumentVersionReindexResponse,
    InvalidateDocumentVersionRequest,
)
from app.domain.errors import (
    DocumentAccessDenied,
    DocumentVersionInvalidated,
    DocumentVersionNotFound,
    DocumentVersionNotReady,
    UnsupportedFileType,
    WorkspaceAccessDenied,
    WorkspaceRoleDenied,
)
from app.domain.services.documents import DocumentService
from app.infrastructure.storage.local import LocalFileStorage, get_local_file_storage

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    workspace_id: Annotated[str, Form()],
    title: Annotated[str, Form()],
    category: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[LocalFileStorage, Depends(get_local_file_storage)],
    document_id: Annotated[str | None, Form()] = None,
    tags: Annotated[str | None, Form()] = None,
) -> DocumentUploadResponse:
    service = DocumentService(db, storage)

    try:
        result = service.upload_markdown_version(
            user_id=current_user.id,
            workspace_id=workspace_id,
            file=file,
            title=title,
            category=category,
            document_id=document_id,
            tags=tags,
        )
        db.commit()
    except (WorkspaceAccessDenied, WorkspaceRoleDenied) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "workspace_access_denied", "message": str(exc)},
        ) from exc
    except DocumentAccessDenied as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "document_not_found", "message": str(exc)},
        ) from exc
    except UnsupportedFileType as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "unsupported_file_type", "message": str(exc)},
        ) from exc

    return DocumentUploadResponse(
        document_id=result.document.id,
        document_version_id=result.version.id,
        workspace_id=result.document.workspace_id,
        title=result.document.title,
        category=result.document.category,
        version_number=result.version.version_number,
        file_name=result.version.file_name,
        mime_type=result.version.mime_type,
        processing_status=result.version.processing_status,
        is_active=result.version.is_active,
    )


@router.post(
    "/{document_id}/versions/{version_id}/activate",
    response_model=DocumentVersionLifecycleResponse,
)
def activate_document_version(
    document_id: str,
    version_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[LocalFileStorage, Depends(get_local_file_storage)],
) -> DocumentVersionLifecycleResponse:
    service = DocumentService(db, storage)

    try:
        version = service.activate_version(
            user_id=current_user.id,
            document_id=document_id,
            version_id=version_id,
        )
        db.commit()
    except DocumentVersionNotReady as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "document_version_not_ready", "message": str(exc)},
        ) from exc
    except DocumentVersionInvalidated as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "document_version_invalidated", "message": str(exc)},
        ) from exc
    except (DocumentAccessDenied, DocumentVersionNotFound) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "document_not_found", "message": str(exc)},
        ) from exc
    except (WorkspaceAccessDenied, WorkspaceRoleDenied) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "workspace_access_denied", "message": str(exc)},
        ) from exc

    return _lifecycle_response(version)


@router.post(
    "/{document_id}/versions/{version_id}/invalidate",
    response_model=DocumentVersionLifecycleResponse,
)
def invalidate_document_version(
    document_id: str,
    version_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[LocalFileStorage, Depends(get_local_file_storage)],
    payload: InvalidateDocumentVersionRequest = Body(default_factory=InvalidateDocumentVersionRequest),
) -> DocumentVersionLifecycleResponse:
    service = DocumentService(db, storage)

    try:
        version = service.invalidate_version(
            user_id=current_user.id,
            document_id=document_id,
            version_id=version_id,
            reason=payload.reason,
        )
        db.commit()
    except (DocumentAccessDenied, DocumentVersionNotFound) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "document_not_found", "message": str(exc)},
        ) from exc
    except (WorkspaceAccessDenied, WorkspaceRoleDenied) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "workspace_access_denied", "message": str(exc)},
        ) from exc

    return _lifecycle_response(version)


@router.post(
    "/{document_id}/versions/{version_id}/reindex",
    response_model=DocumentVersionReindexResponse,
)
def reindex_document_version(
    document_id: str,
    version_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[LocalFileStorage, Depends(get_local_file_storage)],
) -> DocumentVersionReindexResponse:
    service = DocumentService(db, storage)

    try:
        job = service.request_reindex_version(
            user_id=current_user.id,
            document_id=document_id,
            version_id=version_id,
        )
        db.commit()
    except DocumentVersionInvalidated as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "document_version_invalidated", "message": str(exc)},
        ) from exc
    except (DocumentAccessDenied, DocumentVersionNotFound) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "document_not_found", "message": str(exc)},
        ) from exc
    except (WorkspaceAccessDenied, WorkspaceRoleDenied) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "workspace_access_denied", "message": str(exc)},
        ) from exc

    version = job.document_version
    return DocumentVersionReindexResponse(
        document_id=version.document.id,
        document_version_id=version.id,
        workspace_id=version.document.workspace_id,
        job_id=job.id,
        job_type=job.job_type,
        job_status=job.status,
    )


def _lifecycle_response(version) -> DocumentVersionLifecycleResponse:
    return DocumentVersionLifecycleResponse(
        document_id=version.document.id,
        document_version_id=version.id,
        workspace_id=version.document.workspace_id,
        version_number=version.version_number,
        processing_status=version.processing_status,
        is_active=version.is_active,
        is_invalidated=version.is_invalidated,
        invalidated_reason=version.invalidated_reason,
    )
