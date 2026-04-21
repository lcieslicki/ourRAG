import pytest
from pydantic import ValidationError

from app.core.config.settings import EnvSettings


def test_env_settings_parses_comma_separated_cors_origins() -> None:
    settings = minimal_env_settings(
        app_cors_origins="http://localhost:5173, http://127.0.0.1:5173",
    ).to_settings()

    assert settings.app.cors_origins == ("http://localhost:5173", "http://127.0.0.1:5173")


def test_env_settings_rejects_invalid_cors_origin() -> None:
    with pytest.raises(ValidationError):
        minimal_env_settings(app_cors_origins="not-a-url")


def minimal_env_settings(**overrides):
    values = {
        "app_env": "test",
        "app_debug": True,
        "app_host": "0.0.0.0",
        "app_port": 8000,
        "app_log_level": "info",
        "postgres_host": "postgres",
        "postgres_port": 5432,
        "postgres_db": "ourrag",
        "postgres_user": "ourrag",
        "postgres_password": "secret",
        "qdrant_host": "qdrant",
        "qdrant_port": 6333,
        "qdrant_collection": "document_chunks",
        "qdrant_timeout": 10,
        "ollama_host": "ollama",
        "ollama_port": 11434,
        "ollama_model": "bielik",
        "ollama_timeout_seconds": 60,
        "ollama_keep_alive": "5m",
        "ollama_max_concurrency": 2,
        "embedding_provider": "ollama",
        "embedding_model": "nomic-embed-text",
        "embedding_timeout_seconds": 30,
        "files_storage_driver": "local",
        "files_storage_root": "/tmp/ourrag/storage",
        "queue_driver": "redis",
        "redis_host": "redis",
        "redis_port": 6379,
        "worker_concurrency": 2,
        "rag_top_k": 5,
        "rag_max_context_chunks": 5,
        "rag_chunk_size": 1200,
        "rag_chunk_overlap": 150,
        "rag_chunking_strategy": "markdown_semantic_v1",
        "chat_recent_messages_limit": 8,
        "chat_summary_enabled": True,
        "chat_summary_refresh_every_n_messages": 8,
    }
    values.update(overrides)
    return EnvSettings(**values)
