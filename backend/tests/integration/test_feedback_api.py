import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from tests.factories import create_conversation, create_user, create_workspace

client = TestClient(app)


@pytest.mark.integration
class TestFeedbackAPI:
    """Integration tests for feedback API endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        """Set up test data."""
        self.db = db_session
        self.workspace = create_workspace(db_session)
        self.user = create_user(db_session)
        self.conversation = create_conversation(db_session, workspace=self.workspace, user=self.user)
        self.headers = {"X-User-Id": self.user.id}

    def test_submit_feedback_creates_record(self) -> None:
        """Test POST /workspaces/{id}/feedback creates feedback."""
        payload = {
            "conversation_id": self.conversation.id,
            "message_id": "msg-123",
            "helpfulness": "helpful",
            "source_quality": "source_useful",
            "answer_completeness": "answer_complete",
            "comment": "Great answer!",
            "response_mode": "citation",
            "cited_source_ids": ["doc1"],
        }

        response = client.post(
            f"/api/workspaces/{self.workspace.id}/feedback",
            json=payload,
            headers=self.headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["workspace_id"] == self.workspace.id
        assert data["conversation_id"] == self.conversation.id
        assert data["message_id"] == "msg-123"
        assert data["helpfulness"] == "helpful"
        assert data["source_quality"] == "source_useful"
        assert data["answer_completeness"] == "answer_complete"
        assert data["comment"] == "Great answer!"
        assert data["response_mode"] == "citation"

    def test_submit_feedback_rejects_long_comment(self) -> None:
        """Test that feedback with comment > 1000 chars is rejected."""
        payload = {
            "conversation_id": self.conversation.id,
            "message_id": "msg-123",
            "comment": "x" * 1001,
        }

        response = client.post(
            f"/api/workspaces/{self.workspace.id}/feedback",
            json=payload,
            headers=self.headers,
        )

        assert response.status_code == 400
        data = response.json()
        assert "validation_error" in data.get("detail", {}).get("code", "")

    def test_submit_feedback_with_valid_max_comment(self) -> None:
        """Test that feedback with exactly 1000 char comment is accepted."""
        payload = {
            "conversation_id": self.conversation.id,
            "message_id": "msg-123",
            "comment": "x" * 1000,
        }

        response = client.post(
            f"/api/workspaces/{self.workspace.id}/feedback",
            json=payload,
            headers=self.headers,
        )

        assert response.status_code == 201

    def test_submit_feedback_requires_auth(self) -> None:
        """Test that feedback submission requires X-User-Id header."""
        payload = {
            "conversation_id": self.conversation.id,
            "message_id": "msg-123",
            "helpfulness": "helpful",
        }

        response = client.post(
            f"/api/workspaces/{self.workspace.id}/feedback",
            json=payload,
        )

        assert response.status_code == 401

    def test_list_feedback_returns_workspace_records(self) -> None:
        """Test GET /workspaces/{id}/feedback returns workspace-scoped feedback."""
        # Submit feedback
        payload = {
            "conversation_id": self.conversation.id,
            "message_id": "msg-123",
            "helpfulness": "helpful",
        }
        client.post(
            f"/api/workspaces/{self.workspace.id}/feedback",
            json=payload,
            headers=self.headers,
        )

        # List feedback
        response = client.get(
            f"/api/workspaces/{self.workspace.id}/feedback",
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["helpfulness"] == "helpful"

    def test_list_feedback_pagination(self) -> None:
        """Test feedback listing supports pagination."""
        # Submit multiple feedback records
        for i in range(5):
            payload = {
                "conversation_id": self.conversation.id,
                "message_id": f"msg-{i}",
                "helpfulness": "helpful",
            }
            client.post(
                f"/api/workspaces/{self.workspace.id}/feedback",
                json=payload,
                headers=self.headers,
            )

        # List with limit
        response = client.get(
            f"/api/workspaces/{self.workspace.id}/feedback?limit=2&offset=0",
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_get_feedback_summary(self) -> None:
        """Test GET /workspaces/{id}/feedback/summary returns statistics."""
        # Submit diverse feedback
        payloads = [
            {"message_id": "msg-1", "helpfulness": "helpful", "source_quality": "source_useful"},
            {"message_id": "msg-2", "helpfulness": "helpful", "source_quality": "source_not_useful"},
            {"message_id": "msg-3", "helpfulness": "not_helpful", "source_quality": "source_useful"},
            {"message_id": "msg-4", "helpfulness": "not_helpful"},
        ]

        for payload in payloads:
            payload["conversation_id"] = self.conversation.id
            client.post(
                f"/api/workspaces/{self.workspace.id}/feedback",
                json=payload,
                headers=self.headers,
            )

        # Get summary
        response = client.get(
            f"/api/workspaces/{self.workspace.id}/feedback/summary",
            headers=self.headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4
        assert data["helpful_count"] == 2
        assert data["not_helpful_count"] == 2
        assert data["source_useful_count"] == 2
        assert data["source_not_useful_count"] == 1

    def test_feedback_upsert_by_message(self) -> None:
        """Test that feedback is upserted by (workspace, conversation, message)."""
        # Submit initial feedback
        payload1 = {
            "conversation_id": self.conversation.id,
            "message_id": "msg-123",
            "helpfulness": "helpful",
            "comment": "Good",
        }
        response1 = client.post(
            f"/api/workspaces/{self.workspace.id}/feedback",
            json=payload1,
            headers=self.headers,
        )
        feedback_id_1 = response1.json()["id"]

        # Submit updated feedback for same message
        payload2 = {
            "conversation_id": self.conversation.id,
            "message_id": "msg-123",
            "helpfulness": "not_helpful",
            "comment": "Actually bad",
        }
        response2 = client.post(
            f"/api/workspaces/{self.workspace.id}/feedback",
            json=payload2,
            headers=self.headers,
        )
        feedback_id_2 = response2.json()["id"]

        # Should be same record
        assert feedback_id_1 == feedback_id_2
        assert response2.json()["helpfulness"] == "not_helpful"
        assert response2.json()["comment"] == "Actually bad"

        # Verify only one feedback exists
        list_response = client.get(
            f"/api/workspaces/{self.workspace.id}/feedback",
            headers=self.headers,
        )
        assert list_response.json()["total"] == 1
