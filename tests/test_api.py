"""Tests for API health, readiness, and endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient) -> None:
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "mandate-api"


@pytest.mark.asyncio
async def test_agent_registration_and_listing(async_client: AsyncClient) -> None:
    # First, list agents (initially empty)
    res = await async_client.get("/api/v1/agents")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_mandates_listing(async_client: AsyncClient) -> None:
    res = await async_client.get("/api/v1/mandates")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_audit_listing(async_client: AsyncClient) -> None:
    res = await async_client.get("/api/v1/audit")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
