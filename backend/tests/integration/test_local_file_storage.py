from io import BytesIO

from starlette.datastructures import UploadFile

from app.infrastructure.storage.local import LocalFileStorage


def test_local_storage_saves_original_file_under_workspace_scope(tmp_path) -> None:
    storage = LocalFileStorage(tmp_path)
    relative_path = storage.original_file_path(
        workspace_id="workspace-1",
        document_id="document-1",
        version_id="version-1",
        file_name="policy.md",
    )

    stored = storage.save_upload(
        file=UploadFile(file=BytesIO(b"# Policy\n"), filename="policy.md"),
        relative_path=relative_path,
    )

    assert stored.relative_path == "workspaces/workspace-1/documents/document-1/versions/version-1/original/policy.md"
    assert stored.size_bytes == 9
    assert (tmp_path / stored.relative_path).read_bytes() == b"# Policy\n"
