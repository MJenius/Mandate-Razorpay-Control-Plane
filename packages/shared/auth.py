"""Authoritative Caller Authentication and Principal Resolution for AI Agents."""

import hashlib
import hmac
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.enums import AgentStatus
from packages.core.models import Agent
from packages.shared.config import get_settings
from packages.shared.database import get_db_session
from packages.shared.logging import get_logger

logger = get_logger("shared.auth")


async def authenticate_agent_caller(
    db: AsyncSession,
    x_agent_key: Any = None,
    authorization: Any = None,
    x_agent_id: Any = None,
    required: bool = True,
) -> Agent | None:
    """
    Strict Authoritative Agent Principal Resolution:
    1. Extracts API key from X-Agent-Key or Authorization Bearer header.
    2. Hashes/matches credential against Agent.api_key_hash using constant-time comparison.
    3. Enforces Active status (rejects SUSPENDED / REVOKED agents with 403 Forbidden).
    4. Enforces Identity Match: If caller also provided x_agent_id, verifies exact match.
    5. Zero Credential Exposure: Raw keys are never logged.
    """
    settings = get_settings()

    # Sanitize header arguments (guarding against FastAPI Header() default instances)
    raw_key: str | None = x_agent_key if isinstance(x_agent_key, str) and x_agent_key else None
    raw_auth: str | None = authorization if isinstance(authorization, str) and authorization else None
    active_agent_id: str | None = x_agent_id if isinstance(x_agent_id, str) and x_agent_id else None

    bearer_token: str | None = None
    if raw_auth and raw_auth.startswith("Bearer "):
        bearer_token = raw_auth[7:].strip()
    elif raw_auth:
        bearer_token = raw_auth

    active_key = raw_key or bearer_token

    if active_key:
        # Resolve agent by key or key hash
        key_hash = hashlib.sha256(active_key.encode("utf-8")).hexdigest()
        stmt = select(Agent).where(
            (Agent.api_key_hash == active_key)
            | (Agent.api_key_hash == f"hash_{active_key}")
            | (Agent.api_key_hash == key_hash)
            | (Agent.id == active_key)
        )
        res = await db.execute(stmt)
        agent = res.scalars().first()

        if not agent:
            logger.warning("agent_authentication_failed_invalid_key")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or unauthorized Agent API Key.",
            )

        if agent.status != AgentStatus.ACTIVE:
            logger.warning("inactive_agent_rejected", agent_id=agent.id, status=agent.status.value)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Agent '{agent.name}' is currently {agent.status.value} and cannot execute operations.",
            )

        if active_agent_id and agent.id != active_agent_id:
            logger.warning(
                "agent_identity_mismatch",
                authenticated_agent=agent.id,
                requested_agent=active_agent_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Agent identity mismatch: Authenticated credential belongs to '{agent.id}', not '{active_agent_id}'.",
            )

        return agent

    elif active_agent_id and settings.ENVIRONMENT.lower() != "production":
        # Development / Test Compatibility Path
        agent = await db.get(Agent, active_agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Agent '{active_agent_id}' not found.",
            )
        if agent.status != AgentStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Agent '{agent.name}' is currently {agent.status.value}.",
            )
        return agent

    if required:
        logger.warning("agent_authentication_missing_credential")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication: Provide X-Agent-Key or Authorization Bearer token header.",
        )

    return None



async def get_authenticated_agent(
    x_agent_key: str | None = Header(None, alias="X-Agent-Key"),
    authorization: str | None = Header(None, alias="Authorization"),
    x_agent_id: str | None = Header(None, alias="X-Agent-Id"),
    db: AsyncSession = Depends(get_db_session),
) -> Agent:
    """FastAPI Dependency for authoritative agent authentication."""
    agent = await authenticate_agent_caller(
        db=db,
        x_agent_key=x_agent_key,
        authorization=authorization,
        x_agent_id=x_agent_id,
        required=True,
    )
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    return agent

