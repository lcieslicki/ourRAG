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


class RuleBasedDocumentClassifier(BaseDocumentClassifier):
    """Classifies documents using keyword matching rules."""

    # Keyword patterns for each document type
    KEYWORDS = {
        DocumentType.procedure: [
            "procedura",
            "procedure",
            "kroki",
            "steps",
            "instrukcja",
        ],
        DocumentType.policy: [
            "polityka",
            "policy",
            "zasady",
            "rules",
            "regulamin",
        ],
        DocumentType.faq: [
            "faq",
            "często zadawane",
            "pytania i odpowiedzi",
            "frequently asked",
        ],
        DocumentType.form: [
            ".docx",
            "formularz",
            "wniosek",
            "form",
        ],
        DocumentType.instruction: [
            "instrukcja",
            "guide",
            "jak",
            "how to",
        ],
    }

    def classify_document(
        self,
        content: str,
        filename: str,
    ) -> DocumentClassificationResult:
        """
        Classify a document using keyword matching.

        Confidence is calculated based on match count:
        - 1 match: 0.5 confidence
        - 2+ matches: 0.7 confidence
        """
        text_lower = content.lower()
        filename_lower = filename.lower()
        combined = f"{text_lower} {filename_lower}"

        best_type = DocumentType.other
        best_confidence = 0.0

        for doc_type, keywords in self.KEYWORDS.items():
            match_count = sum(
                1 for keyword in keywords if keyword in combined
            )

            if match_count > 0:
                # Confidence: 0.5 for 1 match, 0.7 for 2+
                confidence = 0.5 if match_count == 1 else 0.7

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_type = doc_type

        is_fallback = best_type == DocumentType.other

        return DocumentClassificationResult(
            label=best_type.value,
            confidence=best_confidence if not is_fallback else 0.0,
            document_type=best_type,
            inferred_department=None,
            is_fallback=is_fallback,
            provider_strategy="rule_based",
        )


class RuleBasedQueryClassifier(BaseQueryClassifier):
    """Classifies query intent using keyword matching rules."""

    # Keyword patterns for each intent
    INTENT_KEYWORDS = {
        QueryIntent.summary: [
            "streszcz",
            "podsumuj",
            "brief",
            "summarize",
            "skrót",
        ],
        QueryIntent.extraction: [
            "wyciągnij",
            "extract",
            "pobierz dane",
            "schemat",
            "schema",
        ],
        QueryIntent.admin_lookup: [
            "kto jest",
            "who is",
            "admin",
            "lista użytkowników",
        ],
    }

    def classify_query(
        self,
        query: str,
        workspace_context: dict | None = None,
    ) -> QueryClassificationResult:
        """
        Classify a query intent using keyword matching.

        Defaults to 'qa' if no specific intent matches.
        In-scope is determined by simple heuristic matching against workspace topics.
        """
        if workspace_context is None:
            workspace_context = {}

        query_lower = query.lower()
        best_intent = QueryIntent.qa
        best_confidence = 0.0
        is_in_scope = True

        # Check for specific intents
        for intent, keywords in self.INTENT_KEYWORDS.items():
            match_count = sum(1 for kw in keywords if kw in query_lower)

            if match_count > 0:
                # Confidence: 0.5 for 1 match, 0.7 for 2+
                confidence = 0.5 if match_count == 1 else 0.7

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_intent = intent

        # Default to qa if no specific intent matched
        if best_intent == QueryIntent.qa:
            best_confidence = 0.6

        # Simple out-of-scope heuristic:
        # If workspace has topics and query doesn't contain any, flag as potentially out-of-scope
        workspace_topics = workspace_context.get("topics", [])
        if workspace_topics:
            has_matching_topic = any(
                topic.lower() in query_lower for topic in workspace_topics
            )
            if not has_matching_topic:
                is_in_scope = False

        is_fallback = best_intent == QueryIntent.qa and best_confidence == 0.6

        return QueryClassificationResult(
            label=best_intent.value,
            confidence=best_confidence,
            intent=best_intent,
            is_in_scope=is_in_scope,
            is_fallback=is_fallback,
            provider_strategy="rule_based",
        )
