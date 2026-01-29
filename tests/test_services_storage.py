import pytest
from app.services.storage_service import StorageService


def test_calculate_sha256():
    data = b"hello"
    digest = StorageService.calculate_sha256(data)
    assert isinstance(digest, str)
    assert len(digest) == 64


@pytest.mark.asyncio
async def test_presign_upload_or_multipart_small_file(monkeypatch):
    svc = StorageService()

    async def fake_generate_presigned_upload(self, bucket, key, content_type):
        return "https://example.com/presigned"

    monkeypatch.setattr(StorageService, "generate_presigned_upload", fake_generate_presigned_upload)

    url, upload_id, parts = await svc.presign_upload_or_multipart("bucket", "key", "text/plain", 1)
    assert url == "https://example.com/presigned"
    assert upload_id is None
    assert parts is None


@pytest.mark.asyncio
async def test_presign_upload_or_multipart_large_file(monkeypatch):
    svc = StorageService()

    async def fake_initiate(self, bucket, key, content_type):
        return "upload-1"

    async def fake_generate_parts(self, bucket, key, upload_id, size):
        return [(1, "url-1")]

    monkeypatch.setattr(StorageService, "initiate_multipart_upload", fake_initiate)
    monkeypatch.setattr(StorageService, "generate_presigned_part_urls", fake_generate_parts)

    # Use a size larger than the multipart threshold (100MB)
    url, upload_id, parts = await svc.presign_upload_or_multipart("bucket", "key", "text/plain", 200 * 1024 * 1024)
    assert url is None
    assert upload_id == "upload-1"
    assert parts == [(1, "url-1")]
