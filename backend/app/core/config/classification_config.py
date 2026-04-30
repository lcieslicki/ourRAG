from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClassificationSettings(BaseSettings):
    """Classification pipeline configuration loaded from environment variables."""

    classification_enabled: bool = Field(
        default=True,
        description="Enable classification pipeline globally.",
    )
    classification_document_enabled: bool = Field(
        default=True,
        description="Enable document classification.",
    )
    classification_query_enabled: bool = Field(
        default=True,
        description="Enable query classification.",
    )
    classification_min_confidence: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for accepting classifications.",
    )
    classification_provider: str = Field(
        default="rule_based",
        description="Classification provider strategy (e.g., 'rule_based').",
    )

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class ClassificationConfig(BaseModel):
    """Classification pipeline configuration with normalized short field names.

    Used internally in Settings model after env variable mapping.
    """

    enabled: bool = Field(default=False, description="Enable classification pipeline globally.")
    document_enabled: bool = Field(default=False, description="Enable document classification.")
    query_enabled: bool = Field(default=False, description="Enable query classification.")
    min_confidence: float = Field(default=0.65, ge=0.0, le=1.0, description="Minimum confidence threshold.")
    provider: str = Field(default="rule_based", description="Classification provider strategy.")
