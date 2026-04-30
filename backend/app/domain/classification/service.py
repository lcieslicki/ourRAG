import logging

from app.domain.classification.base import (
    BaseDocumentClassifier,
    BaseQueryClassifier,
)
from app.domain.classification.models import (
    DocumentClassificationResult,
    DocumentType,
    QueryClassificationResult,
    QueryIntent,
)


logger = logging.getLogger(__name__)


class ClassificationConfig:
    """Configuration for classification service."""

    def __init__(
        self,
        enabled: bool = True,
        document_enabled: bool = True,
        query_enabled: bool = True,
        min_confidence: float = 0.65,
        provider: str = "rule_based",
    ) -> None:
        self.enabled = enabled
        self.document_enabled = document_enabled
        self.query_enabled = query_enabled
        self.min_confidence = min_confidence
        self.provider = provider


class ClassificationService:
    """Service for document and query classification."""

    def __init__(
        self,
        doc_classifier: BaseDocumentClassifier,
        query_classifier: BaseQueryClassifier,
        config: ClassificationConfig,
    ) -> None:
        self.doc_classifier = doc_classifier
        self.query_classifier = query_classifier
        self.config = config

    def classify_document(
        self,
        content: str,
        filename: str,
    ) -> DocumentClassificationResult | None:
        """
        Classify a document if enabled.

        Returns None if CLASSIFICATION_DOCUMENT_ENABLED=False.
        """
        if not self.config.enabled or not self.config.document_enabled:
            return None

        return self.doc_classifier.classify_document(content, filename)

    def classify_query(
        self,
        query: str,
        workspace_context: dict | None = None,
    ) -> QueryClassificationResult | None:
        """
        Classify a query if enabled.

        Returns None if CLASSIFICATION_QUERY_ENABLED=False.
        """
        if not self.config.enabled or not self.config.query_enabled:
            return None

        if workspace_context is None:
            workspace_context = {}

        return self.query_classifier.classify_query(query, workspace_context)

    def classify_document_safe(
        self,
        content: str,
        filename: str,
    ) -> DocumentClassificationResult:
        """
        Classify a document with fallback on any error.

        Never raises. Returns fallback (other, confidence=0.0) if classification fails.
        """
        try:
            result = self.classify_document(content, filename)
            if result is None:
                # Classification disabled
                return DocumentClassificationResult(
                    label=DocumentType.other.value,
                    confidence=0.0,
                    document_type=DocumentType.other,
                    is_fallback=True,
                    provider_strategy="rule_based",
                )
            return result
        except Exception as e:
            logger.exception(f"Document classification failed: {e}")
            return DocumentClassificationResult(
                label=DocumentType.other.value,
                confidence=0.0,
                document_type=DocumentType.other,
                is_fallback=True,
                provider_strategy="rule_based",
            )
