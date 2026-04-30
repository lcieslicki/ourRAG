import pytest
from sqlalchemy.orm import Session

from app.domain.models.feedback import Feedback
from app.domain.services.feedback import FeedbackService
from tests.factories import create_conversation, create_user, create_workspace


class TestFeedbackService:
    """Unit tests for FeedbackService."""

    def test_submit_creates_new_feedback(self, db_session: Session) -> None:
        """Test that submit_feedback creates a new feedback record."""
        workspace = create_workspace(db_session)
        user = create_user(db_session)
        conversation = create_conversation(db_session, workspace=workspace, user=user)

        feedback = FeedbackService.submit_feedback(
            db=db_session,
            workspace_id=workspace.id,
            conversation_id=conversation.id,
            message_id="msg-123",
            helpfulness="helpful",
            source_quality="source_useful",
            answer_completeness="answer_complete",
            comment="Great response!",
            response_mode="citation",
            cited_source_ids=["doc1", "doc2"],
        )

        assert feedback.id is not None
        assert feedback.workspace_id == workspace.id
        assert feedback.conversation_id == conversation.id
        assert feedback.message_id == "msg-123"
        assert feedback.helpfulness == "helpful"
        assert feedback.source_quality == "source_useful"
        assert feedback.answer_completeness == "answer_complete"
        assert feedback.comment == "Great response!"
        assert feedback.response_mode == "citation"
        assert feedback.cited_source_ids == ["doc1", "doc2"]

    def test_submit_updates_existing_feedback(self, db_session: Session) -> None:
        """Test that submit_feedback updates existing feedback by (workspace, conversation, message)."""
        workspace = create_workspace(db_session)
        user = create_user(db_session)
        conversation = create_conversation(db_session, workspace=workspace, user=user)

        # Create initial feedback
        feedback1 = FeedbackService.submit_feedback(
            db=db_session,
            workspace_id=workspace.id,
            conversation_id=conversation.id,
            message_id="msg-123",
            helpfulness="helpful",
            comment="Good",
        )
        db_session.commit()
        feedback_id_1 = feedback1.id

        # Update same feedback
        feedback2 = FeedbackService.submit_feedback(
            db=db_session,
            workspace_id=workspace.id,
            conversation_id=conversation.id,
            message_id="msg-123",
            helpfulness="not_helpful",
            comment="Actually, not helpful",
        )
        db_session.commit()

        # Should be the same record
        assert feedback2.id == feedback_id_1
        assert feedback2.helpfulness == "not_helpful"
        assert feedback2.comment == "Actually, not helpful"

        # Verify only one record exists
        all_feedback = db_session.query(Feedback).all()
        assert len(all_feedback) == 1

    def test_comment_over_limit_raises_value_error(self, db_session: Session) -> None:
        """Test that a comment over 1000 characters raises ValueError."""
        workspace = create_workspace(db_session)
        user = create_user(db_session)
        conversation = create_conversation(db_session, workspace=workspace, user=user)

        long_comment = "x" * 1001

        with pytest.raises(ValueError, match="Comment exceeds maximum length"):
            FeedbackService.submit_feedback(
                db=db_session,
                workspace_id=workspace.id,
                conversation_id=conversation.id,
                message_id="msg-123",
                comment=long_comment,
            )

    def test_list_feedback_returns_workspace_scoped_results(self, db_session: Session) -> None:
        """Test that list_feedback returns only feedback from the specified workspace."""
        workspace1 = create_workspace(db_session, slug_prefix="workspace1")
        workspace2 = create_workspace(db_session, slug_prefix="workspace2")
        user = create_user(db_session)
        conv1 = create_conversation(db_session, workspace=workspace1, user=user)
        conv2 = create_conversation(db_session, workspace=workspace2, user=user)

        # Create feedback in workspace1
        FeedbackService.submit_feedback(
            db=db_session,
            workspace_id=workspace1.id,
            conversation_id=conv1.id,
            message_id="msg-1",
            helpfulness="helpful",
        )

        # Create feedback in workspace2
        FeedbackService.submit_feedback(
            db=db_session,
            workspace_id=workspace2.id,
            conversation_id=conv2.id,
            message_id="msg-2",
            helpfulness="not_helpful",
        )

        db_session.commit()

        # List should return only workspace1 feedback
        feedback_list = FeedbackService.list_feedback(db=db_session, workspace_id=workspace1.id)
        assert len(feedback_list) == 1
        assert feedback_list[0].workspace_id == workspace1.id
        assert feedback_list[0].message_id == "msg-1"

    def test_get_summary_returns_correct_counts(self, db_session: Session) -> None:
        """Test that get_feedback_summary returns correct aggregated counts."""
        workspace = create_workspace(db_session)
        user = create_user(db_session)
        conversation = create_conversation(db_session, workspace=workspace, user=user)

        # Create various feedback records
        FeedbackService.submit_feedback(
            db=db_session,
            workspace_id=workspace.id,
            conversation_id=conversation.id,
            message_id="msg-1",
            helpfulness="helpful",
            source_quality="source_useful",
        )

        FeedbackService.submit_feedback(
            db=db_session,
            workspace_id=workspace.id,
            conversation_id=conversation.id,
            message_id="msg-2",
            helpfulness="helpful",
            source_quality="source_not_useful",
        )

        FeedbackService.submit_feedback(
            db=db_session,
            workspace_id=workspace.id,
            conversation_id=conversation.id,
            message_id="msg-3",
            helpfulness="not_helpful",
            source_quality="source_useful",
        )

        FeedbackService.submit_feedback(
            db=db_session,
            workspace_id=workspace.id,
            conversation_id=conversation.id,
            message_id="msg-4",
            helpfulness="not_helpful",
        )

        db_session.commit()

        summary = FeedbackService.get_feedback_summary(db=db_session, workspace_id=workspace.id)

        assert summary["total"] == 4
        assert summary["helpful_count"] == 2
        assert summary["not_helpful_count"] == 2
        assert summary["source_useful_count"] == 2
        assert summary["source_not_useful_count"] == 1
