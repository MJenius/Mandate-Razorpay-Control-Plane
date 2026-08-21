"""API Route Handlers for Health, Readiness, and Liveness checks."""

from typing import Any

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from packages.shared.database import get_session_factory
from packages.shared.redis import get_redis_client

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """Process liveness probe."""
    return {"status": "ok", "service": "mandate-api"}


@router.get("/ready")
async def readiness_check(response: Response) -> dict[str, Any]:
    """Postgres and Redis dependency readiness probe."""
    checks = {
        "database": "down",
        "redis": "down",
    }

    # Check Database connection
    try:
        session_maker = get_session_factory()
        async with session_maker() as session:
            await session.execute(text("SELECT 1"))
            checks["database"] = "up"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Check Redis connection
    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        checks["redis"] = "up"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"

    is_ready = checks["database"] == "up" and checks["redis"] == "up"
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "dependencies": checks,
    }
