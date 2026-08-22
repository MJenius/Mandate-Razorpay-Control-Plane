"""FastAPI main application entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.routes.agent_chat import router as agent_chat_router
from apps.api.routes.agents import router as agents_router
from apps.api.routes.audit import router as audit_router
from apps.api.routes.demo import router as demo_router
from apps.api.routes.evaluation import router as evaluation_router
from apps.api.routes.health import router as health_router
from apps.api.routes.mandates import router as mandates_router
from apps.api.routes.mcp_gateway import router as mcp_gateway_router
from apps.api.routes.operations import router as operations_router
from apps.api.routes.policies import router as policies_router
from apps.api.routes.telemetry import router as telemetry_router
from apps.api.routes.webhooks import router as webhooks_router
from packages.core.models import Base
from packages.shared.config import get_settings
from packages.shared.database import get_engine
from packages.shared.logging import get_logger, setup_logging

setup_logging()
logger = get_logger("api.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context for DB initialization and teardown."""
    logger.info("mandate_api_starting")

    # Auto-create tables and bootstrap default demo agents in development / test
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # Proactively bootstrap seed agents only if database is currently unseeded
        from sqlalchemy import func, select

        from apps.api.routes.demo import reset_demo_dataset
        from packages.core.models import Agent
        from packages.shared.database import get_session_factory

        session_factory = get_session_factory()
        async with session_factory() as session:
            agent_count = (await session.execute(select(func.count(Agent.id)))).scalar() or 0
            if agent_count == 0:
                await reset_demo_dataset(db=session)
                logger.info("database_demo_state_bootstrapped")
            else:
                logger.info("database_already_seeded", agent_count=agent_count)
    except Exception as exc:
        logger.warning("database_sync_deferred", reason=str(exc))

    yield
    logger.info("mandate_api_stopping")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Mandate API",
        description="Financial authorization and control plane for AI agents operating through Razorpay APIs & MCP",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handler (Structured RFC 7807 JSON)
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "type": "https://mandate.dev/errors/internal-server-error",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected error occurred processing the request.",
                "instance": request.url.path,
            },
        )

    # Mount Route Modules
    app.include_router(health_router)
    app.include_router(agents_router, prefix="/api/v1")
    app.include_router(agent_chat_router, prefix="/api/v1")
    app.include_router(mandates_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(operations_router, prefix="/api/v1")
    app.include_router(webhooks_router, prefix="/api/v1")
    app.include_router(telemetry_router, prefix="/api/v1")
    app.include_router(evaluation_router, prefix="/api/v1")
    app.include_router(policies_router, prefix="/api/v1")
    app.include_router(mcp_gateway_router, prefix="/api/v1")
    app.include_router(demo_router, prefix="/api/v1")

    return app


app = create_app()
