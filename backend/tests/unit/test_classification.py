import pytest

from app.domain.classification.models import (
    DocumentClassificationResult,
    DocumentType,
    QueryClassificationResult,
    QueryIntent,
)
from app.domain.classification.rule_based import (
    RuleBasedDocumentClassifier,
    RuleBasedQueryClassifier,
)
from app.domain.classification.service import (
    ClassificationConfig,
    ClassificationService,
)


class TestRuleBasedDocumentClassifier:
    """Tests for RuleBasedDocumentClassifier."""

    def test_classify_returns_procedure_for_procedure_keywords(self):
        """Document with 'procedura' keyword should be classified as procedure."""
        classifier = RuleBasedDocumentClassifier()
        result = classifier.classify_document(
            content="Procedura bezpieczeństwa w biurze",
            filename="safety.md",
        )

        assert isinstance(result, DocumentClassificationResult)
        assert result.document_type == DocumentType.procedure
        assert result.confidence == 0.5

    def test_classify_returns_policy_for_policy_keywords(self):
        """Document with 'polityka' keyword should be classified as policy."""
        classifier = RuleBasedDocumentClassifier()
        result = classifier.classify_document(
            content="Polityka firmy dotycząca urlopu",
            filename="policy.md",
        )

        assert result.document_type == DocumentType.policy
        assert result.confidence == 0.5

    def test_classify_returns_form_for_form_keywords(self):
        """Document with 'formularz' keyword should be classified as form."""
        classifier = RuleBasedDocumentClassifier()
        result = classifier.classify_document(
            content="Formularz wniosku o urlop",
            filename="form.docx",
        )

        assert result.document_type == DocumentType.form
        assert result.confidence >= 0.5

    def test_classify_returns_other_on_no_match(self):
        """Document with no matching keywords should return 'other' as fallback."""
        classifier = RuleBasedDocumentClassifier()
        result = classifier.classify_document(
            content="Random content without classification keywords",
            filename="unknown.md",
        )

        assert result.document_type == DocumentType.other
        assert result.confidence == 0.0
        assert result.is_fallback is True

    def test_confidence_increases_with_more_keywords(self):
        """Confidence should be 0.7 when 2+ keywords match."""
        classifier = RuleBasedDocumentClassifier()
        # Content with 2 procedure keywords
        result = classifier.classify_document(
            content="Procedura kroki instrukcja",
            filename="procedure.md",
        )

        assert result.document_type == DocumentType.procedure
        assert result.confidence == 0.7

    def test_classify_prefers_best_match(self):
        """Should return the type with highest confidence."""
        classifier = RuleBasedDocumentClassifier()
        # Content with policy (1 match) and instruction (2 matches)
        result = classifier.classify_document(
            content="Instrukcja guide how to bezpieczeństwa polityka",
            filename="guide.md",
        )

        assert result.document_type == DocumentType.instruction
        assert result.confidence == 0.7


class TestRuleBasedQueryClassifier:
    """Tests for RuleBasedQueryClassifier."""

    def test_classify_returns_summary_intent(self):
        """Query with 'streszcz' should be classified as summary."""
        classifier = RuleBasedQueryClassifier()
        result = classifier.classify_query(
            query="Streszcz politykę firmy"
        )

        assert isinstance(result, QueryClassificationResult)
        assert result.intent == QueryIntent.summary
        assert result.confidence == 0.5

    def test_classify_returns_extraction_intent(self):
        """Query with 'extract' should be classified as extraction."""
        classifier = RuleBasedQueryClassifier()
        result = classifier.classify_query(
            query="Extract data from the document"
        )

        assert result.intent == QueryIntent.extraction
        assert result.confidence == 0.5

    def test_classify_returns_admin_lookup_intent(self):
        """Query about admin should be classified as admin_lookup."""
        classifier = RuleBasedQueryClassifier()
        result = classifier.classify_query(
            query="Kto jest administratorem?"
        )

        assert result.intent == QueryIntent.admin_lookup
        assert result.confidence == 0.5

    def test_classify_default_qa_fallback(self):
        """Query without specific intent should default to qa."""
        classifier = RuleBasedQueryClassifier()
        result = classifier.classify_query(
            query="What is the vacation policy?"
        )

        assert result.intent == QueryIntent.qa
        assert result.confidence == 0.6
        assert result.is_fallback is True

    def test_classify_prefers_best_match(self):
        """Should return the intent with highest confidence."""
        classifier = RuleBasedQueryClassifier()
        # Query with 2 summary keywords
        result = classifier.classify_query(
            query="Streszcz i podsumuj dokument"
        )

        assert result.intent == QueryIntent.summary
        assert result.confidence == 0.7

    def test_query_out_of_scope_when_no_topic_match(self):
        """Query should be out-of-scope if workspace topics don't match."""
        classifier = RuleBasedQueryClassifier()
        result = classifier.classify_query(
            query="What about Python programming?",
            workspace_context={"topics": ["HR", "Finance"]},
        )

        assert result.is_in_scope is False

    def test_query_in_scope_when_topic_matches(self):
        """Query should be in-scope if workspace topics match."""
        classifier = RuleBasedQueryClassifier()
        result = classifier.classify_query(
            query="What is the HR policy?",
            workspace_context={"topics": ["HR", "Finance"]},
        )

        assert result.is_in_scope is True

    def test_query_in_scope_when_no_workspace_context(self):
        """Query should default to in-scope without workspace context."""
        classifier = RuleBasedQueryClassifier()
        result = classifier.classify_query(query="Random question")

        assert result.is_in_scope is True


class TestClassificationService:
    """Tests for ClassificationService."""

    def test_service_returns_none_when_disabled(self):
        """Service should return None when classification is disabled."""
        config = ClassificationConfig(enabled=False)
        service = ClassificationService(
            doc_classifier=RuleBasedDocumentClassifier(),
            query_classifier=RuleBasedQueryClassifier(),
            config=config,
        )

        result = service.classify_document("test", "test.md")
        assert result is None

        result = service.classify_query("test query")
        assert result is None

    def test_service_returns_none_when_document_disabled(self):
        """Service should return None when document classification is disabled."""
        config = ClassificationConfig(
            enabled=True,
            document_enabled=False,
        )
        service = ClassificationService(
            doc_classifier=RuleBasedDocumentClassifier(),
            query_classifier=RuleBasedQueryClassifier(),
            config=config,
        )

        result = service.classify_document("test", "test.md")
        assert result is None

    def test_service_returns_none_when_query_disabled(self):
        """Service should return None when query classification is disabled."""
        config = ClassificationConfig(
            enabled=True,
            query_enabled=False,
        )
        service = ClassificationService(
            doc_classifier=RuleBasedDocumentClassifier(),
            query_classifier=RuleBasedQueryClassifier(),
            config=config,
        )

        result = service.classify_query("test query")
        assert result is None

    def test_service_classify_document_safe_never_raises(self):
        """classify_document_safe should never raise exceptions."""
        config = ClassificationConfig()
        service = ClassificationService(
            doc_classifier=RuleBasedDocumentClassifier(),
            query_classifier=RuleBasedQueryClassifier(),
            config=config,
        )

        # Should not raise even with extreme input
        result = service.classify_document_safe("", "")
        assert isinstance(result, DocumentClassificationResult)
        assert result.is_fallback is True

    def test_service_classify_document_safe_returns_fallback_when_disabled(self):
        """classify_document_safe should return fallback when disabled."""
        config = ClassificationConfig(enabled=False)
        service = ClassificationService(
            doc_classifier=RuleBasedDocumentClassifier(),
            query_classifier=RuleBasedQueryClassifier(),
            config=config,
        )

        result = service.classify_document_safe("test", "test.md")
        assert result.document_type == DocumentType.other
        assert result.confidence == 0.0
        assert result.is_fallback is True

    def test_service_respects_workspace_context(self):
        """Service should pass workspace context to query classifier."""
        config = ClassificationConfig()
        service = ClassificationService(
            doc_classifier=RuleBasedDocumentClassifier(),
            query_classifier=RuleBasedQueryClassifier(),
            config=config,
        )

        result = service.classify_query(
            query="programming",
            workspace_context={"topics": ["HR", "Finance"]},
        )

        assert result.is_in_scope is False
