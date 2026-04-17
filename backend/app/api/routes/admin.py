import io
import logging
import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from app.api.dependencies import CurrentUser, get_current_user, get_db
from app.api.schemas.admin import (
    AdminDocumentsBulkDeleteResponse,
    AdminDocumentsBulkReindexResponse,
    AdminDocumentIndexResult,
    AdminDocumentListItemResponse,
    AdminDocumentUploadResponse,
    AdminDocumentDeleteResponse,
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
from app.domain.services.processing_jobs import DocumentProcessingJobService, ProcessingJobNotFound
from app.domain.services.access import WorkspaceAccessService
from app.domain.services.documents import DocumentService
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.storage.local import LocalFileStorage, get_local_file_storage
from app.infrastructure.vector_index.qdrant import QdrantVectorIndex, VectorIndexError
from app.workers import IngestionJobRunner

logger = logging.getLogger(__name__)


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
    data_root = data_root.resolve()
    candidate = (data_root / folder.strip("/")).resolve()
    if data_root not in candidate.parents and candidate != data_root:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "invalid_folder", "message": "Path escapes data directory"})
    if not candidate.is_dir():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {"code": "invalid_folder", "message": f"Folder not found: {candidate} (data_root={data_root})"},
        )
    return candidate


def _run_ingestion() -> None:
    with SessionLocal() as session:
        IngestionJobRunner.from_settings(session).run_until_idle()
        session.commit()


def _processing_job_response(job: DocumentProcessingJob, document: Document) -> ProcessingJobResponse:
    return ProcessingJobResponse(
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


def _delete_document_with_artifacts(db: Session, *, workspace_id: str, document: Document) -> tuple[int, int]:
    versions = list(document.versions)
    vector_index = QdrantVectorIndex.from_settings(get_settings())
    for version in versions:
        try:
            vector_index.delete_document_version_vectors(
                workspace_id=workspace_id,
                document_version_id=version.id,
            )
        except VectorIndexError as exc:
            # Document deletion should still succeed when vector cleanup is already absent
            # (e.g. collection not initialized yet or version not indexed).
            logger.warning(
                "admin.delete_document.skip_vector_cleanup workspace_id=%s document_id=%s version_id=%s error=%s",
                workspace_id,
                document.id,
                version.id,
                str(exc),
            )

    document_storage_root = get_settings().storage.root / "workspaces" / workspace_id / "documents" / document.id
    if document_storage_root.exists():
        shutil.rmtree(document_storage_root)

    deleted_versions = len(versions)
    db.delete(document)
    return 1, deleted_versions


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
        _processing_job_response(job, document)
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


# ── Diagnostics ──────────────────────────────────────────────────────────────

@router.get("/data-info")
def data_info() -> dict:
    settings = get_settings()
    data_root = settings.data_root.resolve()
    exists = data_root.is_dir()
    subfolders = sorted(p.name for p in data_root.iterdir() if p.is_dir()) if exists else []
    return {
        "data_root": str(data_root),
        "files_storage_root": str(settings.storage.root),
        "exists": exists,
        "subfolders": subfolders,
    }


# ── Bootstrap document endpoints (no auth required) ──────────────────────────

@router.get("/workspaces/{workspace_id}/documents", response_model=list[AdminDocumentListItemResponse])
def list_workspace_documents(workspace_id: str, db: Annotated[Session, Depends(get_db)]) -> list[AdminDocumentListItemResponse]:
    documents = db.execute(
        select(Document)
        .where(Document.workspace_id == workspace_id)
        .order_by(Document.created_at.desc())
    ).scalars().all()

    latest_failed_job_rows = db.execute(
        select(DocumentProcessingJob, DocumentVersion)
        .join(DocumentVersion, DocumentProcessingJob.document_version_id == DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .where(Document.workspace_id == workspace_id, DocumentProcessingJob.status == "failed")
        .order_by(Document.id, DocumentProcessingJob.created_at.desc())
    ).all()
    latest_failed_by_document: dict[str, DocumentProcessingJob] = {}
    for job, version in latest_failed_job_rows:
        if version.document_id not in latest_failed_by_document:
            latest_failed_by_document[version.document_id] = job

    result = []
    for doc in documents:
        versions = sorted(doc.versions, key=lambda v: v.version_number)
        latest = versions[-1] if versions else None
        latest_failed = latest_failed_by_document.get(doc.id)
        result.append(AdminDocumentListItemResponse(
            id=doc.id,
            title=doc.title,
            category=doc.category,
            status=doc.status,
            latest_processing_status=latest.processing_status if latest else None,
            latest_version_id=latest.id if latest else None,
            latest_error_message=latest_failed.error_message if latest_failed else None,
            latest_error_job_type=latest_failed.job_type if latest_failed else None,
            version_count=len(versions),
        ))
    return result


@router.delete("/workspaces/{workspace_id}/documents/{document_id}", response_model=AdminDocumentDeleteResponse)
def delete_workspace_document(
    workspace_id: str,
    document_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> AdminDocumentDeleteResponse:
    document = db.get(Document, document_id)
    if document is None or document.workspace_id != workspace_id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            {"code": "document_not_found", "message": "Document not found in workspace"},
        )

    _, deleted_versions = _delete_document_with_artifacts(db, workspace_id=workspace_id, document=document)
    db.commit()
    return AdminDocumentDeleteResponse(document_id=document_id, deleted_versions=deleted_versions)


@router.delete("/workspaces/{workspace_id}/documents", response_model=AdminDocumentsBulkDeleteResponse)
def delete_all_workspace_documents(
    workspace_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> AdminDocumentsBulkDeleteResponse:
    documents = db.execute(select(Document).where(Document.workspace_id == workspace_id)).scalars().all()
    deleted_documents = 0
    deleted_versions = 0
    for document in documents:
        docs_count, versions_count = _delete_document_with_artifacts(db, workspace_id=workspace_id, document=document)
        deleted_documents += docs_count
        deleted_versions += versions_count

    db.commit()
    return AdminDocumentsBulkDeleteResponse(
        deleted_documents=deleted_documents,
        deleted_versions=deleted_versions,
    )


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


@router.post("/workspaces/{workspace_id}/documents/reindex-all", response_model=AdminDocumentsBulkReindexResponse)
def reindex_all_workspace_documents(
    workspace_id: str,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
) -> AdminDocumentsBulkReindexResponse:
    documents = db.execute(select(Document).where(Document.workspace_id == workspace_id)).scalars().all()
    service = DocumentProcessingJobService(db)
    queued_jobs = 0
    skipped_documents = 0

    for document in documents:
        versions = sorted(document.versions, key=lambda version: version.version_number)
        if not versions:
            skipped_documents += 1
            continue

        latest = versions[-1]
        if latest.is_invalidated:
            skipped_documents += 1
            continue

        service.enqueue(
            document_version_id=latest.id,
            job_type="reindex_document_version",
            reuse_succeeded=False,
        )
        queued_jobs += 1

    db.commit()
    if queued_jobs > 0:
        background_tasks.add_task(_run_ingestion)

    return AdminDocumentsBulkReindexResponse(
        queued_jobs=queued_jobs,
        skipped_documents=skipped_documents,
    )


@router.post("/workspaces/{workspace_id}/processing-jobs/{job_id}/retry", response_model=ProcessingJobResponse)
def retry_processing_job(
    workspace_id: str,
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
) -> ProcessingJobResponse:
    query = (
        select(DocumentProcessingJob, Document)
        .join(DocumentVersion, DocumentProcessingJob.document_version_id == DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .where(DocumentProcessingJob.id == job_id)
    )
    row = db.execute(query).one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "job_not_found", "message": "Processing job not found"})

    job, document = row
    if document.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "job_not_found", "message": "Processing job not found"})

    service = DocumentProcessingJobService(db)
    try:
        retried_job = service.retry_failed(job_id=job_id)
    except ProcessingJobNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "job_not_found", "message": "Processing job not found"}) from None

    db.commit()
    background_tasks.add_task(_run_ingestion)
    return _processing_job_response(retried_job, document)


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
