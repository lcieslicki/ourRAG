from dataclasses import dataclass
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
