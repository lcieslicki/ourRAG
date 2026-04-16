from fastapi.testclient import TestClient

from app.api.dependencies.db import get_db
from app.infrastructure.storage.local import LocalFileStorage, get_local_file_storage
from app.main import app
from app.domain.models import Audit, DocumentVersion
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


def test_activate_ready_version_deactivates_other_versions_and_records_audit(db_session, tmp_path) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="admin")
    document = create_document(db_session, workspace=workspace, created_by=user)
    first = create_document_version(db_session, document=document, created_by=user, version_number=1, is_active=True)
    second = create_document_version(db_session, document=document, created_by=user, version_number=2, is_active=False)
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.post(
            f"/api/documents/{document.id}/versions/{second.id}/activate",
            headers={"X-User-Id": user.id},
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert response.json()["is_active"] is True
    db_session.refresh(first)
    db_session.refresh(second)
    assert first.is_active is False
    assert second.is_active is True
    audit = db_session.query(Audit).filter_by(event_type="document_version_activated", entity_id=second.id).one()
    assert audit.workspace_id == workspace.id
    assert audit.user_id == user.id


def test_invalidate_version_removes_active_eligibility_and_records_reason(db_session, tmp_path) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="owner")
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1, is_active=True)
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.post(
            f"/api/documents/{document.id}/versions/{version.id}/invalidate",
            headers={"X-User-Id": user.id},
            json={"reason": "Superseded"},
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_active"] is False
    assert payload["is_invalidated"] is True
    assert payload["invalidated_reason"] == "Superseded"
    db_session.refresh(version)
    eligible_versions = (
        db_session.query(DocumentVersion)
        .filter_by(document_id=document.id, is_active=True, is_invalidated=False)
        .all()
    )
    assert eligible_versions == []
    audit = db_session.query(Audit).filter_by(event_type="document_version_invalidated", entity_id=version.id).one()
    assert audit.payload_json["reason"] == "Superseded"


def test_activate_invalidated_version_is_rejected(db_session, tmp_path) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="admin")
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    version.is_invalidated = True
    db_session.flush()
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.post(
            f"/api/documents/{document.id}/versions/{version.id}/activate",
            headers={"X-User-Id": user.id},
        )
    finally:
        clear_overrides()

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "document_version_invalidated"


def test_activate_pending_version_is_rejected_as_not_ready(db_session, tmp_path) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="admin")
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    version.processing_status = "pending"
    db_session.flush()
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.post(
            f"/api/documents/{document.id}/versions/{version.id}/activate",
            headers={"X-User-Id": user.id},
        )
    finally:
        clear_overrides()

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "document_version_not_ready"


def test_member_cannot_activate_document_version(db_session, tmp_path) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="member")
    document = create_document(db_session, workspace=workspace, created_by=user)
    version = create_document_version(db_session, document=document, created_by=user, version_number=1)
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.post(
            f"/api/documents/{document.id}/versions/{version.id}/activate",
            headers={"X-User-Id": user.id},
        )
    finally:
        clear_overrides()

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "workspace_access_denied"


def test_activate_rejects_version_from_another_document(db_session, tmp_path) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="admin")
    document = create_document(db_session, workspace=workspace, created_by=user, slug_prefix="document-a")
    other_document = create_document(db_session, workspace=workspace, created_by=user, slug_prefix="document-b")
    other_version = create_document_version(db_session, document=other_document, created_by=user, version_number=1)
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.post(
            f"/api/documents/{document.id}/versions/{other_version.id}/activate",
            headers={"X-User-Id": user.id},
        )
    finally:
        clear_overrides()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "document_not_found"


def test_invalidate_rejects_cross_workspace_user(db_session, tmp_path) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session, slug_prefix="workspace-a")
    other_workspace = create_workspace(db_session, slug_prefix="workspace-b")
    create_membership(db_session, user=user, workspace=workspace, role="admin")
    other_document = create_document(db_session, workspace=other_workspace, created_by=user)
    other_version = create_document_version(db_session, document=other_document, created_by=user, version_number=1)
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.post(
            f"/api/documents/{other_document.id}/versions/{other_version.id}/invalidate",
            headers={"X-User-Id": user.id},
            json={"reason": "Should not be allowed"},
        )
    finally:
        clear_overrides()

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "workspace_access_denied"
