from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_db
from app.api.schemas.documents import DocumentUploadResponse
from app.domain.errors import DocumentAccessDenied, UnsupportedFileType, WorkspaceAccessDenied, WorkspaceRoleDenied
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
