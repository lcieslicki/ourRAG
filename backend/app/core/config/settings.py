import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, BaseModel, Field, PositiveInt, StringConstraints, TypeAdapter, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AppConfig(BaseModel):
    env: Literal["local", "docker", "test", "production"]
    debug: bool
    host: NonEmptyStr
    port: int = Field(ge=1, le=65535)
    log_level: Literal["debug", "info", "warning", "error", "critical"]
    cors_origins: tuple[str, ...]


class PostgresConfig(BaseModel):
    host: NonEmptyStr
    port: int = Field(ge=1, le=65535)
    db: NonEmptyStr
    user: NonEmptyStr
    password: NonEmptyStr


class QdrantConfig(BaseModel):
    host: NonEmptyStr
    port: int = Field(ge=1, le=65535)
    collection: NonEmptyStr
    timeout: PositiveInt


class OllamaConfig(BaseModel):
    host: NonEmptyStr
    port: int = Field(ge=1, le=65535)
    model: NonEmptyStr
    timeout_seconds: PositiveInt
    keep_alive: NonEmptyStr
    max_concurrency: PositiveInt


class EmbeddingsConfig(BaseModel):
    provider: Literal["ollama"]
    model: NonEmptyStr
    timeout_seconds: PositiveInt


class StorageConfig(BaseModel):
    driver: Literal["local"]
    root: Path


class QueueConfig(BaseModel):
    driver: Literal["redis"]
    redis_host: NonEmptyStr
    redis_port: int = Field(ge=1, le=65535)
    worker_concurrency: PositiveInt


class RetrievalConfig(BaseModel):
    top_k: PositiveInt
    max_context_chunks: PositiveInt
    min_score_threshold: float | None
    chunk_size: PositiveInt
    chunk_overlap: int = Field(ge=0)
    chunking_strategy: NonEmptyStr

    @model_validator(mode="after")
    def validate_chunk_overlap(self) -> "RetrievalConfig":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("RAG_CHUNK_OVERLAP must be smaller than RAG_CHUNK_SIZE")
        return self

    @field_validator("min_score_threshold")
    @classmethod
    def validate_score_threshold(cls, value: float | None) -> float | None:
        if value is not None and not 0 <= value <= 1:
            raise ValueError("RAG_MIN_SCORE_THRESHOLD must be between 0 and 1")
        return value


class ChatMemoryConfig(BaseModel):
    recent_messages_limit: PositiveInt
    summary_enabled: bool
    summary_refresh_every_n_messages: PositiveInt


class CitationConfig(BaseModel):
    max_exposed_citations: PositiveInt
    excerpt_max_chars: PositiveInt
    include_retrieved_sources: bool
    include_cited_sources: bool
    transition_include_legacy_sources: bool


class GuardrailsConfig(BaseModel):
    enabled: bool
    in_scope_required: bool
    min_top_score: float
    min_usable_chunks: PositiveInt
    use_template_responses: bool


class HybridRetrievalConfig(BaseModel):
    mode: str  # "vector_only" | "hybrid"
    semantic_top_k: PositiveInt
    lexical_top_k: PositiveInt
    final_top_k: PositiveInt
    semantic_weight: float
    lexical_weight: float


class RerankingConfig(BaseModel):
    enabled: bool
    provider: str
    top_k_candidates: PositiveInt
    final_top_k: PositiveInt
    timeout_ms: PositiveInt
    fail_open: bool


class ObservabilityConfig(BaseModel):
    json_logs: bool
    chat_trace_enabled: bool
    retrieval_trace_enabled: bool
    ingestion_trace_enabled: bool
    include_debug_fields: bool


class Settings(BaseModel):
    app: AppConfig
    postgres: PostgresConfig
    qdrant: QdrantConfig
    ollama: OllamaConfig
    embeddings: EmbeddingsConfig
    storage: StorageConfig
    queue: QueueConfig
    retrieval: RetrievalConfig
    chat_memory: ChatMemoryConfig
    citations: CitationConfig
    guardrails: GuardrailsConfig
    hybrid_retrieval: HybridRetrievalConfig
    reranking: RerankingConfig
    observability: ObservabilityConfig
    data_root: Path


class EnvSettings(BaseSettings):
    app_env: Literal["local", "docker", "test", "production"]
    app_debug: bool
    app_host: NonEmptyStr
    app_port: int
    app_log_level: Literal["debug", "info", "warning", "error", "critical"]
    app_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    postgres_host: NonEmptyStr
    postgres_port: int
    postgres_db: NonEmptyStr
    postgres_user: NonEmptyStr
    postgres_password: NonEmptyStr

    qdrant_host: NonEmptyStr
    qdrant_port: int
    qdrant_collection: NonEmptyStr
    qdrant_timeout: PositiveInt

    ollama_host: NonEmptyStr
    ollama_port: int
    ollama_model: NonEmptyStr
    ollama_timeout_seconds: PositiveInt
    ollama_keep_alive: NonEmptyStr
    ollama_max_concurrency: PositiveInt

    embedding_provider: Literal["ollama"]
    embedding_model: NonEmptyStr
    embedding_timeout_seconds: PositiveInt

    files_storage_driver: Literal["local"]
    files_storage_root: Path

    queue_driver: Literal["redis"]
    redis_host: NonEmptyStr
    redis_port: int
    worker_concurrency: PositiveInt

    rag_top_k: PositiveInt
    rag_max_context_chunks: PositiveInt
    rag_min_score_threshold: float | None = None
    rag_chunk_size: PositiveInt
    rag_chunk_overlap: int = Field(ge=0)
    rag_chunking_strategy: NonEmptyStr

    chat_recent_messages_limit: PositiveInt
    chat_summary_enabled: bool
    chat_summary_refresh_every_n_messages: PositiveInt

    # Citations
    chat_max_exposed_citations: PositiveInt = Field(default=3)
    chat_citation_excerpt_max_chars: PositiveInt = Field(default=300)
    chat_include_retrieved_sources: bool = Field(default=True)
    chat_include_cited_sources: bool = Field(default=True)
    chat_citation_transition_include_legacy_sources: bool = Field(default=True)

    # Guardrails
    guardrails_enabled: bool = Field(default=True)
    guardrails_in_scope_required: bool = Field(default=True)
    guardrails_min_top_score: float = Field(default=0.72)
    guardrails_min_usable_chunks: PositiveInt = Field(default=2)
    guardrails_use_template_responses: bool = Field(default=True)

    # Hybrid retrieval
    retrieval_mode: str = Field(default="vector_only")
    retrieval_hybrid_semantic_top_k: PositiveInt = Field(default=20)
    retrieval_hybrid_lexical_top_k: PositiveInt = Field(default=20)
    retrieval_hybrid_final_top_k: PositiveInt = Field(default=12)
    retrieval_hybrid_semantic_weight: float = Field(default=0.65)
    retrieval_hybrid_lexical_weight: float = Field(default=0.35)

    # Reranking
    reranking_enabled: bool = Field(default=False)
    reranking_provider: str = Field(default="local_cross_encoder")
    reranking_top_k_candidates: PositiveInt = Field(default=20)
    reranking_final_top_k: PositiveInt = Field(default=6)
    reranking_timeout_ms: PositiveInt = Field(default=800)
    reranking_fail_open: bool = Field(default=True)

    # Observability
    observability_json_logs: bool = Field(default=True)
    observability_chat_trace_enabled: bool = Field(default=True)
    observability_retrieval_trace_enabled: bool = Field(default=True)
    observability_ingestion_trace_enabled: bool = Field(default=True)
    observability_include_debug_fields: bool = Field(default=False)

    data_root: Path | None = Field(default=None)

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def set_data_root_default(self) -> "EnvSettings":
        if self.data_root is None:
            # Derive from FILES_STORAGE_ROOT, for example: /app/data/storage -> /app/data.
            self.data_root = self.files_storage_root.parent
        return self

    @field_validator("rag_min_score_threshold", mode="before")
    @classmethod
    def empty_score_threshold_as_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("app_cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not origins:
            raise ValueError("APP_CORS_ORIGINS must include at least one origin")
        adapter = TypeAdapter(AnyHttpUrl)
        for origin in origins:
            adapter.validate_python(origin)
        return ",".join(origins)

    def to_settings(self) -> Settings:
        return Settings(
            app=AppConfig(
                env=self.app_env,
                debug=self.app_debug,
                host=self.app_host,
                port=self.app_port,
                log_level=self.app_log_level,
                cors_origins=tuple(self.app_cors_origins.split(",")),
            ),
            postgres=PostgresConfig(
                host=self.postgres_host,
                port=self.postgres_port,
                db=self.postgres_db,
                user=self.postgres_user,
                password=self.postgres_password,
            ),
            qdrant=QdrantConfig(
                host=self.qdrant_host,
                port=self.qdrant_port,
                collection=self.qdrant_collection,
                timeout=self.qdrant_timeout,
            ),
            ollama=OllamaConfig(
                host=self.ollama_host,
                port=self.ollama_port,
                model=self.ollama_model,
                timeout_seconds=self.ollama_timeout_seconds,
                keep_alive=self.ollama_keep_alive,
                max_concurrency=self.ollama_max_concurrency,
            ),
            embeddings=EmbeddingsConfig(
                provider=self.embedding_provider,
                model=self.embedding_model,
                timeout_seconds=self.embedding_timeout_seconds,
            ),
            storage=StorageConfig(
                driver=self.files_storage_driver,
                root=self.files_storage_root,
            ),
            queue=QueueConfig(
                driver=self.queue_driver,
                redis_host=self.redis_host,
                redis_port=self.redis_port,
                worker_concurrency=self.worker_concurrency,
            ),
            retrieval=RetrievalConfig(
                top_k=self.rag_top_k,
                max_context_chunks=self.rag_max_context_chunks,
                min_score_threshold=self.rag_min_score_threshold,
                chunk_size=self.rag_chunk_size,
                chunk_overlap=self.rag_chunk_overlap,
                chunking_strategy=self.rag_chunking_strategy,
            ),
            chat_memory=ChatMemoryConfig(
                recent_messages_limit=self.chat_recent_messages_limit,
                summary_enabled=self.chat_summary_enabled,
                summary_refresh_every_n_messages=self.chat_summary_refresh_every_n_messages,
            ),
            citations=CitationConfig(
                max_exposed_citations=self.chat_max_exposed_citations,
                excerpt_max_chars=self.chat_citation_excerpt_max_chars,
                include_retrieved_sources=self.chat_include_retrieved_sources,
                include_cited_sources=self.chat_include_cited_sources,
                transition_include_legacy_sources=self.chat_citation_transition_include_legacy_sources,
            ),
            guardrails=GuardrailsConfig(
                enabled=self.guardrails_enabled,
                in_scope_required=self.guardrails_in_scope_required,
                min_top_score=self.guardrails_min_top_score,
                min_usable_chunks=self.guardrails_min_usable_chunks,
                use_template_responses=self.guardrails_use_template_responses,
            ),
            hybrid_retrieval=HybridRetrievalConfig(
                mode=self.retrieval_mode,
                semantic_top_k=self.retrieval_hybrid_semantic_top_k,
                lexical_top_k=self.retrieval_hybrid_lexical_top_k,
                final_top_k=self.retrieval_hybrid_final_top_k,
                semantic_weight=self.retrieval_hybrid_semantic_weight,
                lexical_weight=self.retrieval_hybrid_lexical_weight,
            ),
            reranking=RerankingConfig(
                enabled=self.reranking_enabled,
                provider=self.reranking_provider,
                top_k_candidates=self.reranking_top_k_candidates,
                final_top_k=self.reranking_final_top_k,
                timeout_ms=self.reranking_timeout_ms,
                fail_open=self.reranking_fail_open,
            ),
            observability=ObservabilityConfig(
                json_logs=self.observability_json_logs,
                chat_trace_enabled=self.observability_chat_trace_enabled,
                retrieval_trace_enabled=self.observability_retrieval_trace_enabled,
                ingestion_trace_enabled=self.observability_ingestion_trace_enabled,
                include_debug_fields=self.observability_include_debug_fields,
            ),
            data_root=self.data_root or find_env_root() / "data",
        )


@lru_cache
def get_settings() -> Settings:
    return EnvSettings(_env_file=env_files()).to_settings()


def env_files() -> tuple[str, ...]:
    env_root = find_env_root()
    base_env = env_root / ".env"
    app_env = os.environ.get("APP_ENV") or read_app_env_from_file(base_env) or "local"
    return (str(base_env), str(env_root / f".env.{app_env}"))


def find_env_root() -> Path:
    for path in (Path.cwd(), *Path.cwd().parents):
        if (path / ".env").exists() or (path / ".env.example").exists():
            return path

    return Path.cwd()


def read_app_env_from_file(path: Path) -> str | None:
    if not path.exists():
        return None

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()

        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)

        if key.strip() == "APP_ENV":
            return value.strip().strip("\"'")

    return None
