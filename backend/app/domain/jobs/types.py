from typing import Literal

IngestionJobType = Literal[
    "parse_document",
    "chunk_document",
    "embed_document",
    "index_document",
    "reindex_document_version",
]

IngestionJobStatus = Literal["queued", "running", "succeeded", "failed"]

PARSE_DOCUMENT: IngestionJobType = "parse_document"
CHUNK_DOCUMENT: IngestionJobType = "chunk_document"
EMBED_DOCUMENT: IngestionJobType = "embed_document"
INDEX_DOCUMENT: IngestionJobType = "index_document"
REINDEX_DOCUMENT_VERSION: IngestionJobType = "reindex_document_version"

INGESTION_JOB_FLOW: tuple[IngestionJobType, ...] = (
    PARSE_DOCUMENT,
    CHUNK_DOCUMENT,
    EMBED_DOCUMENT,
    INDEX_DOCUMENT,
)

INGESTION_JOB_TYPES: tuple[IngestionJobType, ...] = (
    *INGESTION_JOB_FLOW,
    REINDEX_DOCUMENT_VERSION,
)

QUEUED: IngestionJobStatus = "queued"
RUNNING: IngestionJobStatus = "running"
SUCCEEDED: IngestionJobStatus = "succeeded"
FAILED: IngestionJobStatus = "failed"

ACTIVE_JOB_STATUSES: tuple[IngestionJobStatus, ...] = (QUEUED, RUNNING)
