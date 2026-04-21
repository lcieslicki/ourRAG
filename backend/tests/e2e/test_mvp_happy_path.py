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
    def __init__(self) -> None:
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        prompt_text = "\n\n".join(message.content for message in request.messages)
        assert "Employees request vacation leave through the HR portal." in prompt_text
        return GenerationResponse(
            text="Vacation leave is requested through the HR portal and approved by a manager. [S1]",
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
    gateway = GroundedFakeGateway()
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
