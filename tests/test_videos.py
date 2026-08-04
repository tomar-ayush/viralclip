from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_enqueue_video_render_and_poll_status(
    async_client: AsyncClient,
):
    # 1. Register and login user
    user_data = {
        "email": "render_user@viralcut.ai",
        "password": "Password123!",
    }
    await async_client.post("/api/v1/user/register", json=user_data)
    login_resp = await async_client.post(
        "/api/v1/user/login", json=user_data
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Mock script payload
    script_payload = {
        "hook": "Check this out!",
        "topic": "Quantum Computing",
        "tone": "dramatic",
        "total_estimated_duration": 30.0,
        "scenes": [
            {
                "scene_number": 1,
                "text": "Quantum computers are changing the future.",
                "visual_description": "Futuristic chip glowing with blue particle effects.",
                "duration_seconds": 6.0,
            }
        ],
    }

    render_request = {
        "script_json": script_payload,
        "background_asset_id": "gameplay_minecraft_01",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
    }

    # 3. Enqueue job
    render_resp = await async_client.post(
        "/api/v1/videos/render", json=render_request, headers=headers
    )
    assert render_resp.status_code == 202
    job_data = render_resp.json()
    assert "job_id" in job_data
    assert job_data["status"] == "QUEUED"

    job_id = job_data["job_id"]

    # 4. Poll status endpoint
    poll_resp = await async_client.get(f"/api/v1/videos/jobs/{job_id}")
    assert poll_resp.status_code == 200
    status_data = poll_resp.json()
    assert status_data["id"] == job_id
    assert "progress_percent" in status_data


@pytest.mark.asyncio
async def test_sse_progress_stream_endpoint(async_client: AsyncClient):
    fake_job_id = "00000000-0000-0000-0000-000000000001"
    response = await async_client.get(
        f"/api/v1/videos/jobs/{fake_job_id}/stream"
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get(
        "content-type", ""
    )
