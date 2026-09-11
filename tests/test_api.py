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


@pytest.mark.asyncio
async def test_cors_options_preflight_vercel(async_client: AsyncClient) -> None:
    """Verify OPTIONS preflight request for the public Vercel frontend succeeds."""
    response = await async_client.options(
        "/ready",
        headers={
            "Origin": "https://mandate-razorpay-control-plane.vercel.app",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin")
        == "https://mandate-razorpay-control-plane.vercel.app"
    )
    allow_methods = response.headers.get("access-control-allow-methods", "")
    for method in ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]:
        assert method in allow_methods
    allow_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "content-type" in allow_headers
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_options_preflight_localhost(async_client: AsyncClient) -> None:
    """Verify OPTIONS preflight request for localhost development succeeds."""
    response = await async_client.options(
        "/api/v1/agents",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-agent-id",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_options_preflight_disallowed_origin(async_client: AsyncClient) -> None:
    """Verify unauthorized origin receives 400 Disallowed CORS origin without allow-origin header."""
    response = await async_client.options(
        "/ready",
        headers={
            "Origin": "https://malicious-site.example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers

