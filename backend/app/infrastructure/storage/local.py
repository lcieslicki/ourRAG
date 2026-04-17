from pathlib import Path
from typing import Any
import hashlib
import json
import shutil

from fastapi import Depends, UploadFile

from app.core.config import Settings, get_settings
from app.infrastructure.storage.base import StoredFile


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def original_file_path(self, *, workspace_id: str, document_id: str, version_id: str, file_name: str) -> str:
        return str(
            Path("workspaces")
            / workspace_id
            / "documents"
            / document_id
            / "versions"
            / version_id
            / "original"
            / file_name
        )

    def parsed_text_path(self, *, workspace_id: str, document_id: str, version_id: str) -> str:
        return str(self._version_path(workspace_id=workspace_id, document_id=document_id, version_id=version_id) / "parsed" / "normalized.md")

    def chunks_path(self, *, workspace_id: str, document_id: str, version_id: str) -> str:
        return str(self._version_path(workspace_id=workspace_id, document_id=document_id, version_id=version_id) / "parsed" / "chunks.json")

    def embeddings_path(self, *, workspace_id: str, document_id: str, version_id: str) -> str:
        return str(self._version_path(workspace_id=workspace_id, document_id=document_id, version_id=version_id) / "parsed" / "embeddings.json")

    def save_upload(self, *, file: UploadFile, relative_path: str) -> StoredFile:
        target_path = self._resolve_relative_path(relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        digest = hashlib.sha256()
        size_bytes = 0

        file.file.seek(0)
        with target_path.open("wb") as target:
            while chunk := file.file.read(1024 * 1024):
                size_bytes += len(chunk)
                digest.update(chunk)
                target.write(chunk)

        file.file.seek(0)
        return StoredFile(relative_path=relative_path, checksum=digest.hexdigest(), size_bytes=size_bytes)

    def read_bytes(self, relative_path: str) -> bytes:
        return self._resolve_relative_path(relative_path).read_bytes()

    def write_text(self, *, relative_path: str, content: str) -> None:
        target_path = self._resolve_relative_path(relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")

    def read_text(self, relative_path: str) -> str:
        return self._resolve_relative_path(relative_path).read_text(encoding="utf-8")

    def write_json(self, *, relative_path: str, content: Any) -> None:
        self.write_text(relative_path=relative_path, content=json.dumps(content, ensure_ascii=False, sort_keys=True))

    def read_json(self, relative_path: str) -> Any:
        return json.loads(self.read_text(relative_path))

    def _resolve_relative_path(self, relative_path: str) -> Path:
        root = self.root.resolve()
        target = (root / relative_path).resolve()

        if root not in (target, *target.parents):
            raise ValueError("Storage path escapes configured root.")

        return target

    @staticmethod
    def _version_path(*, workspace_id: str, document_id: str, version_id: str) -> Path:
        return Path("workspaces") / workspace_id / "documents" / document_id / "versions" / version_id


def get_local_file_storage(settings: Settings = Depends(get_settings)) -> LocalFileStorage:
    return LocalFileStorage(settings.storage.root)
