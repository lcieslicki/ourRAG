from fastapi.testclient import TestClient

from app.api.dependencies.db import get_db
from app.domain.models import DocumentProcessingJob
from app.infrastructure.storage.local import LocalFileStorage, get_local_file_storage
from app.main import app
from tests.factories import create_document, create_document_version, create_membership, create_user, create_workspace


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


def test_reindex_document_version_enqueues_job(db_session, tmp_path) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="admin")
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.post(
            f"/api/documents/{document.id}/versions/{version.id}/reindex",
            headers={"X-User-Id": user.id},
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == document.id
    assert payload["document_version_id"] == version.id
    assert payload["job_type"] == "reindex_document_version"
    assert payload["job_status"] == "queued"
    job = db_session.get(DocumentProcessingJob, payload["job_id"])
    assert job is not None
    assert job.document_version_id == version.id


def test_reindex_document_version_requires_admin_or_owner(db_session, tmp_path) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="member")
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.post(
            f"/api/documents/{document.id}/versions/{version.id}/reindex",
            headers={"X-User-Id": user.id},
        )
    finally:
        clear_overrides()

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "workspace_access_denied"
