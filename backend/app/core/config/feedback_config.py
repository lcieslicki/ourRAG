from pydantic import BaseModel, Field, PositiveInt


class FeedbackConfig(BaseModel):
    """Configuration for the feedback feature."""
    enabled: bool = Field(default=True, description="Enable feedback submission")
    ui_enabled: bool = Field(default=True, description="Enable feedback UI")
    comment_max_chars: PositiveInt = Field(default=1000, description="Maximum comment length")
