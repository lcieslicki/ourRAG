from pathlib import Path

from fastapi.testclient import TestClient

from app.api.dependencies.db import get_db
from app.infrastructure.storage.local import LocalFileStorage, get_local_file_storage
from app.main import app
from app.domain.models import Document, DocumentProcessingJob, DocumentVersion
from tests.factories import create_document, create_membership, create_user, create_workspace


def client_with_dependencies(db_session, tmp_path) -> TestClient:
    def override_db():
        yield db_session

    def override_storage():
        return LocalFileStorage(tmp_path)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_local_file_storage] = override_storage
    return TestClient(app)


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_upload_markdown_creates_document_version_and_stores_file(db_session, tmp_path) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="admin")
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.post(
            "/api/documents/upload",
            headers={"X-User-Id": user.id},
            data={
                "workspace_id": workspace.id,
                "title": "Vacation Policy",
                "category": "HR",
                "tags": "hr, vacation",
            },
            files={"file": ("vacation.md", b"# Vacation\n", "text/markdown")},
        )
    finally:
        clear_overrides()

    assert response.status_code == 201
    payload = response.json()
    document = db_session.get(Document, payload["document_id"])
    version = db_session.get(DocumentVersion, payload["document_version_id"])

    assert document is not None
    assert document.workspace_id == workspace.id
    assert document.tags_json == ["hr", "vacation"]
    assert version is not None
    assert version.document_id == document.id
    assert version.version_number == 1
    assert version.processing_status == "pending"
    assert version.is_active is False
    assert "storage_path" not in payload
    assert Path(tmp_path / version.storage_path).read_bytes() == b"# Vacation\n"
    assert version.storage_path.startswith(
        f"workspaces/{workspace.id}/documents/{document.id}/versions/{version.id}/original/"
    )
    job = db_session.query(DocumentProcessingJob).filter_by(document_version_id=version.id).one()
    assert job.job_type == "parse_document"
    assert job.status == "queued"


def test_upload_new_version_for_existing_document_increments_version_number(db_session, tmp_path) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="owner")
    document = create_document(db_session, workspace=workspace, created_by=user)
    client = client_with_dependencies(db_session, tmp_path)

    try:
        first = client.post(
            "/api/documents/upload",
            headers={"X-User-Id": user.id},
            data={
                "workspace_id": workspace.id,
                "document_id": document.id,
                "title": document.title,
                "category": document.category,
            },
            files={"file": ("first.md", b"# First\n", "text/markdown")},
        )
        second = client.post(
            "/api/documents/upload",
            headers={"X-User-Id": user.id},
            data={
                "workspace_id": workspace.id,
                "document_id": document.id,
                "title": document.title,
                "category": document.category,
            },
            files={"file": ("second.md", b"# Second\n", "text/markdown")},
        )
    finally:
        clear_overrides()

    assert first.status_code == 201
    assert first.json()["version_number"] == 1
    assert second.status_code == 201
    assert second.json()["version_number"] == 2
    assert second.json()["document_id"] == document.id


def test_upload_rejects_unsupported_file_type(db_session, tmp_path) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="admin")
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.post(
            "/api/documents/upload",
            headers={"X-User-Id": user.id},
            data={"workspace_id": workspace.id, "title": "Notes", "category": "HR"},
            files={"file": ("notes.txt", b"notes", "text/plain")},
        )
    finally:
        clear_overrides()

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "unsupported_file_type"


def test_upload_rejects_markdown_extension_with_unsupported_mime_type(db_session, tmp_path) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="admin")
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.post(
            "/api/documents/upload",
            headers={"X-User-Id": user.id},
            data={"workspace_id": workspace.id, "title": "Policy", "category": "HR"},
            files={"file": ("policy.md", b"# Policy\n", "application/pdf")},
        )
    finally:
        clear_overrides()

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "unsupported_file_type"
    assert db_session.query(Document).filter_by(workspace_id=workspace.id).count() == 0
    assert list(tmp_path.rglob("*")) == []


def test_upload_requires_admin_or_owner_role(db_session, tmp_path) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="member")
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.post(
            "/api/documents/upload",
            headers={"X-User-Id": user.id},
            data={"workspace_id": workspace.id, "title": "Policy", "category": "HR"},
            files={"file": ("policy.md", b"# Policy\n", "text/markdown")},
        )
    finally:
        clear_overrides()

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "workspace_access_denied"


def test_upload_existing_document_rejects_wrong_workspace(db_session, tmp_path) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session, slug_prefix="workspace-a")
    other_workspace = create_workspace(db_session, slug_prefix="workspace-b")
    create_membership(db_session, user=user, workspace=workspace, role="admin")
    other_document = create_document(db_session, workspace=other_workspace, created_by=user)
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.post(
            "/api/documents/upload",
            headers={"X-User-Id": user.id},
            data={
                "workspace_id": workspace.id,
                "document_id": other_document.id,
                "title": other_document.title,
                "category": other_document.category,
            },
            files={"file": ("policy.md", b"# Policy\n", "text/markdown")},
        )
    finally:
        clear_overrides()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "document_not_found"


def test_upload_rejects_missing_workspace_membership(db_session, tmp_path) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.post(
            "/api/documents/upload",
            headers={"X-User-Id": user.id},
            data={"workspace_id": workspace.id, "title": "Policy", "category": "HR"},
            files={"file": ("policy.md", b"# Policy\n", "text/markdown")},
        )
    finally:
        clear_overrides()

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "workspace_access_denied"
