from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_unauthenticated_script_generation_fails(
    async_client: AsyncClient,
):
    payload = {
        "topic": "AI Tools Changing coding",
        "tone": "dramatic & engaging",
        "target_duration_seconds": 30,
    }
    response = await async_client.post(
        "/api/v1/scripts/generate", json=payload
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_script_generation(
    async_client: AsyncClient,
):
    # Register & Login
    user_data = {
        "email": "script_gen@viralcut.ai",
        "password": "Password123!",
    }
    await async_client.post("/api/v1/user/register", json=user_data)
    login_resp = await async_client.post(
        "/api/v1/user/login", json=user_data
    )
    token = login_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "topic": "5 Mind-Blowing Quantum Breakthroughs",
        "tone": "futuristic",
        "target_duration_seconds": 30,
    }
    response = await async_client.post(
        "/api/v1/scripts/generate", json=payload, headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "hook" in data
    assert "scenes" in data
    assert len(data["scenes"]) > 0
    assert data["scenes"][0]["scene_number"] == 1
