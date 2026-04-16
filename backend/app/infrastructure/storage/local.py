from pathlib import Path
import hashlib
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

    def _resolve_relative_path(self, relative_path: str) -> Path:
        root = self.root.resolve()
        target = (root / relative_path).resolve()

        if root not in (target, *target.parents):
            raise ValueError("Storage path escapes configured root.")

        return target


def get_local_file_storage(settings: Settings = Depends(get_settings)) -> LocalFileStorage:
    return LocalFileStorage(settings.storage.root)
