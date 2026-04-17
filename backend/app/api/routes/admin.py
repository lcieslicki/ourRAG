from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_db
from app.api.schemas.admin import ProcessingJobResponse, WorkspaceSettingsResponse, WorkspaceSettingsUpdateRequest
from app.domain.errors import WorkspaceAccessDenied, WorkspaceRoleDenied
from app.domain.models import Audit, Document, DocumentProcessingJob, DocumentVersion, Workspace
from app.domain.services.access import WorkspaceAccessService

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/workspaces/{workspace_id}/processing-jobs", response_model=list[ProcessingJobResponse])
def list_processing_jobs(
    workspace_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ProcessingJobResponse]:
    try:
        ensure_admin(db, user_id=current_user.id, workspace_id=workspace_id)
    except (WorkspaceAccessDenied, WorkspaceRoleDenied) as exc:
        raise workspace_denied(exc)

    jobs = db.execute(
        select(DocumentProcessingJob, DocumentVersion, Document)
        .join(DocumentVersion, DocumentProcessingJob.document_version_id == DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .where(Document.workspace_id == workspace_id)
        .order_by(DocumentProcessingJob.created_at.desc())
    ).all()

    return [
        ProcessingJobResponse(
            id=job.id,
            document_version_id=job.document_version_id,
            document_id=document.id,
            document_title=document.title,
            job_type=job.job_type,
            status=job.status,
            attempts=job.attempts,
            error_message=job.error_message,
            started_at=job.started_at,
            finished_at=job.finished_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        for job, _, document in jobs
    ]


@router.get("/workspaces/{workspace_id}/settings", response_model=WorkspaceSettingsResponse)
def get_workspace_settings(
    workspace_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkspaceSettingsResponse:
    try:
        ensure_admin(db, user_id=current_user.id, workspace_id=workspace_id)
    except (WorkspaceAccessDenied, WorkspaceRoleDenied) as exc:
        raise workspace_denied(exc)

    workspace = db.get(Workspace, workspace_id)
    return workspace_settings_response(workspace)


@router.put("/workspaces/{workspace_id}/settings", response_model=WorkspaceSettingsResponse)
def update_workspace_settings(
    workspace_id: str,
    payload: WorkspaceSettingsUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkspaceSettingsResponse:
    try:
        ensure_admin(db, user_id=current_user.id, workspace_id=workspace_id)
    except (WorkspaceAccessDenied, WorkspaceRoleDenied) as exc:
        raise workspace_denied(exc)

    workspace = db.get(Workspace, workspace_id)
    before = {
        "default_language": workspace.default_language,
        "system_prompt_override": workspace.system_prompt_override,
        "llm_model_override": workspace.llm_model_override,
        "embedding_model_override": workspace.embedding_model_override,
        "settings": workspace.settings_json,
    }

    if payload.default_language is not None:
        workspace.default_language = payload.default_language.strip()
    if payload.system_prompt_override is not None:
        workspace.system_prompt_override = payload.system_prompt_override.strip() or None
    if payload.llm_model_override is not None:
        workspace.llm_model_override = payload.llm_model_override.strip() or None
    if payload.embedding_model_override is not None:
        workspace.embedding_model_override = payload.embedding_model_override.strip() or None
    if payload.settings is not None:
        workspace.settings_json = payload.settings

    db.add(
        Audit(
            workspace_id=workspace.id,
            user_id=current_user.id,
            event_type="workspace_settings_updated",
            entity_type="workspace",
            entity_id=workspace.id,
            payload_json={
                "before": before,
                "after": {
                    "default_language": workspace.default_language,
                    "system_prompt_override": workspace.system_prompt_override,
                    "llm_model_override": workspace.llm_model_override,
                    "embedding_model_override": workspace.embedding_model_override,
                    "settings": workspace.settings_json,
                },
            },
        )
    )
    db.commit()
    return workspace_settings_response(workspace)


def ensure_admin(db: Session, *, user_id: str, workspace_id: str) -> None:
    WorkspaceAccessService(db).ensure_workspace_role(
        user_id=user_id,
        workspace_id=workspace_id,
        allowed_roles={"owner", "admin"},
    )


def workspace_denied(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "workspace_access_denied", "message": str(exc)},
    )


def workspace_settings_response(workspace: Workspace) -> WorkspaceSettingsResponse:
    return WorkspaceSettingsResponse(
        workspace_id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        status=workspace.status,
        default_language=workspace.default_language,
        system_prompt_override=workspace.system_prompt_override,
        llm_model_override=workspace.llm_model_override,
        embedding_model_override=workspace.embedding_model_override,
        settings=workspace.settings_json or {},
    )
