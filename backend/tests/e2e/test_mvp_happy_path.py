from pathlib import Path

from fastapi.testclient import TestClient

from app.api.dependencies.db import get_db
from app.api.dependencies.llm import get_generation_gateway
from app.api.dependencies.retrieval import get_query_embedding_service, get_retrieval_vector_index
from app.domain.embeddings import EmbeddingMetadata, EmbeddingResult
from app.domain.llm import GenerationResponse
from app.domain.models import DocumentVersion
from app.infrastructure.storage.local import LocalFileStorage, get_local_file_storage
from app.infrastructure.vector_index import VectorIndexQuery, VectorIndexResult
from app.main import app
from app.workers.ingestion import IngestionJobRunner
from tests.factories import create_membership, create_user, create_workspace


class DeterministicEmbeddingService:
    metadata = EmbeddingMetadata(
        provider="fake",
        model_name="deterministic-e2e-embed",
        model_version="deterministic-e2e-embed:v1",
        dimensions=2,
    )

    def embed_texts(self, inputs):
        return [
            EmbeddingResult(
                vector=[1.0, float(index)],
                metadata=self.metadata,
                input_metadata=item.metadata,
            )
            for index, item in enumerate(inputs)
        ]

    def embed_chunks(self, chunks):
        return [
            EmbeddingResult(
                vector=[1.0, float(chunk.chunk_index)],
                metadata=self.metadata,
                input_metadata={"chunk_index": chunk.chunk_index},
            )
            for chunk in chunks
        ]

    def embed_query(self, query: str) -> EmbeddingResult:
        return EmbeddingResult(
            vector=[1.0, 0.0],
            metadata=self.metadata,
            input_metadata={"query": query},
        )


class InMemoryVectorIndex:
    def __init__(self) -> None:
        self.points = []

    def ensure_collection(self, *, vector_size: int, distance: str = "Cosine") -> None:
        return None

    def delete_document_version_vectors(self, *, workspace_id: str, document_version_id: str) -> None:
        self.points = [
            point
            for point in self.points
            if not (point.workspace_id == workspace_id and point.document_version_id == document_version_id)
        ]

    def upsert_chunk_vectors(self, points) -> None:
        self.points.extend(points)

    def query(self, query: VectorIndexQuery) -> list[VectorIndexResult]:
        results = []
        for point in self.points:
            if point.workspace_id != query.workspace_id:
                continue
            if query.active_only and not point.is_active:
                continue
            if query.category and point.category != query.category:
                continue
            if query.document_ids and point.document_id not in query.document_ids:
                continue
            if query.language and point.language != query.language:
                continue
            score = 0.99 if "vacation" in point.text.lower() else 0.5
            results.append(VectorIndexResult(id=point.point_id, score=score, payload=point.payload()))

        return sorted(results, key=lambda result: result.score, reverse=True)[: query.top_k]


class GroundedFakeGateway:
    def __init__(
        self,
        *,
        answer: str = "Vacation leave is requested through the HR portal and approved by a manager. [S1]",
        expected_prompt_fragments: list[str] | None = None,
    ) -> None:
        self.requests = []
        self.answer = answer
        self.expected_prompt_fragments = expected_prompt_fragments or []

    def generate(self, request):
        self.requests.append(request)
        prompt_text = "\n\n".join(message.content for message in request.messages)
        for fragment in self.expected_prompt_fragments:
            assert fragment in prompt_text
        return GenerationResponse(
            text=self.answer,
            model="fake-bielik-e2e",
            provider="fake",
            finish_reason="stop",
            metadata={},
        )


def client_with_dependencies(db_session, tmp_path, embedding_service, vector_index, gateway) -> TestClient:
    storage = LocalFileStorage(tmp_path)

    def override_db():
        yield db_session

    def override_storage():
        return storage

    def override_embedding_service():
        yield embedding_service

    def override_vector_index():
        yield vector_index

    def override_gateway():
        yield gateway

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_local_file_storage] = override_storage
    app.dependency_overrides[get_query_embedding_service] = override_embedding_service
    app.dependency_overrides[get_retrieval_vector_index] = override_vector_index
    app.dependency_overrides[get_generation_gateway] = override_gateway
    return TestClient(app)


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_mvp_upload_process_chat_happy_path(db_session, tmp_path) -> None:
    admin = create_user(db_session, email_prefix="admin")
    workspace = create_workspace(db_session, slug_prefix="acme-hr")
    create_membership(db_session, user=admin, workspace=workspace, role="admin")
    embedding_service = DeterministicEmbeddingService()
    vector_index = InMemoryVectorIndex()
    gateway = GroundedFakeGateway(expected_prompt_fragments=["Employees request vacation leave through the HR portal."])
    client = client_with_dependencies(db_session, tmp_path, embedding_service, vector_index, gateway)
    fixture = Path(__file__).parents[1] / "fixtures" / "retrieval" / "acme_hr_handbook.md"

    try:
        upload = client.post(
            "/api/documents/upload",
            headers={"X-User-Id": admin.id},
            data={
                "workspace_id": workspace.id,
                "title": "HR Handbook",
                "tags": "hr,vacation",
            },
            files={"file": ("hr_handbook.md", fixture.read_bytes(), "text/markdown")},
        )
        assert upload.status_code == 201
        upload_payload = upload.json()
        version = db_session.get(DocumentVersion, upload_payload["document_version_id"])
        assert version is not None
        assert version.processing_status == "pending"

        processed = IngestionJobRunner(
            db_session,
            storage=LocalFileStorage(tmp_path),
            embedding_service=embedding_service,
            vector_index=vector_index,
        ).run_until_idle()

        db_session.refresh(version)
        assert [job.job_type for job in processed] == [
            "parse_document",
            "chunk_document",
            "embed_document",
            "index_document",
        ]
        assert version.processing_status == "ready"
        assert version.is_active is True
        assert version.indexed_at is not None
        assert vector_index.points

        conversation = client.post(
            "/api/conversations",
            headers={"X-User-Id": admin.id},
            json={"workspace_id": workspace.id, "title": "Vacation question"},
        )
        assert conversation.status_code == 201
        conversation_id = conversation.json()["id"]

        chat = client.post(
            "/api/chat",
            headers={"X-User-Id": admin.id},
            json={
                "workspace_id": workspace.id,
                "conversation_id": conversation_id,
                "message": "How do I request vacation leave?",
                "scope": {"mode": "category", "category": "HR"},
            },
        )
    finally:
        clear_overrides()

    assert chat.status_code == 200
    payload = chat.json()
    assert payload["conversation_id"] == conversation_id
    assert "HR portal" in payload["assistant_message"]["content"]
    assert payload["assistant_message"]["sources"]
    source = payload["assistant_message"]["sources"][0]
    assert source["document_id"] == upload_payload["document_id"]
    assert source["document_title"] == "HR Handbook"
    assert source["document_version_id"] == version.id
    assert source["section_path"]
    assert "vacation" in source["snippet"].lower()
    assert gateway.requests


def test_e2e_tenant_isolation_returns_only_active_workspace_sources(db_session, tmp_path) -> None:
    user = create_user(db_session, email_prefix="tenant-admin")
    workspace_a = create_workspace(db_session, slug_prefix="acme-hr")
    workspace_b = create_workspace(db_session, slug_prefix="beta-hr")
    create_membership(db_session, user=user, workspace=workspace_a, role="admin")
    create_membership(db_session, user=user, workspace=workspace_b, role="admin")
    embedding_service = DeterministicEmbeddingService()
    vector_index = InMemoryVectorIndex()
    gateway = GroundedFakeGateway(answer="Acme vacation requests use the Acme HR portal. [S1]")
    client = client_with_dependencies(db_session, tmp_path, embedding_service, vector_index, gateway)

    try:
        acme = upload_markdown(
            client,
            user_id=user.id,
            workspace_id=workspace_a.id,
            title="Acme HR Handbook",
            file_name="hr_acme_handbook.md",
            content="# HR\n\nAcme vacation requests use the Acme HR portal.\n",
        )
        beta = upload_markdown(
            client,
            user_id=user.id,
            workspace_id=workspace_b.id,
            title="Beta HR Handbook",
            file_name="hr_beta_handbook.md",
            content="# HR\n\nBeta vacation requests use the Beta HR desk.\n",
        )
        process_ingestion(db_session, tmp_path, embedding_service, vector_index)
        conversation_id = create_chat_conversation(client, user_id=user.id, workspace_id=workspace_a.id)
        response = send_chat(
            client,
            user_id=user.id,
            workspace_id=workspace_a.id,
            conversation_id=conversation_id,
            message="How do I request vacation?",
            scope={"mode": "category", "category": "HR"},
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    sources = response.json()["assistant_message"]["sources"]
    assert sources
    assert {source["document_id"] for source in sources} == {acme["document_id"]}
    assert beta["document_id"] not in {source["document_id"] for source in sources}


def test_e2e_version_invalidation_returns_only_active_version_sources(db_session, tmp_path) -> None:
    user = create_user(db_session, email_prefix="version-admin")
    workspace = create_workspace(db_session, slug_prefix="version-hr")
    create_membership(db_session, user=user, workspace=workspace, role="admin")
    embedding_service = DeterministicEmbeddingService()
    vector_index = InMemoryVectorIndex()
    gateway = GroundedFakeGateway(answer="Use the new HR portal for vacation requests. [S1]")
    client = client_with_dependencies(db_session, tmp_path, embedding_service, vector_index, gateway)

    try:
        first = upload_markdown(
            client,
            user_id=user.id,
            workspace_id=workspace.id,
            title="Vacation Policy",
            file_name="hr_vacation_policy_v1.md",
            content="# Vacation\n\nOld vacation requests use legacy email.\n",
        )
        process_ingestion(db_session, tmp_path, embedding_service, vector_index)
        second = upload_markdown(
            client,
            user_id=user.id,
            workspace_id=workspace.id,
            title="Vacation Policy",
            file_name="hr_vacation_policy_v2.md",
            content="# Vacation\n\nNew vacation requests use the new HR portal.\n",
            document_id=first["document_id"],
        )
        process_ingestion(db_session, tmp_path, embedding_service, vector_index)
        invalidate = client.post(
            f"/api/documents/{first['document_id']}/versions/{first['document_version_id']}/invalidate",
            headers={"X-User-Id": user.id},
            json={"reason": "superseded"},
        )
        assert invalidate.status_code == 200
        conversation_id = create_chat_conversation(client, user_id=user.id, workspace_id=workspace.id)
        response = send_chat(
            client,
            user_id=user.id,
            workspace_id=workspace.id,
            conversation_id=conversation_id,
            message="How do I request vacation now?",
            scope={"mode": "category", "category": "HR"},
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    sources = response.json()["assistant_message"]["sources"]
    assert sources
    assert {source["document_version_id"] for source in sources} == {second["document_version_id"]}
    assert first["document_version_id"] not in {source["document_version_id"] for source in sources}
    assert "legacy email" not in prompt_text(gateway.requests[-1])


def test_e2e_category_filtering_limits_sources_to_requested_category(db_session, tmp_path) -> None:
    user = create_user(db_session, email_prefix="category-admin")
    workspace = create_workspace(db_session, slug_prefix="category-workspace")
    create_membership(db_session, user=user, workspace=workspace, role="admin")
    embedding_service = DeterministicEmbeddingService()
    vector_index = InMemoryVectorIndex()
    gateway = GroundedFakeGateway(answer="Vacation requests are handled by HR. [S1]")
    client = client_with_dependencies(db_session, tmp_path, embedding_service, vector_index, gateway)

    try:
        hr = upload_markdown(
            client,
            user_id=user.id,
            workspace_id=workspace.id,
            title="HR Handbook",
            file_name="hr_handbook.md",
            content="# HR\n\nVacation requests go through HR.\n",
        )
        it = upload_markdown(
            client,
            user_id=user.id,
            workspace_id=workspace.id,
            title="IT Onboarding",
            file_name="it_onboarding.md",
            content="# IT\n\nIncident reports go through the IT service desk.\n",
        )
        process_ingestion(db_session, tmp_path, embedding_service, vector_index)
        conversation_id = create_chat_conversation(client, user_id=user.id, workspace_id=workspace.id)
        response = send_chat(
            client,
            user_id=user.id,
            workspace_id=workspace.id,
            conversation_id=conversation_id,
            message="How are requests handled?",
            scope={"mode": "category", "category": "HR"},
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    sources = response.json()["assistant_message"]["sources"]
    assert sources
    assert {source["document_id"] for source in sources} == {hr["document_id"]}
    assert it["document_id"] not in {source["document_id"] for source in sources}


def test_e2e_multi_workspace_user_switching_keeps_contexts_separate(db_session, tmp_path) -> None:
    user = create_user(db_session, email_prefix="switch-admin")
    workspace_a = create_workspace(db_session, slug_prefix="switch-a")
    workspace_b = create_workspace(db_session, slug_prefix="switch-b")
    create_membership(db_session, user=user, workspace=workspace_a, role="admin")
    create_membership(db_session, user=user, workspace=workspace_b, role="admin")
    embedding_service = DeterministicEmbeddingService()
    vector_index = InMemoryVectorIndex()
    gateway = GroundedFakeGateway(answer="Workspace-specific answer. [S1]")
    client = client_with_dependencies(db_session, tmp_path, embedding_service, vector_index, gateway)

    try:
        doc_a = upload_markdown(
            client,
            user_id=user.id,
            workspace_id=workspace_a.id,
            title="Workspace A Handbook",
            file_name="hr_workspace_a.md",
            content="# HR\n\nWorkspace A vacation requests use Portal A.\n",
        )
        doc_b = upload_markdown(
            client,
            user_id=user.id,
            workspace_id=workspace_b.id,
            title="Workspace B Handbook",
            file_name="hr_workspace_b.md",
            content="# HR\n\nWorkspace B vacation requests use Portal B.\n",
        )
        process_ingestion(db_session, tmp_path, embedding_service, vector_index)
        conversation_a = create_chat_conversation(client, user_id=user.id, workspace_id=workspace_a.id)
        conversation_b = create_chat_conversation(client, user_id=user.id, workspace_id=workspace_b.id)
        response_a = send_chat(
            client,
            user_id=user.id,
            workspace_id=workspace_a.id,
            conversation_id=conversation_a,
            message="Where do vacation requests go?",
            scope={"mode": "category", "category": "HR"},
        )
        response_b = send_chat(
            client,
            user_id=user.id,
            workspace_id=workspace_b.id,
            conversation_id=conversation_b,
            message="Where do vacation requests go?",
            scope={"mode": "category", "category": "HR"},
        )
    finally:
        clear_overrides()

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert {source["document_id"] for source in response_a.json()["assistant_message"]["sources"]} == {doc_a["document_id"]}
    assert {source["document_id"] for source in response_b.json()["assistant_message"]["sources"]} == {doc_b["document_id"]}


def test_e2e_follow_up_memory_continuity_includes_recent_conversation_context(db_session, tmp_path) -> None:
    user = create_user(db_session, email_prefix="memory-admin")
    workspace = create_workspace(db_session, slug_prefix="memory-hr")
    create_membership(db_session, user=user, workspace=workspace, role="admin")
    embedding_service = DeterministicEmbeddingService()
    vector_index = InMemoryVectorIndex()
    gateway = GroundedFakeGateway(answer="Remote work needs manager approval. [S1]")
    client = client_with_dependencies(db_session, tmp_path, embedding_service, vector_index, gateway)

    try:
        upload_markdown(
            client,
            user_id=user.id,
            workspace_id=workspace.id,
            title="Remote Work Policy",
            file_name="hr_remote_work.md",
            content="# Remote Work\n\nRemote work requires manager approval and a weekly team check-in.\n",
        )
        process_ingestion(db_session, tmp_path, embedding_service, vector_index)
        conversation_id = create_chat_conversation(client, user_id=user.id, workspace_id=workspace.id)
        first = send_chat(
            client,
            user_id=user.id,
            workspace_id=workspace.id,
            conversation_id=conversation_id,
            message="What is the remote work policy?",
            scope={"mode": "category", "category": "HR"},
        )
        assert first.status_code == 200
        second = send_chat(
            client,
            user_id=user.id,
            workspace_id=workspace.id,
            conversation_id=conversation_id,
            message="What approval does it need?",
            scope={"mode": "category", "category": "HR"},
        )
    finally:
        clear_overrides()

    assert second.status_code == 200
    assert len(gateway.requests) == 2
    second_prompt = prompt_text(gateway.requests[-1])
    assert "What is the remote work policy?" in second_prompt
    assert "Remote work needs manager approval. [S1]" in second_prompt
    assert "What approval does it need?" in second_prompt


def upload_markdown(
    client: TestClient,
    *,
    user_id: str,
    workspace_id: str,
    title: str,
    file_name: str,
    content: str,
    document_id: str | None = None,
) -> dict:
    data = {
        "workspace_id": workspace_id,
        "title": title,
        "tags": "e2e",
    }
    if document_id:
        data["document_id"] = document_id

    response = client.post(
        "/api/documents/upload",
        headers={"X-User-Id": user_id},
        data=data,
        files={"file": (file_name, content.encode("utf-8"), "text/markdown")},
    )
    assert response.status_code == 201
    return response.json()


def process_ingestion(db_session, tmp_path, embedding_service, vector_index) -> None:
    processed = IngestionJobRunner(
        db_session,
        storage=LocalFileStorage(tmp_path),
        embedding_service=embedding_service,
        vector_index=vector_index,
    ).run_until_idle()
    assert processed
    assert all(job.status == "succeeded" for job in processed)


def create_chat_conversation(client: TestClient, *, user_id: str, workspace_id: str) -> str:
    response = client.post(
        "/api/conversations",
        headers={"X-User-Id": user_id},
        json={"workspace_id": workspace_id, "title": "E2E question"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def send_chat(
    client: TestClient,
    *,
    user_id: str,
    workspace_id: str,
    conversation_id: str,
    message: str,
    scope: dict | None = None,
):
    payload = {
        "workspace_id": workspace_id,
        "conversation_id": conversation_id,
        "message": message,
    }
    if scope:
        payload["scope"] = scope
    return client.post("/api/chat", headers={"X-User-Id": user_id}, json=payload)


def prompt_text(request) -> str:
    return "\n\n".join(message.content for message in request.messages)
