from __future__ import annotations

import pytest

from app.storage.service import storage_service


@pytest.mark.asyncio
async def test_r2_storage_upload_bytes():
    dummy_bytes = b"mock mp3 audio bytes content"
    r2_key = "test_audio/voice.mp3"

    url = await storage_service.upload_bytes(
        file_bytes=dummy_bytes, r2_key=r2_key, content_type="audio/mpeg"
    )
    assert url is not None
    assert "test_audio/voice.mp3" in url


@pytest.mark.asyncio
async def test_r2_storage_generate_presigned_url():
    r2_key = "test_renders/sample.mp4"
    presigned_url = await storage_service.generate_presigned_url(
        r2_key=r2_key, expiration_seconds=1800
    )

    assert presigned_url is not None
    assert "test_renders/sample.mp4" in presigned_url
