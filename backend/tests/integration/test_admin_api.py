from fastapi.testclient import TestClient

from app.api.dependencies.db import get_db
from app.infrastructure.storage.local import LocalFileStorage, get_local_file_storage
from app.main import app
from app.domain.models import Audit
from tests.factories import (
    create_document,
    create_document_version,
    create_membership,
    create_processing_job,
    create_user,
    create_workspace,
)


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


def test_admin_can_list_documents_and_versions(db_session, tmp_path) -> None:
    admin = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=admin, workspace=workspace, role="admin")
    document = create_document(db_session, workspace=workspace, created_by=admin)
    first = create_document_version(db_session, document=document, created_by=admin, version_number=1)
    second = create_document_version(db_session, document=document, created_by=admin, version_number=2, is_active=True)
    second.chunk_count = 3
    second.embedding_model_name = "fake-embed"
    second.embedding_model_version = "fake:v1"
    client = client_with_dependencies(db_session, tmp_path)

    try:
        list_response = client.get(
            "/api/documents",
            headers={"X-User-Id": admin.id},
            params={"workspace_id": workspace.id},
        )
        detail_response = client.get(
            f"/api/documents/{document.id}",
            headers={"X-User-Id": admin.id},
        )
    finally:
        clear_overrides()

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload[0]["id"] == document.id
    assert list_payload[0]["version_count"] == 2
    assert list_payload[0]["active_version_id"] == second.id
    assert list_payload[0]["latest_processing_status"] == second.processing_status

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["id"] == document.id
    assert [version["id"] for version in detail_payload["versions"]] == [first.id, second.id]
    assert detail_payload["versions"][1]["chunk_count"] == 3
    assert detail_payload["versions"][1]["embedding_model_name"] == "fake-embed"


def test_document_admin_surface_rejects_member_role(db_session, tmp_path) -> None:
    member = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=member, workspace=workspace, role="member")
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.get(
            "/api/documents",
            headers={"X-User-Id": member.id},
            params={"workspace_id": workspace.id},
        )
    finally:
        clear_overrides()

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "workspace_access_denied"


def test_admin_can_read_processing_jobs(db_session, tmp_path) -> None:
    admin = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=admin, workspace=workspace, role="owner")
    document = create_document(db_session, workspace=workspace, created_by=admin)
    version = create_document_version(db_session, document=document, created_by=admin, version_number=1)
    job = create_processing_job(db_session, document_version=version, job_type="embed_document", status="failed", attempts=2)
    job.error_message = "embedding unavailable"
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.get(
            f"/api/admin/workspaces/{workspace.id}/processing-jobs",
            headers={"X-User-Id": admin.id},
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["id"] == job.id
    assert payload[0]["document_id"] == document.id
    assert payload[0]["document_title"] == document.title
    assert payload[0]["job_type"] == "embed_document"
    assert payload[0]["status"] == "failed"
    assert payload[0]["attempts"] == 2
    assert payload[0]["error_message"] == "embedding unavailable"


def test_admin_can_read_and_update_workspace_settings_with_audit(db_session, tmp_path) -> None:
    admin = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=admin, workspace=workspace, role="admin")
    client = client_with_dependencies(db_session, tmp_path)

    try:
        read_response = client.get(
            f"/api/admin/workspaces/{workspace.id}/settings",
            headers={"X-User-Id": admin.id},
        )
        update_response = client.put(
            f"/api/admin/workspaces/{workspace.id}/settings",
            headers={"X-User-Id": admin.id},
            json={
                "default_language": "pl",
                "system_prompt_override": "Use concise Polish answers.",
                "llm_model_override": "bielik-custom",
                "embedding_model_override": "nomic-custom",
                "settings": {"retrieval": {"top_k": 4}},
            },
        )
    finally:
        clear_overrides()

    assert read_response.status_code == 200
    assert read_response.json()["workspace_id"] == workspace.id
    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["system_prompt_override"] == "Use concise Polish answers."
    assert payload["llm_model_override"] == "bielik-custom"
    assert payload["embedding_model_override"] == "nomic-custom"
    assert payload["settings"] == {"retrieval": {"top_k": 4}}

    audit = db_session.query(Audit).filter_by(event_type="workspace_settings_updated").one()
    assert audit.workspace_id == workspace.id
    assert audit.user_id == admin.id
    assert audit.payload_json["after"]["llm_model_override"] == "bielik-custom"


def test_admin_settings_rejects_member_role(db_session, tmp_path) -> None:
    member = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=member, workspace=workspace, role="member")
    client = client_with_dependencies(db_session, tmp_path)

    try:
        response = client.get(
            f"/api/admin/workspaces/{workspace.id}/settings",
            headers={"X-User-Id": member.id},
        )
    finally:
        clear_overrides()

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "workspace_access_denied"
