from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_user_registration(async_client: AsyncClient):
    payload = {
        "email": "testuser@viralcut.ai",
        "password": "TestPassword123!",
    }
    response = await async_client.post(
        "/api/v1/user/register", json=payload
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_duplicate_user_registration_fails(
    async_client: AsyncClient,
):
    payload = {
        "email": "duplicate@viralcut.ai",
        "password": "TestPassword123!",
    }
    resp1 = await async_client.post(
        "/api/v1/user/register", json=payload
    )
    assert resp1.status_code == 201

    resp2 = await async_client.post(
        "/api/v1/user/register", json=payload
    )
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_user_login_and_token_generation(
    async_client: AsyncClient,
):
    reg_payload = {
        "email": "login_user@viralcut.ai",
        "password": "SecurePassword123!",
    }
    await async_client.post("/api/v1/user/register", json=reg_payload)

    login_payload = {
        "email": "login_user@viralcut.ai",
        "password": "SecurePassword123!",
    }
    response = await async_client.post(
        "/api/v1/user/login", json=login_payload
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["email"] == reg_payload["email"]


@pytest.mark.asyncio
async def test_get_authenticated_user_profile(
    async_client: AsyncClient,
):
    reg_payload = {
        "email": "profile_user@viralcut.ai",
        "password": "SecurePassword123!",
    }
    await async_client.post("/api/v1/user/register", json=reg_payload)

    login_resp = await async_client.post(
        "/api/v1/user/login", json=reg_payload
    )
    token = login_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    profile_resp = await async_client.get(
        "/api/v1/user/me", headers=headers
    )
    assert profile_resp.status_code == 200
    assert profile_resp.json()["email"] == reg_payload["email"]


@pytest.mark.asyncio
async def test_store_encrypted_byok_api_key(async_client: AsyncClient):
    reg_payload = {
        "email": "byok_user@viralcut.ai",
        "password": "SecurePassword123!",
    }
    await async_client.post("/api/v1/user/register", json=reg_payload)
    login_resp = await async_client.post(
        "/api/v1/user/login", json=reg_payload
    )
    token = login_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    key_payload = {
        "provider": "openai",
        "api_key": "sk-proj-9999888877776666",
    }
    response = await async_client.post(
        "/api/v1/user/keys", json=key_payload, headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["provider"] == "openai"
    assert "key_fingerprint" in data
    assert (
        "encrypted_key" not in data
    )  # Ensure encrypted key payload is not leaked
