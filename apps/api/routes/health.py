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
    """Postgres and Redis dependency readiness probe with strict database gate."""
    checks: dict[str, str] = {
        "database": "down",
        "redis": "down",
    }

    # Check Database connection (Mandatory for readiness)
    db_up = False
    try:
        session_maker = get_session_factory()
        async with session_maker() as session:
            await session.execute(text("SELECT 1"))
            checks["database"] = "up"
            db_up = True
    except Exception as e:
        checks["database"] = f"down: {str(e)}"
        db_up = False

    # Check Redis connection (Optional / Graceful degradation)
    redis_up = False
    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        checks["redis"] = "up"
        redis_up = True
    except Exception as e:
        checks["redis"] = f"down: {str(e)}"
        redis_up = False

    if not db_up:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "message": "PostgreSQL database is unavailable or uninitialized",
            "dependencies": checks,
        }

    overall_status = "ready" if redis_up else "degraded"
    return {
        "status": overall_status,
        "message": "Mandate control plane is fully operational"
        if redis_up
        else "Mandate core authorization is operational (Redis cache degraded)",
        "dependencies": checks,
    }

