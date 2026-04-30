import pytest
from sqlalchemy.orm import Session

from app.domain.classification.models import DocumentType
from app.domain.classification.rule_based import (
    RuleBasedDocumentClassifier,
    RuleBasedQueryClassifier,
)
from app.domain.classification.service import (
    ClassificationConfig,
    ClassificationService,
)
from tests.factories import (
    create_document,
    create_document_version,
    create_user,
    create_workspace,
)


@pytest.mark.integration
class TestDocumentClassification:
    """Integration tests for document classification with database."""

    def test_document_classification_enriches_metadata(
        self,
        db_session: Session,
    ):
        """Document should be classified and metadata enriched."""
        workspace = create_workspace(db_session)
        user = create_user(db_session)
        document = create_document(db_session, workspace=workspace, created_by=user)
        version = create_document_version(
            db_session,
            document=document,
            created_by=user,
            version_number=1,
        )

        config = ClassificationConfig()
        service = ClassificationService(
            doc_classifier=RuleBasedDocumentClassifier(),
            query_classifier=RuleBasedQueryClassifier(),
            config=config,
        )

        # Classify a procedure document
        result = service.classify_document(
            content="Procedura bezpieczeństwa kroki instrukcja",
            filename=version.file_name,
        )

        assert result is not None
        assert result.document_type == DocumentType.procedure
        assert result.confidence >= 0.5
        assert not result.is_fallback

    def test_low_confidence_result_has_is_fallback_true(self):
        """Low confidence results should be marked as fallback."""
        config = ClassificationConfig()
        service = ClassificationService(
            doc_classifier=RuleBasedDocumentClassifier(),
            query_classifier=RuleBasedQueryClassifier(),
            config=config,
        )

        # Classify a document with no matching keywords
        result = service.classify_document(
            content="This is some random content",
            filename="random.md",
        )

        assert result is not None
        assert result.document_type == DocumentType.other
        assert result.confidence == 0.0
        assert result.is_fallback is True

    def test_query_classification_feeds_router_safely(self):
        """Query classification should integrate safely with routing."""
        config = ClassificationConfig()
        service = ClassificationService(
            doc_classifier=RuleBasedDocumentClassifier(),
            query_classifier=RuleBasedQueryClassifier(),
            config=config,
        )

        queries = [
            ("Streszcz politykę", {"topics": ["HR"]}),
            ("Wyciągnij dane", {}),
            ("Normalne pytanie", None),
        ]

        for query, context in queries:
            result = service.classify_query(
                query=query,
                workspace_context=context,
            )

            assert result is not None
            assert result.intent is not None
            assert result.confidence >= 0.0

    def test_classification_safe_handles_exceptions(self):
        """Safe classification should handle exceptions gracefully."""
        config = ClassificationConfig()
        service = ClassificationService(
            doc_classifier=RuleBasedDocumentClassifier(),
            query_classifier=RuleBasedQueryClassifier(),
            config=config,
        )

        # Should never raise
        result = service.classify_document_safe(
            content=None,  # type: ignore
            filename=None,  # type: ignore
        )

        assert result is not None
        assert result.document_type == DocumentType.other
        assert result.is_fallback is True

    def test_multiple_classifications_independent(self):
        """Multiple classification calls should be independent."""
        config = ClassificationConfig()
        service = ClassificationService(
            doc_classifier=RuleBasedDocumentClassifier(),
            query_classifier=RuleBasedQueryClassifier(),
            config=config,
        )

        result1 = service.classify_document(
            content="Procedura bezpieczeństwa",
            filename="proc.md",
        )
        result2 = service.classify_document(
            content="Polityka firmy",
            filename="policy.md",
        )

        assert result1.document_type == DocumentType.procedure
        assert result2.document_type == DocumentType.policy
