from fastapi.testclient import TestClient

from app.api.dependencies.db import get_db
from app.api.dependencies.llm import get_generation_gateway
from app.api.dependencies.retrieval import get_query_embedding_service, get_retrieval_vector_index
from app.domain.embeddings import EmbeddingMetadata, EmbeddingResult
from app.domain.llm import GenerationResponse
from app.domain.models import Message
from app.infrastructure.vector_index import VectorIndexResult
from app.main import app
from tests.factories import create_conversation, create_document, create_membership, create_user, create_workspace


class FakeGateway:
    def __init__(self) -> None:
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return GenerationResponse(
            text="Assistant answer from fake gateway.",
            model="fake-bielik",
            provider="fake",
            finish_reason="stop",
            metadata={},
        )


class FakeEmbeddingService:
    def __init__(self) -> None:
        self.queries = []

    def embed_texts(self, inputs):
        return []

    def embed_chunks(self, chunks):
        return []

    def embed_query(self, query: str) -> EmbeddingResult:
        self.queries.append(query)
        return EmbeddingResult(
            vector=[0.1, 0.2],
            metadata=EmbeddingMetadata(
                provider="fake",
                model_name="fake-embed",
                model_version="fake-embed:v1",
                dimensions=2,
            ),
            input_metadata={"input_type": "query"},
        )


class FakeVectorIndex:
    def __init__(self, *, workspace_id: str | None = None, document_id: str = "document-1") -> None:
        self.workspace_id = workspace_id
        self.document_id = document_id
        self.queries = []

    def query(self, query):
        self.queries.append(query)
        if self.workspace_id is None:
            return []
        return [
            VectorIndexResult(
                id="chunk-1",
                score=0.92,
                payload={
                    "workspace_id": self.workspace_id,
                    "document_id": self.document_id,
                    "document_version_id": "version-1",
                    "chunk_id": "chunk-1",
                    "text": "Vacation requests must be submitted in the HR portal.",
                    "title": "HR Handbook",
                    "section_path": ["HR", "Vacation"],
                    "category": "HR",
                    "language": "pl",
                    "is_active": True,
                },
            )
        ]


def client_with_dependencies(
    db_session,
    gateway: FakeGateway | None = None,
    embedding_service: FakeEmbeddingService | None = None,
    vector_index: FakeVectorIndex | None = None,
) -> TestClient:
    def override_db():
        yield db_session

    def override_gateway():
        yield gateway or FakeGateway()

    def override_embedding_service():
        yield embedding_service or FakeEmbeddingService()

    def override_vector_index():
        yield vector_index or FakeVectorIndex()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_generation_gateway] = override_gateway
    app.dependency_overrides[get_query_embedding_service] = override_embedding_service
    app.dependency_overrides[get_retrieval_vector_index] = override_vector_index
    return TestClient(app)


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_create_and_list_conversations_for_workspace(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="member")
    client = client_with_dependencies(db_session)

    try:
        create_response = client.post(
            "/api/conversations",
            headers={"X-User-Id": user.id},
            json={"workspace_id": workspace.id, "title": "Vacation policy questions"},
        )
        list_response = client.get(
            "/api/conversations",
            headers={"X-User-Id": user.id},
            params={"workspace_id": workspace.id},
        )
    finally:
        clear_overrides()

    assert create_response.status_code == 201
    assert create_response.json()["workspace_id"] == workspace.id
    assert create_response.json()["title"] == "Vacation policy questions"
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [create_response.json()["id"]]


def test_create_conversation_requires_workspace_membership(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    client = client_with_dependencies(db_session)

    try:
        response = client.post(
            "/api/conversations",
            headers={"X-User-Id": user.id},
            json={"workspace_id": workspace.id, "title": "Blocked"},
        )
    finally:
        clear_overrides()

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "workspace_access_denied"


def test_get_conversation_returns_messages_and_summary_ready_shape(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="member")
    conversation = create_conversation(db_session, workspace=workspace, user=user)
    db_session.add(
        Message(
            conversation_id=conversation.id,
            workspace_id=workspace.id,
            user_id=user.id,
            role="user",
            content_text="Hello",
        )
    )
    db_session.flush()
    client = client_with_dependencies(db_session)

    try:
        response = client.get(
            f"/api/conversations/{conversation.id}",
            headers={"X-User-Id": user.id},
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == conversation.id
    assert payload["workspace_id"] == workspace.id
    assert payload["summary"] is None
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == "Hello"


def test_get_conversation_rejects_other_user(db_session) -> None:
    owner = create_user(db_session, email_prefix="owner")
    other = create_user(db_session, email_prefix="other")
    workspace = create_workspace(db_session)
    create_membership(db_session, user=owner, workspace=workspace, role="member")
    create_membership(db_session, user=other, workspace=workspace, role="member")
    conversation = create_conversation(db_session, workspace=workspace, user=owner)
    client = client_with_dependencies(db_session)

    try:
        response = client.get(
            f"/api/conversations/{conversation.id}",
            headers={"X-User-Id": other.id},
        )
    finally:
        clear_overrides()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "conversation_not_found"


def test_multi_workspace_user_lists_and_reads_only_requested_workspace_conversations(db_session) -> None:
    user = create_user(db_session)
    workspace_a = create_workspace(db_session, slug_prefix="workspace-a")
    workspace_b = create_workspace(db_session, slug_prefix="workspace-b")
    create_membership(db_session, user=user, workspace=workspace_a, role="member")
    create_membership(db_session, user=user, workspace=workspace_b, role="member")
    conversation_a = create_conversation(db_session, workspace=workspace_a, user=user)
    conversation_a.title = "Workspace A topic"
    conversation_b = create_conversation(db_session, workspace=workspace_b, user=user)
    conversation_b.title = "Workspace B topic"
    client = client_with_dependencies(db_session)

    try:
        response_a = client.get(
            "/api/conversations",
            headers={"X-User-Id": user.id},
            params={"workspace_id": workspace_a.id},
        )
        response_b = client.get(
            "/api/conversations",
            headers={"X-User-Id": user.id},
            params={"workspace_id": workspace_b.id},
        )
    finally:
        clear_overrides()

    assert response_a.status_code == 200
    assert [conversation["id"] for conversation in response_a.json()] == [conversation_a.id]
    assert response_b.status_code == 200
    assert [conversation["id"] for conversation in response_b.json()] == [conversation_b.id]


def test_chat_appends_user_and_assistant_messages(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="member")
    conversation = create_conversation(db_session, workspace=workspace, user=user)
    gateway = FakeGateway()
    embeddings = FakeEmbeddingService()
    vector_index = FakeVectorIndex(workspace_id=workspace.id)
    client = client_with_dependencies(db_session, gateway, embeddings, vector_index)

    try:
        response = client.post(
            "/api/chat",
            headers={"X-User-Id": user.id},
            json={
                "workspace_id": workspace.id,
                "conversation_id": conversation.id,
                "message": "How do I request vacation?",
            },
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"] == conversation.id
    assert payload["user_message"]["role"] == "user"
    assert payload["user_message"]["content"] == "How do I request vacation?"
    assert payload["assistant_message"]["role"] == "assistant"
    assert payload["assistant_message"]["content"] == "Assistant answer from fake gateway."
    assert payload["assistant_message"]["sources"][0]["document_title"] == "HR Handbook"
    assert payload["assistant_message"]["sources"][0]["section_path"] == "HR > Vacation"
    assert embeddings.queries == ["How do I request vacation?"]
    assert vector_index.queries[0].workspace_id == workspace.id
    assert vector_index.queries[0].active_only is True
    assert len(gateway.requests) == 1
    prompt_text = "\n\n".join(message.content for message in gateway.requests[0].messages)
    assert "Vacation requests must be submitted in the HR portal." in prompt_text

    messages = db_session.query(Message).filter_by(conversation_id=conversation.id).order_by(Message.created_at).all()
    assert [message.role for message in messages] == ["user", "assistant"]
    assert all(message.workspace_id == workspace.id for message in messages)
    assert messages[1].user_id is None
    assert messages[1].response_metadata_json["llm_model"] == "fake-bielik"
    assert messages[1].response_metadata_json["sources"][0]["chunk_id"] == "chunk-1"


def test_chat_prompt_preserves_follow_up_context_from_recent_messages(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="member")
    conversation = create_conversation(db_session, workspace=workspace, user=user)
    db_session.add_all(
        [
            Message(
                conversation_id=conversation.id,
                workspace_id=workspace.id,
                user_id=user.id,
                role="user",
                content_text="How do I request vacation leave?",
            ),
            Message(
                conversation_id=conversation.id,
                workspace_id=workspace.id,
                user_id=None,
                role="assistant",
                content_text="Use the HR portal for vacation leave.",
            ),
        ]
    )
    db_session.flush()
    gateway = FakeGateway()
    client = client_with_dependencies(db_session, gateway=gateway, vector_index=FakeVectorIndex(workspace_id=workspace.id))

    try:
        response = client.post(
            "/api/chat",
            headers={"X-User-Id": user.id},
            json={
                "workspace_id": workspace.id,
                "conversation_id": conversation.id,
                "message": "And what about approval?",
            },
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    prompt_text = "\n\n".join(message.content for message in gateway.requests[0].messages)
    assert "How do I request vacation leave?" in prompt_text
    assert "Use the HR portal for vacation leave." in prompt_text
    assert "And what about approval?" in prompt_text


def test_chat_memory_does_not_leak_between_workspaces_for_multi_workspace_user(db_session) -> None:
    user = create_user(db_session)
    workspace_a = create_workspace(db_session, slug_prefix="workspace-a")
    workspace_b = create_workspace(db_session, slug_prefix="workspace-b")
    create_membership(db_session, user=user, workspace=workspace_a, role="member")
    create_membership(db_session, user=user, workspace=workspace_b, role="member")
    conversation_a = create_conversation(db_session, workspace=workspace_a, user=user)
    conversation_b = create_conversation(db_session, workspace=workspace_b, user=user)
    db_session.add_all(
        [
            Message(
                conversation_id=conversation_a.id,
                workspace_id=workspace_a.id,
                user_id=user.id,
                role="user",
                content_text="Workspace A secret vacation context",
            ),
            Message(
                conversation_id=conversation_b.id,
                workspace_id=workspace_b.id,
                user_id=user.id,
                role="user",
                content_text="Workspace B incident context",
            ),
        ]
    )
    db_session.flush()
    gateway = FakeGateway()
    client = client_with_dependencies(db_session, gateway=gateway, vector_index=FakeVectorIndex(workspace_id=workspace_b.id))

    try:
        response = client.post(
            "/api/chat",
            headers={"X-User-Id": user.id},
            json={
                "workspace_id": workspace_b.id,
                "conversation_id": conversation_b.id,
                "message": "Continue that topic",
            },
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    prompt_text = "\n\n".join(message.content for message in gateway.requests[0].messages)
    assert "Workspace B incident context" in prompt_text
    assert "Workspace A secret vacation context" not in prompt_text


def test_chat_applies_category_scope_filters(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="member")
    conversation = create_conversation(db_session, workspace=workspace, user=user)
    vector_index = FakeVectorIndex(workspace_id=workspace.id)
    client = client_with_dependencies(db_session, vector_index=vector_index)

    try:
        response = client.post(
            "/api/chat",
            headers={"X-User-Id": user.id},
            json={
                "workspace_id": workspace.id,
                "conversation_id": conversation.id,
                "message": "What is HR policy?",
                "scope": {"mode": "category", "category": "HR", "language": "pl"},
            },
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert vector_index.queries[0].category == "HR"
    assert vector_index.queries[0].language == "pl"


def test_chat_applies_selected_document_scope_filters(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session)
    create_membership(db_session, user=user, workspace=workspace, role="member")
    document = create_document(db_session, workspace=workspace, created_by=user)
    conversation = create_conversation(db_session, workspace=workspace, user=user)
    vector_index = FakeVectorIndex(workspace_id=workspace.id, document_id=document.id)
    client = client_with_dependencies(db_session, vector_index=vector_index)

    try:
        response = client.post(
            "/api/chat",
            headers={"X-User-Id": user.id},
            json={
                "workspace_id": workspace.id,
                "conversation_id": conversation.id,
                "message": "Use selected doc",
                "scope": {"mode": "documents", "document_ids": [document.id]},
            },
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert vector_index.queries[0].document_ids == [document.id]


def test_chat_rejects_selected_document_outside_workspace(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session, slug_prefix="workspace-a")
    other_workspace = create_workspace(db_session, slug_prefix="workspace-b")
    create_membership(db_session, user=user, workspace=workspace, role="member")
    other_document = create_document(db_session, workspace=other_workspace, created_by=user)
    conversation = create_conversation(db_session, workspace=workspace, user=user)
    gateway = FakeGateway()
    vector_index = FakeVectorIndex(workspace_id=workspace.id)
    client = client_with_dependencies(db_session, gateway=gateway, vector_index=vector_index)

    try:
        response = client.post(
            "/api/chat",
            headers={"X-User-Id": user.id},
            json={
                "workspace_id": workspace.id,
                "conversation_id": conversation.id,
                "message": "Use selected doc",
                "scope": {"mode": "documents", "document_ids": [other_document.id]},
            },
        )
    finally:
        clear_overrides()

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_scope_filter"
    assert gateway.requests == []
    assert vector_index.queries == []


def test_chat_rejects_workspace_mismatch(db_session) -> None:
    user = create_user(db_session)
    workspace = create_workspace(db_session, slug_prefix="workspace-a")
    other_workspace = create_workspace(db_session, slug_prefix="workspace-b")
    create_membership(db_session, user=user, workspace=workspace, role="member")
    create_membership(db_session, user=user, workspace=other_workspace, role="member")
    conversation = create_conversation(db_session, workspace=workspace, user=user)
    gateway = FakeGateway()
    vector_index = FakeVectorIndex(workspace_id=workspace.id)
    client = client_with_dependencies(db_session, gateway=gateway, vector_index=vector_index)

    try:
        response = client.post(
            "/api/chat",
            headers={"X-User-Id": user.id},
            json={
                "workspace_id": other_workspace.id,
                "conversation_id": conversation.id,
                "message": "Cross workspace?",
            },
        )
    finally:
        clear_overrides()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "conversation_not_found"
    assert gateway.requests == []
    assert db_session.query(Message).filter_by(conversation_id=conversation.id).count() == 0
