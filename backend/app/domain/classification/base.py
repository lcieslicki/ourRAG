from abc import ABC, abstractmethod

from app.domain.classification.models import (
    DocumentClassificationResult,
    QueryClassificationResult,
)


class BaseDocumentClassifier(ABC):
    """Abstract base class for document classifiers."""

    @abstractmethod
    def classify_document(
        self,
        content: str,
        filename: str,
    ) -> DocumentClassificationResult:
        """
        Classify a document based on content and filename.

        Args:
            content: The document content text.
            filename: The document filename.

        Returns:
            DocumentClassificationResult with document type and confidence.
        """
        pass


class BaseQueryClassifier(ABC):
    """Abstract base class for query classifiers."""

    @abstractmethod
    def classify_query(
        self,
        query: str,
        workspace_context: dict | None = None,
    ) -> QueryClassificationResult:
        """
        Classify a query based on intent.

        Args:
            query: The query text.
            workspace_context: Optional context about the workspace (topics, settings, etc.).

        Returns:
            QueryClassificationResult with intent and in-scope signal.
        """
        pass
