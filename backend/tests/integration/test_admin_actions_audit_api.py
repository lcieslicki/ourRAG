from fastapi.testclient import TestClient
import pytest

from app.api.dependencies.db import get_db
from app.domain.models import Audit, DocumentProcessingJob
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


def test_admin_can_manage_versions_and_records_audit_events(db_session, tmp_path) -> None:
    admin = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=admin, workspace=workspace, role="admin")
    document = create_document(db_session, workspace=workspace, created_by=admin)
    first = create_document_version(db_session, document=document, created_by=admin, version_number=1, is_active=True)
    second = create_document_version(db_session, document=document, created_by=admin, version_number=2)
    client = client_with_dependencies(db_session, tmp_path)

    try:
        activate = client.post(
            f"/api/documents/{document.id}/versions/{second.id}/activate",
            headers={"X-User-Id": admin.id},
        )
        reindex = client.post(
            f"/api/documents/{document.id}/versions/{second.id}/reindex",
            headers={"X-User-Id": admin.id},
        )
        invalidate = client.post(
            f"/api/documents/{document.id}/versions/{first.id}/invalidate",
            headers={"X-User-Id": admin.id},
            json={"reason": "replaced by version 2"},
        )
    finally:
        clear_overrides()

    assert activate.status_code == 200
    assert activate.json()["is_active"] is True
    assert reindex.status_code == 200
    assert reindex.json()["job_type"] == "reindex_document_version"
    assert invalidate.status_code == 200
    assert invalidate.json()["is_invalidated"] is True

    job = db_session.get(DocumentProcessingJob, reindex.json()["job_id"])
    assert job is not None
    assert job.document_version_id == second.id
    assert job.status == "queued"

    audits = db_session.query(Audit).filter_by(workspace_id=workspace.id).all()
    audit_events = {audit.event_type for audit in audits}
    assert audit_events == {
        "document_version_activated",
        "document_version_reindex_requested",
        "document_version_invalidated",
    }
    assert all(audit.user_id == admin.id for audit in audits)


@pytest.mark.parametrize(
    ("action", "payload"),
    [
        ("activate", None),
        ("invalidate", {"reason": "not allowed"}),
        ("reindex", None),
    ],
)
def test_non_admin_cannot_perform_admin_actions_or_create_audit_events(
    db_session,
    tmp_path,
    action: str,
    payload: dict | None,
) -> None:
    member = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=member, workspace=workspace, role="member")
    document = create_document(db_session, workspace=workspace, created_by=member)
    version = create_document_version(db_session, document=document, created_by=member, version_number=1)
    member_id = member.id
    path = f"/api/documents/{document.id}/versions/{version.id}/{action}"
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.post(path, headers={"X-User-Id": member_id}, json=payload)
    finally:
        clear_overrides()

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "workspace_access_denied"
    assert db_session.query(Audit).count() == 0
    assert db_session.query(DocumentProcessingJob).count() == 0
