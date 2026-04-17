from dataclasses import dataclass
from typing import Any
from typing import Protocol

from fastapi import UploadFile


@dataclass(frozen=True)
class StoredFile:
    relative_path: str
    checksum: str
    size_bytes: int


class Storage(Protocol):
    def original_file_path(self, *, workspace_id: str, document_id: str, version_id: str, file_name: str) -> str:
        pass

    def save_upload(self, *, file: UploadFile, relative_path: str) -> StoredFile:
        pass

    def parsed_text_path(self, *, workspace_id: str, document_id: str, version_id: str) -> str:
        pass

    def chunks_path(self, *, workspace_id: str, document_id: str, version_id: str) -> str:
        pass

    def embeddings_path(self, *, workspace_id: str, document_id: str, version_id: str) -> str:
        pass

    def read_bytes(self, relative_path: str) -> bytes:
        pass

    def write_text(self, *, relative_path: str, content: str) -> None:
        pass

    def read_text(self, relative_path: str) -> str:
        pass

    def write_json(self, *, relative_path: str, content: Any) -> None:
        pass

    def read_json(self, relative_path: str) -> Any:
        pass
