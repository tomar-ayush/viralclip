from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_viral_trends_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/trends")
    assert response.status_code == 200
    data = response.json()
    assert "source" in data
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) > 0
    assert "title" in data["items"][0]


@pytest.mark.asyncio
async def test_get_viral_trends_with_geo_param(
    async_client: AsyncClient,
):
    response = await async_client.get("/api/v1/trends?geo=IN")
    assert response.status_code == 200
    data = response.json()
    assert data["items_count"] > 0
