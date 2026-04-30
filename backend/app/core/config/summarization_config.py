from pydantic import PositiveInt
from pydantic_settings import BaseSettings


class SummarizationConfig(BaseSettings):
    """Configuration for summarization features."""

    enabled: bool = True
    max_source_chunks: PositiveInt = 12
    long_doc_map_reduce_enabled: bool = True
    timeout_ms: PositiveInt = 6000

    class Config:
        case_sensitive = False
        env_prefix = "SUMMARIZATION_"
