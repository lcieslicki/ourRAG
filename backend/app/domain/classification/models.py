from enum import Enum

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Classification of document types."""
    procedure = "procedure"
    policy = "policy"
    instruction = "instruction"
    faq = "faq"
    form = "form"
    other = "other"


class QueryIntent(str, Enum):
    """Classification of query intents."""
    qa = "qa"
    summary = "summary"
    extraction = "extraction"
    admin_lookup = "admin_lookup"
    other = "other"


class ClassificationResult(BaseModel):
    """Base classification result with confidence and provider strategy."""
    label: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    provider_strategy: str = "rule_based"
    is_fallback: bool = False
    metadata: dict = Field(default_factory=dict)


class DocumentClassificationResult(ClassificationResult):
    """Result of document classification."""
    document_type: DocumentType
    inferred_department: str | None = None


class QueryClassificationResult(ClassificationResult):
    """Result of query classification."""
    intent: QueryIntent
    is_in_scope: bool = True
