from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExtractionConfig(BaseSettings):
    """Configuration for structured extraction."""

    extraction_enabled: bool = Field(default=True, description="Enable extraction feature")
    extraction_max_schema_fields: PositiveInt = Field(
        default=30, description="Maximum number of fields allowed in a schema"
    )
    extraction_validation_strict: bool = Field(
        default=True, description="Enforce strict schema validation"
    )
    extraction_timeout_ms: PositiveInt = Field(default=5000, description="Timeout for extraction in milliseconds")

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file_encoding="utf-8",
        extra="ignore",
    )
