from dataclasses import dataclass
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.domain.embeddings import EmbeddingMetadata, EmbeddingResult
from app.domain.services.retrieval import RetrievalScope, RetrievalService
from app.infrastructure.vector_index import VectorIndexQuery, VectorIndexResult
from tests.factories import create_document, create_document_version, create_membership, create_user, create_workspace


@dataclass(frozen=True)
class FixtureChunk:
    workspace_id: str
    document_id: str
    document_version_id: str
    chunk_id: str
    text: str
    title: str
    category: str
    section_path: list[str]
    language: str
    is_active: bool
    vector: tuple[float, float, float]


class FixtureEmbeddingService:
    vectors = {
        "vacation": [1.0, 0.0, 0.0],
        "incident": [0.0, 1.0, 0.0],
        "onboarding": [0.0, 0.2, 1.0],
        "compliance": [0.0, 0.0, 1.0],
        "remote": [0.7, 0.2, 0.0],
    }

    def embed_texts(self, inputs):
        return []

    def embed_chunks(self, chunks):
        return []

    def embed_query(self, query: str) -> EmbeddingResult:
        lowered = query.lower()
        vector = [0.0, 0.0, 0.0]
        for keyword, candidate in self.vectors.items():
            if keyword in lowered:
                vector = candidate
                break

        return EmbeddingResult(
            vector=vector,
            metadata=EmbeddingMetadata(
                provider="fixture",
                model_name="fixture-retrieval",
                model_version="fixture-retrieval:v1",
                dimensions=3,
            ),
            input_metadata={"input_type": "query"},
        )


class FixtureVectorIndex:
    def __init__(self, chunks: list[FixtureChunk]) -> None:
        self.chunks = chunks
        self.queries: list[VectorIndexQuery] = []

    def query(self, query: VectorIndexQuery) -> list[VectorIndexResult]:
        self.queries.append(query)
        candidates = [
            chunk
            for chunk in self.chunks
            if chunk.workspace_id == query.workspace_id
            and (not query.active_only or chunk.is_active)
            and (query.category is None or chunk.category == query.category)
            and (query.document_ids is None or chunk.document_id in query.document_ids)
            and (query.language is None or chunk.language == query.language)
        ]
        ranked = sorted(
            candidates,
            key=lambda chunk: dot_product(query.vector, chunk.vector),
            reverse=True,
        )
        return [
            VectorIndexResult(
                id=chunk.chunk_id,
                score=dot_product(query.vector, chunk.vector),
                payload={
                    "workspace_id": chunk.workspace_id,
                    "document_id": chunk.document_id,
                    "document_version_id": chunk.document_version_id,
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "title": chunk.title,
                    "category": chunk.category,
                    "section_path": chunk.section_path,
                    "language": chunk.language,
                    "is_active": chunk.is_active,
                },
            )
            for chunk in ranked[: query.top_k]
        ]


def test_fixture_retrieval_returns_correct_top_k_chunks(db_session) -> None:
    fixture = build_retrieval_fixture(db_session)

    response = fixture.service.retrieve(
        user_id=fixture.user_id,
        workspace_id=fixture.acme_workspace_id,
        query="How do I request vacation leave?",
        top_k=2,
    )

    assert [chunk.chunk_id for chunk in response.chunks] == ["acme-hr-vacation-v2", "acme-hr-remote-v2"]
    assert "HR portal" in response.chunks[0].chunk_text
    assert fixture.vector_index.queries[-1].top_k == 2


def test_fixture_retrieval_enforces_workspace_isolation(db_session) -> None:
    fixture = build_retrieval_fixture(db_session)

    response = fixture.service.retrieve(
        user_id=fixture.user_id,
        workspace_id=fixture.acme_workspace_id,
        query="vacation legal retention",
        top_k=5,
    )

    assert response.chunks
    assert {chunk.payload["workspace_id"] for chunk in response.chunks} == {fixture.acme_workspace_id}
    assert "Beta only" not in " ".join(chunk.chunk_text for chunk in response.chunks)


def test_fixture_retrieval_supports_category_restricted_scope(db_session) -> None:
    fixture = build_retrieval_fixture(db_session)

    response = fixture.service.retrieve(
        user_id=fixture.user_id,
        workspace_id=fixture.acme_workspace_id,
        query="How do I report an incident?",
        scope=RetrievalScope(category="IT"),
        top_k=5,
    )

    assert [chunk.category for chunk in response.chunks] == ["IT", "IT"]
    assert response.chunks[0].chunk_id == "acme-it-incident-v1"
    assert fixture.vector_index.queries[-1].category == "IT"


def test_fixture_retrieval_supports_selected_document_scope(db_session) -> None:
    fixture = build_retrieval_fixture(db_session)

    response = fixture.service.retrieve(
        user_id=fixture.user_id,
        workspace_id=fixture.acme_workspace_id,
        query="Where is onboarding described?",
        scope=RetrievalScope(document_ids=(fixture.it_document_id,)),
        top_k=5,
    )

    assert response.chunks
    assert {chunk.document_id for chunk in response.chunks} == {fixture.it_document_id}
    assert response.chunks[0].chunk_id == "acme-it-onboarding-v1"
    assert fixture.vector_index.queries[-1].document_ids == [fixture.it_document_id]


def test_fixture_retrieval_uses_active_versions_only(db_session) -> None:
    fixture = build_retrieval_fixture(db_session)

    response = fixture.service.retrieve(
        user_id=fixture.user_id,
        workspace_id=fixture.acme_workspace_id,
        query="How do I request vacation leave?",
        scope=RetrievalScope(document_ids=(fixture.hr_document_id,)),
        top_k=5,
    )

    assert "old paper form" not in " ".join(chunk.chunk_text for chunk in response.chunks)
    assert "HR portal" in response.chunks[0].chunk_text
    assert {chunk.document_version_id for chunk in response.chunks} == {fixture.hr_version_v2_id}
    assert fixture.vector_index.queries[-1].active_only is True


@dataclass(frozen=True)
class RetrievalFixture:
    service: RetrievalService
    vector_index: FixtureVectorIndex
    user_id: str
    acme_workspace_id: str
    hr_document_id: str
    hr_version_v2_id: str
    it_document_id: str


def build_retrieval_fixture(db_session) -> RetrievalFixture:
    assert fixture_text("acme_hr_handbook.md")
    assert fixture_text("acme_it_onboarding.md")
    assert fixture_text("beta_legal_compliance.md")

    user = create_user(db_session, email_prefix="fixture-user")
    acme = create_workspace(db_session, slug_prefix="acme")
    beta = create_workspace(db_session, slug_prefix="beta")
    create_membership(db_session, user=user, workspace=acme, role="member")
    create_membership(db_session, user=user, workspace=beta, role="member")

    hr_document = create_document(db_session, workspace=acme, created_by=user, slug_prefix="hr-handbook")
    hr_document.title = "HR Handbook"
    hr_document.category = "HR"
    it_document = create_document(db_session, workspace=acme, created_by=user, slug_prefix="it-onboarding")
    it_document.title = "IT Onboarding Guide"
    it_document.category = "IT"
    legal_document = create_document(db_session, workspace=beta, created_by=user, slug_prefix="legal-compliance")
    legal_document.title = "Legal Compliance Memo"
    legal_document.category = "Legal"

    hr_v1 = create_document_version(db_session, document=hr_document, created_by=user, version_number=1)
    hr_v1.is_active = False
    hr_v1.is_invalidated = True
    hr_v1.invalidated_reason = "superseded by version 2"
    hr_v2 = create_document_version(db_session, document=hr_document, created_by=user, version_number=2, is_active=True)
    it_v1 = create_document_version(db_session, document=it_document, created_by=user, version_number=1, is_active=True)
    legal_v1 = create_document_version(db_session, document=legal_document, created_by=user, version_number=1, is_active=True)
    db_session.flush()

    chunks = [
        FixtureChunk(
            workspace_id=acme.id,
            document_id=hr_document.id,
            document_version_id=hr_v1.id,
            chunk_id="acme-hr-vacation-v1",
            text="Vacation leave uses an old paper form. This version is invalidated.",
            title=hr_document.title,
            category="HR",
            section_path=["HR Handbook"],
            language="pl",
            is_active=False,
            vector=(1.2, 0.0, 0.0),
        ),
        FixtureChunk(
            workspace_id=acme.id,
            document_id=hr_document.id,
            document_version_id=hr_v2.id,
            chunk_id="acme-hr-vacation-v2",
            text="Employees request vacation leave through the HR portal.",
            title=hr_document.title,
            category="HR",
            section_path=["HR Handbook"],
            language="pl",
            is_active=True,
            vector=(1.0, 0.0, 0.0),
        ),
        FixtureChunk(
            workspace_id=acme.id,
            document_id=hr_document.id,
            document_version_id=hr_v2.id,
            chunk_id="acme-hr-remote-v2",
            text="Remote work requires manager approval and a weekly team check-in.",
            title=hr_document.title,
            category="HR",
            section_path=["HR Handbook", "Remote Work"],
            language="pl",
            is_active=True,
            vector=(0.7, 0.2, 0.0),
        ),
        FixtureChunk(
            workspace_id=acme.id,
            document_id=it_document.id,
            document_version_id=it_v1.id,
            chunk_id="acme-it-incident-v1",
            text="Security incidents must be reported in the IT incident channel immediately.",
            title=it_document.title,
            category="IT",
            section_path=["IT Onboarding Guide", "Incident Reporting"],
            language="pl",
            is_active=True,
            vector=(0.0, 1.0, 0.0),
        ),
        FixtureChunk(
            workspace_id=acme.id,
            document_id=it_document.id,
            document_version_id=it_v1.id,
            chunk_id="acme-it-onboarding-v1",
            text="New employees receive laptop setup instructions during IT onboarding.",
            title=it_document.title,
            category="IT",
            section_path=["IT Onboarding Guide"],
            language="pl",
            is_active=True,
            vector=(0.0, 0.9, 0.1),
        ),
        FixtureChunk(
            workspace_id=beta.id,
            document_id=legal_document.id,
            document_version_id=legal_v1.id,
            chunk_id="beta-legal-vacation-retention-v1",
            text="Vacation-related legal retention records belong to Beta only.",
            title=legal_document.title,
            category="Legal",
            section_path=["Legal Compliance Memo"],
            language="pl",
            is_active=True,
            vector=(1.1, 0.0, 0.4),
        ),
    ]
    vector_index = FixtureVectorIndex(chunks)
    return RetrievalFixture(
        service=RetrievalService(
            session=db_session,
            embedding_service=FixtureEmbeddingService(),
            vector_index=vector_index,
            settings=get_settings(),
        ),
        vector_index=vector_index,
        user_id=user.id,
        acme_workspace_id=acme.id,
        hr_document_id=hr_document.id,
        hr_version_v2_id=hr_v2.id,
        it_document_id=it_document.id,
    )


def fixture_text(name: str) -> str:
    return (Path(pytest.FIXTURES_DIR) / "retrieval" / name).read_text(encoding="utf-8")


def dot_product(left: list[float], right: tuple[float, float, float]) -> float:
    return sum(value * right[index] for index, value in enumerate(left))
