from collections.abc import Iterator

from app.domain.embeddings import EmbeddingService
from app.domain.services.retrieval import VectorIndexService
from app.infrastructure.embeddings import get_embedding_service
from app.infrastructure.vector_index import get_vector_index


def get_query_embedding_service() -> Iterator[EmbeddingService]:
    yield get_embedding_service()


def get_retrieval_vector_index() -> Iterator[VectorIndexService]:
    yield get_vector_index()
