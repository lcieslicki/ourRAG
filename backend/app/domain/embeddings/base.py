from dataclasses import dataclass
from typing import Protocol

from app.domain.chunking.markdown import DocumentChunk


@dataclass(frozen=True)
class EmbeddingMetadata:
    provider: str
    model_name: str
    model_version: str
    dimensions: int


@dataclass(frozen=True)
class EmbeddingInput:
    text: str
    metadata: dict


@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float]
    metadata: EmbeddingMetadata
    input_metadata: dict


class EmbeddingService(Protocol):
    def embed_texts(self, inputs: list[EmbeddingInput]) -> list[EmbeddingResult]:
        pass

    def embed_chunks(self, chunks: list[DocumentChunk]) -> list[EmbeddingResult]:
        pass

    def embed_query(self, query: str) -> EmbeddingResult:
        pass
