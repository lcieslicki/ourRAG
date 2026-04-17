from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.chunking.markdown import ChunkingConfig, DocumentChunk, MarkdownChunkingService
from app.domain.embeddings import EmbeddingMetadata, EmbeddingService
from app.domain.jobs import (
    CHUNK_DOCUMENT,
    EMBED_DOCUMENT,
    INGESTION_JOB_FLOW,
    INDEX_DOCUMENT,
    PARSE_DOCUMENT,
    REINDEX_DOCUMENT_VERSION,
)
from app.domain.models import DocumentProcessingJob, DocumentVersion
from app.domain.models.common import utc_now
from app.domain.parsers.markdown import MarkdownParser
from app.domain.services.processing_jobs import DocumentProcessingJobService
from app.infrastructure.embeddings import OllamaEmbeddingService
from app.infrastructure.storage.base import Storage
from app.infrastructure.storage.local import LocalFileStorage
from app.infrastructure.vector_index import QdrantVectorIndex, VectorPoint

JobHandler = Callable[[DocumentProcessingJob], None]


class IngestionJobRunner:
    def __init__(
        self,
        session: Session,
        handlers: dict[str, JobHandler] | None = None,
        *,
        storage: Storage | None = None,
        embedding_service: EmbeddingService | None = None,
        vector_index: QdrantVectorIndex | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.jobs = DocumentProcessingJobService(session)
        self.storage = storage
        self.embedding_service = embedding_service
        self.vector_index = vector_index
        self.settings = settings or get_settings()
        self.markdown_parser = MarkdownParser()
        self.handlers = self._default_handlers()
        if handlers:
            self.handlers.update(handlers)

    @classmethod
    def from_settings(cls, session: Session, settings: Settings | None = None) -> "IngestionJobRunner":
        resolved_settings = settings or get_settings()
        return cls(
            session,
            storage=LocalFileStorage(resolved_settings.storage.root),
            embedding_service=OllamaEmbeddingService.from_settings(resolved_settings),
            vector_index=QdrantVectorIndex.from_settings(resolved_settings),
            settings=resolved_settings,
        )

    def run_next(self) -> DocumentProcessingJob | None:
        job = self.jobs.next_queued()
        if job is None:
            return None
        return self.run(job.id)

    def run_until_idle(self, *, max_jobs: int = 100) -> list[DocumentProcessingJob]:
        processed: list[DocumentProcessingJob] = []

        for _ in range(max_jobs):
            job = self.run_next()
            if job is None:
                break
            processed.append(job)

        return processed

    def run(self, job_id: str) -> DocumentProcessingJob:
        job = self.jobs.get(job_id)
        if job.status == "succeeded":
            return job

        self.jobs.mark_running(job)
        try:
            self.handlers[job.job_type](job)
        except Exception as exc:
            self.jobs.mark_failed(job, error=exc)
            return job

        self.jobs.mark_succeeded(job)
        return job

    def _default_handlers(self) -> dict[str, JobHandler]:
        return {
            PARSE_DOCUMENT: self._handle_parse_document,
            CHUNK_DOCUMENT: self._handle_chunk_document,
            EMBED_DOCUMENT: self._handle_embed_document,
            INDEX_DOCUMENT: self._handle_index_document,
            REINDEX_DOCUMENT_VERSION: self._handle_reindex_document_version,
        }

    def _handle_parse_document(self, job: DocumentProcessingJob) -> None:
        version = self._version_for(job)
        if self.storage is None:
            if version.processing_status == "pending":
                version.processing_status = "processing"
            self.jobs.enqueue(document_version_id=version.id, job_type=CHUNK_DOCUMENT)
            return

        document = version.document
        parsed = self.markdown_parser.parse(self.storage.read_bytes(version.storage_path))
        parsed_path = self.storage.parsed_text_path(
            workspace_id=document.workspace_id,
            document_id=document.id,
            version_id=version.id,
        )
        self.storage.write_text(relative_path=parsed_path, content=parsed.normalized_text)
        version.parsed_text_path = parsed_path
        if version.processing_status == "pending":
            version.processing_status = "processing"
        self.jobs.enqueue(document_version_id=version.id, job_type=CHUNK_DOCUMENT)

    def _handle_chunk_document(self, job: DocumentProcessingJob) -> None:
        version = self._version_for(job)
        self._ensure_previous_stages_succeeded(job)
        if self.storage is None:
            version.processing_status = "processing"
            self.jobs.enqueue(document_version_id=version.id, job_type=EMBED_DOCUMENT)
            return

        document = version.document
        if not version.parsed_text_path:
            raise ValueError("Parsed text artifact is missing.")

        parsed = self.markdown_parser.parse(self.storage.read_text(version.parsed_text_path).encode("utf-8"))
        chunking_config = ChunkingConfig(
            chunk_size=self.settings.retrieval.chunk_size,
            chunk_overlap=self.settings.retrieval.chunk_overlap,
            strategy_version=self.settings.retrieval.chunking_strategy,
        )
        chunks = MarkdownChunkingService(chunking_config).chunk(
            parsed,
            workspace_id=document.workspace_id,
            document_version_id=version.id,
            language=version.language,
        )
        chunks_path = self.storage.chunks_path(
            workspace_id=document.workspace_id,
            document_id=document.id,
            version_id=version.id,
        )
        self.storage.write_json(relative_path=chunks_path, content=[serialize_chunk(chunk) for chunk in chunks])
        version.chunk_count = len(chunks)
        version.chunking_strategy_version = chunking_config.strategy_version
        version.processing_status = "processing"
        self.jobs.enqueue(document_version_id=version.id, job_type=EMBED_DOCUMENT)

    def _handle_embed_document(self, job: DocumentProcessingJob) -> None:
        version = self._version_for(job)
        self._ensure_previous_stages_succeeded(job)
        if self.storage is None or self.embedding_service is None:
            version.processing_status = "processing"
            self.jobs.enqueue(document_version_id=version.id, job_type=INDEX_DOCUMENT)
            return

        document = version.document
        chunks_path = self.storage.chunks_path(
            workspace_id=document.workspace_id,
            document_id=document.id,
            version_id=version.id,
        )
        chunks = [deserialize_chunk(raw) for raw in self.storage.read_json(chunks_path)]
        embedding_results = self.embedding_service.embed_chunks(chunks)
        embeddings_path = self.storage.embeddings_path(
            workspace_id=document.workspace_id,
            document_id=document.id,
            version_id=version.id,
        )
        self.storage.write_json(
            relative_path=embeddings_path,
            content=[
                {
                    "chunk": serialize_chunk(chunk),
                    "vector": result.vector,
                    "embedding": {
                        "provider": result.metadata.provider,
                        "model_name": result.metadata.model_name,
                        "model_version": result.metadata.model_version,
                        "dimensions": result.metadata.dimensions,
                    },
                }
                for chunk, result in zip(chunks, embedding_results, strict=True)
            ],
        )
        if embedding_results:
            version.embedding_model_name = embedding_results[0].metadata.model_name
            version.embedding_model_version = embedding_results[0].metadata.model_version
        version.processing_status = "processing"
        self.jobs.enqueue(document_version_id=version.id, job_type=INDEX_DOCUMENT)

    def _handle_index_document(self, job: DocumentProcessingJob) -> None:
        version = self._version_for(job)
        self._ensure_previous_stages_succeeded(job)
        if self.storage is not None and self.vector_index is not None:
            self._index_document_version(version)
        version.processing_status = "ready"
        version.indexed_at = utc_now()

    def _handle_reindex_document_version(self, job: DocumentProcessingJob) -> None:
        version = self._version_for(job)
        version.processing_status = "pending"
        version.indexed_at = None
        version.embedding_model_name = None
        version.embedding_model_version = None
        self.jobs.enqueue(document_version_id=version.id, job_type=PARSE_DOCUMENT, reuse_succeeded=False)

    def _index_document_version(self, version: DocumentVersion) -> None:
        document = version.document
        embeddings_path = self.storage.embeddings_path(
            workspace_id=document.workspace_id,
            document_id=document.id,
            version_id=version.id,
        )
        raw_embeddings = self.storage.read_json(embeddings_path)
        points = [vector_point_from_artifact(version=version, raw=raw) for raw in raw_embeddings]

        if points:
            self.vector_index.ensure_collection(vector_size=len(points[0].vector))
        self.vector_index.delete_document_version_vectors(
            workspace_id=document.workspace_id,
            document_version_id=version.id,
        )
        if not points:
            return

        self.vector_index.upsert_chunk_vectors(points)

    def _ensure_previous_stages_succeeded(self, job: DocumentProcessingJob) -> None:
        if job.job_type not in INGESTION_JOB_FLOW:
            return

        required_stages = INGESTION_JOB_FLOW[: INGESTION_JOB_FLOW.index(job.job_type)]
        for job_type in required_stages:
            if not self._has_succeeded_job(document_version_id=job.document_version_id, job_type=job_type):
                raise ValueError(f"Cannot run {job.job_type} before successful {job_type}.")

    def _has_succeeded_job(self, *, document_version_id: str, job_type: str) -> bool:
        return (
            self.session.query(DocumentProcessingJob)
            .filter_by(document_version_id=document_version_id, job_type=job_type, status="succeeded")
            .count()
            > 0
        )

    @staticmethod
    def _version_for(job: DocumentProcessingJob) -> DocumentVersion:
        version = job.document_version
        if version is None:
            raise ValueError("Document version not found for processing job.")
        if version.is_invalidated:
            raise ValueError("Invalidated document versions cannot be processed.")
        return version


def serialize_chunk(chunk: DocumentChunk) -> dict[str, Any]:
    return {
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
        "heading": chunk.heading,
        "section_path": list(chunk.section_path),
        "document_version_id": chunk.document_version_id,
        "workspace_id": chunk.workspace_id,
        "language": chunk.language,
        "chunking_strategy_version": chunk.chunking_strategy_version,
    }


def deserialize_chunk(raw: dict[str, Any]) -> DocumentChunk:
    return DocumentChunk(
        chunk_index=int(raw["chunk_index"]),
        text=str(raw["text"]),
        heading=raw["heading"],
        section_path=tuple(raw["section_path"]),
        document_version_id=str(raw["document_version_id"]),
        workspace_id=str(raw["workspace_id"]),
        language=str(raw["language"]),
        chunking_strategy_version=str(raw["chunking_strategy_version"]),
    )


def vector_point_from_artifact(*, version: DocumentVersion, raw: dict[str, Any]) -> VectorPoint:
    chunk = deserialize_chunk(raw["chunk"])
    embedding = raw["embedding"]
    document = version.document
    return VectorPoint(
        chunk_id=f"{version.id}:{chunk.chunk_index}",
        vector=[float(value) for value in raw["vector"]],
        workspace_id=document.workspace_id,
        document_id=document.id,
        document_version_id=version.id,
        chunk_index=chunk.chunk_index,
        text=chunk.text,
        title=document.title,
        category=document.category,
        tags=list(document.tags_json or []),
        section_path=list(chunk.section_path),
        language=chunk.language,
        is_active=version.is_active and not version.is_invalidated and document.status == "active",
        embedding=EmbeddingMetadata(
            provider=str(embedding["provider"]),
            model_name=str(embedding["model_name"]),
            model_version=str(embedding["model_version"]),
            dimensions=int(embedding["dimensions"]),
        ),
    )
