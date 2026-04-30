from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.domain.models.feedback import Feedback


class FeedbackService:
    """Service for managing feedback submissions and queries."""

    COMMENT_MAX_CHARS = 1000

    @staticmethod
    def _validate_comment(comment: str | None) -> None:
        """Validate comment length."""
        if comment and len(comment) > FeedbackService.COMMENT_MAX_CHARS:
            raise ValueError(f"Comment exceeds maximum length of {FeedbackService.COMMENT_MAX_CHARS} characters")

    @staticmethod
    def submit_feedback(
        db: Session,
        workspace_id: str,
        conversation_id: str,
        message_id: str | None,
        helpfulness: str | None = None,
        source_quality: str | None = None,
        answer_completeness: str | None = None,
        comment: str | None = None,
        response_mode: str | None = None,
        cited_source_ids: dict | None = None,
    ) -> Feedback:
        """
        Submit or update feedback for a message.
        Upserts by (workspace_id, conversation_id, message_id).
        """
        FeedbackService._validate_comment(comment)

        # Try to find existing feedback
        existing = db.execute(
            select(Feedback).where(
                and_(
                    Feedback.workspace_id == workspace_id,
                    Feedback.conversation_id == conversation_id,
                    Feedback.message_id == message_id,
                )
            )
        ).scalar_one_or_none()

        if existing:
            # Update existing feedback
            if helpfulness is not None:
                existing.helpfulness = helpfulness
            if source_quality is not None:
                existing.source_quality = source_quality
            if answer_completeness is not None:
                existing.answer_completeness = answer_completeness
            if comment is not None:
                existing.comment = comment
            if response_mode is not None:
                existing.response_mode = response_mode
            if cited_source_ids is not None:
                existing.cited_source_ids = cited_source_ids
            feedback = existing
        else:
            # Create new feedback
            feedback = Feedback(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                message_id=message_id,
                helpfulness=helpfulness,
                source_quality=source_quality,
                answer_completeness=answer_completeness,
                comment=comment,
                response_mode=response_mode,
                cited_source_ids=cited_source_ids,
            )
            db.add(feedback)

        db.flush()
        return feedback

    @staticmethod
    def list_feedback(
        db: Session,
        workspace_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Feedback]:
        """List feedback for a workspace with pagination."""
        return db.execute(
            select(Feedback)
            .where(Feedback.workspace_id == workspace_id)
            .order_by(Feedback.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()

    @staticmethod
    def get_feedback_summary(db: Session, workspace_id: str) -> dict:
        """Get summary statistics for feedback in a workspace."""
        feedbacks = db.execute(
            select(Feedback).where(Feedback.workspace_id == workspace_id)
        ).scalars().all()

        total = len(feedbacks)
        helpful_count = sum(1 for f in feedbacks if f.helpfulness == "helpful")
        not_helpful_count = sum(1 for f in feedbacks if f.helpfulness == "not_helpful")
        source_useful_count = sum(1 for f in feedbacks if f.source_quality == "source_useful")
        source_not_useful_count = sum(1 for f in feedbacks if f.source_quality == "source_not_useful")

        return {
            "total": total,
            "helpful_count": helpful_count,
            "not_helpful_count": not_helpful_count,
            "source_useful_count": source_useful_count,
            "source_not_useful_count": source_not_useful_count,
        }
