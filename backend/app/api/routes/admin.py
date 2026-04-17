import io
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from app.api.dependencies import CurrentUser, get_current_user, get_db
from app.api.schemas.admin import (
    AdminDocumentIndexResult,
    AdminDocumentListItemResponse,
    AdminDocumentUploadResponse,
    AdminFolderIndexRequest,
    AdminFolderIndexResponse,
    AdminIndexFailure,
    AdminSetDataFolderRequest,
    ProcessingJobResponse,
    UserCreateRequest,
    UserResponse,
    WorkspaceCreateRequest,
    WorkspaceMemberAddRequest,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceSettingsResponse,
    WorkspaceSettingsUpdateRequest,
)
from app.core.config import get_settings
from app.domain.errors import WorkspaceAccessDenied, WorkspaceRoleDenied
from app.domain.models import Audit, Document, DocumentProcessingJob, DocumentVersion, Workspace
from app.domain.models.user import User
from app.domain.models.workspace import WorkspaceMembership
from app.domain.services.access import WorkspaceAccessService
from app.domain.services.documents import DocumentService
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.storage.local import LocalFileStorage, get_local_file_storage
from app.workers import IngestionJobRunner


class _FilePathUpload:
    """Adapts a Path to the UploadFile interface expected by DocumentService."""

    def __init__(self, path: Path) -> None:
        self.filename = path.name
        self.content_type = "text/markdown"
        self.file = io.BytesIO(path.read_bytes())
        self.headers = Headers({})


def _resolve_data_folder(data_root: Path, folder: str) -> Path:
    if ".." in Path(folder).parts:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "invalid_folder", "message": "Invalid path"})
    candidate = (data_root / folder.strip("/")).resolve()
    if data_root not in candidate.parents and candidate != data_root:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "invalid_folder", "message": "Path escapes data directory"})
    if not candidate.is_dir():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "invalid_folder", "message": "Folder not found"})
    return candidate


def _run_ingestion() -> None:
    with SessionLocal() as session:
        IngestionJobRunner.from_settings(session).run_until_idle()
        session.commit()


def _index_one(
    *,
    service: DocumentService,
    workspace_id: str,
    user_id: str,
    category: str,
    file: UploadFile | _FilePathUpload,
    db: Session,
) -> AdminDocumentIndexResult | AdminIndexFailure:
    file_name = file.filename or "document.md"
    title = Path(file_name).stem.replace("_", " ").replace("-", " ").title()
    sp = db.begin_nested()
    try:
        result = service.upload_markdown_version(
            user_id=user_id,
            workspace_id=workspace_id,
            file=file,  # type: ignore[arg-type]
            title=title,
            category=category,
        )
        sp.commit()
        return AdminDocumentIndexResult(
            document_id=result.document.id,
            document_version_id=result.version.id,
            title=result.document.title,
            file_name=file_name,
        )
    except WorkspaceRoleDenied:
        sp.rollback()
        return AdminIndexFailure(file_name=file_name, error="User must be workspace owner or admin")
    except Exception as exc:
        sp.rollback()
        return AdminIndexFailure(file_name=file_name, error=str(exc))

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


# ── Bootstrap document endpoints (no auth required) ──────────────────────────

@router.get("/workspaces/{workspace_id}/documents", response_model=list[AdminDocumentListItemResponse])
def list_workspace_documents(workspace_id: str, db: Annotated[Session, Depends(get_db)]) -> list[AdminDocumentListItemResponse]:
    documents = db.execute(
        select(Document)
        .where(Document.workspace_id == workspace_id)
        .order_by(Document.created_at.desc())
    ).scalars().all()

    result = []
    for doc in documents:
        versions = sorted(doc.versions, key=lambda v: v.version_number)
        latest = versions[-1] if versions else None
        result.append(AdminDocumentListItemResponse(
            id=doc.id,
            title=doc.title,
            category=doc.category,
            status=doc.status,
            latest_processing_status=latest.processing_status if latest else None,
            version_count=len(versions),
        ))
    return result


@router.post("/workspaces/{workspace_id}/documents/upload", response_model=AdminDocumentUploadResponse, status_code=status.HTTP_201_CREATED)
def admin_upload_documents(
    workspace_id: str,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[LocalFileStorage, Depends(get_local_file_storage)],
    user_id: Annotated[str, Form()],
    category: Annotated[str, Form()] = "admin",
    files: Annotated[list[UploadFile], File()] = (),
) -> AdminDocumentUploadResponse:
    service = DocumentService(db, storage)
    indexed: list[AdminDocumentIndexResult] = []
    failed: list[AdminIndexFailure] = []

    for file in files:
        outcome = _index_one(service=service, workspace_id=workspace_id, user_id=user_id, category=category, file=file, db=db)
        if isinstance(outcome, AdminDocumentIndexResult):
            indexed.append(outcome)
        else:
            failed.append(outcome)

    if indexed:
        db.commit()
        background_tasks.add_task(_run_ingestion)

    return AdminDocumentUploadResponse(indexed=indexed, failed=failed)


@router.post("/workspaces/{workspace_id}/documents/index-folder", response_model=AdminFolderIndexResponse)
def admin_index_folder(
    workspace_id: str,
    payload: AdminFolderIndexRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[LocalFileStorage, Depends(get_local_file_storage)],
) -> AdminFolderIndexResponse:
    folder = payload.folder
    if not folder:
        workspace = db.get(Workspace, workspace_id)
        folder = (workspace.settings_json or {}).get("data_folder") if workspace else None
    if not folder:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "no_folder_configured", "message": "No folder specified and workspace has no data_folder configured"})

    app_settings = get_settings()
    folder_path = _resolve_data_folder(app_settings.data_root, folder)
    md_files = sorted(folder_path.rglob("*.md"))

    if not md_files:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "no_markdown_files", "message": "No .md files found in folder"})

    service = DocumentService(db, storage)
    indexed: list[AdminDocumentIndexResult] = []
    failed: list[AdminIndexFailure] = []

    for path in md_files:
        outcome = _index_one(
            service=service,
            workspace_id=workspace_id,
            user_id=payload.user_id,
            category=payload.category,
            file=_FilePathUpload(path),
            db=db,
        )
        if isinstance(outcome, AdminDocumentIndexResult):
            indexed.append(outcome)
        else:
            failed.append(outcome)

    if indexed:
        db.commit()
        background_tasks.add_task(_run_ingestion)

    return AdminFolderIndexResponse(
        folder=folder,
        files_found=len(md_files),
        indexed=indexed,
        failed=failed,
    )


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


# ── Bootstrap endpoints (no auth required) ───────────────────────────────────

@router.get("/users", response_model=list[UserResponse])
def list_users(db: Annotated[Session, Depends(get_db)]) -> list[UserResponse]:
    users = db.execute(select(User).order_by(User.created_at.desc())).scalars().all()
    return [UserResponse(id=u.id, email=u.email, display_name=u.display_name, status=u.status, created_at=u.created_at) for u in users]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreateRequest, db: Annotated[Session, Depends(get_db)]) -> UserResponse:
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "email_taken", "message": "Email already in use"})
    user = User(email=payload.email.strip().lower(), display_name=payload.display_name.strip())
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(id=user.id, email=user.email, display_name=user.display_name, status=user.status, created_at=user.created_at)


@router.get("/workspaces", response_model=list[WorkspaceResponse])
def list_workspaces(db: Annotated[Session, Depends(get_db)]) -> list[WorkspaceResponse]:
    workspaces = db.execute(select(Workspace).order_by(Workspace.created_at.desc())).scalars().all()
    return [_workspace_response(w) for w in workspaces]


@router.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(payload: WorkspaceCreateRequest, db: Annotated[Session, Depends(get_db)]) -> WorkspaceResponse:
    existing = db.execute(select(Workspace).where(Workspace.slug == payload.slug)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "slug_taken", "message": "Workspace slug already in use"})
    workspace = Workspace(name=payload.name.strip(), slug=payload.slug.strip())
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return _workspace_response(workspace)


@router.put("/workspaces/{workspace_id}/data-folder", response_model=WorkspaceResponse)
def set_data_folder(workspace_id: str, payload: AdminSetDataFolderRequest, db: Annotated[Session, Depends(get_db)]) -> WorkspaceResponse:
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "workspace_not_found", "message": "Workspace not found"})
    settings = dict(workspace.settings_json or {})
    settings["data_folder"] = payload.folder.strip()
    workspace.settings_json = settings
    db.commit()
    return _workspace_response(workspace)


@router.get("/workspaces/{workspace_id}/members", response_model=list[WorkspaceMemberResponse])
def list_workspace_members(workspace_id: str, db: Annotated[Session, Depends(get_db)]) -> list[WorkspaceMemberResponse]:
    rows = db.execute(
        select(WorkspaceMembership, User)
        .join(User, WorkspaceMembership.user_id == User.id)
        .where(WorkspaceMembership.workspace_id == workspace_id)
        .order_by(WorkspaceMembership.created_at)
    ).all()
    return [WorkspaceMemberResponse(user_id=m.user_id, email=u.email, display_name=u.display_name, role=m.role) for m, u in rows]


@router.post("/workspaces/{workspace_id}/members", response_model=WorkspaceMemberResponse, status_code=status.HTTP_201_CREATED)
def add_workspace_member(workspace_id: str, payload: WorkspaceMemberAddRequest, db: Annotated[Session, Depends(get_db)]) -> WorkspaceMemberResponse:
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "workspace_not_found", "message": "Workspace not found"})
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "user_not_found", "message": "User not found"})
    existing = db.execute(
        select(WorkspaceMembership).where(WorkspaceMembership.workspace_id == workspace_id, WorkspaceMembership.user_id == payload.user_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "already_member", "message": "User is already a member of this workspace"})
    membership = WorkspaceMembership(workspace_id=workspace_id, user_id=payload.user_id, role=payload.role)
    db.add(membership)
    db.commit()
    return WorkspaceMemberResponse(user_id=user.id, email=user.email, display_name=user.display_name, role=membership.role)


# ─────────────────────────────────────────────────────────────────────────────

def _workspace_response(workspace: Workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        status=workspace.status,
        data_folder=(workspace.settings_json or {}).get("data_folder"),
        created_at=workspace.created_at,
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
