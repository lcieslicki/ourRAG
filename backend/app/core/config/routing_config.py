from pydantic_settings import BaseSettings, SettingsConfigDict


class RoutingConfig(BaseSettings):
    """Configuration for routing and orchestration feature."""
    routing_enabled: bool = True
    routing_default_mode: str = "qa"
    routing_allow_ui_mode_hint: bool = True
    routing_min_confidence: float = 0.7

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file_encoding="utf-8",
        extra="ignore",
    )
