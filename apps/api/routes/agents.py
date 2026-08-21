"""Agent management API routes with suspension and status controls."""

import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.enums import AgentStatus, AuditAction
from packages.core.models import Agent, AuditEvent, Principal
from packages.core.schemas import AgentCreate, AgentResponse, AgentStatusUpdate
from packages.shared.database import get_db_session
from packages.shared.logging import get_logger

logger = get_logger("api.agents")
router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    db: AsyncSession = Depends(get_db_session),
) -> list[Agent]:
    """Retrieve all registered AI agents."""
    stmt = select(Agent).order_by(Agent.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Agent:
    """Retrieve an AI agent by ID."""
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(
    payload: AgentCreate,
    db: AsyncSession = Depends(get_db_session),
) -> Agent:
    """Register a new AI Agent bound to a principal owner."""
    principal = await db.get(Principal, payload.owner_id)
    if not principal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Principal owner '{payload.owner_id}' not found",
        )

    raw_api_key = f"ag_key_{uuid.uuid4().hex}"
    api_key_hash = hashlib.sha256(raw_api_key.encode()).hexdigest()

    agent = Agent(
        name=payload.name,
        description=payload.description,
        owner_id=payload.owner_id,
        status=AgentStatus.ACTIVE,
        api_key_hash=api_key_hash,
        metadata_json=payload.metadata_json,
    )
    db.add(agent)
    await db.flush()

    audit_evt = AuditEvent(
        event_id=f"aud_{uuid.uuid4().hex[:16]}",
        action=AuditAction.AGENT_REGISTERED,
        actor_id=payload.owner_id,
        actor_type="PRINCIPAL",
        resource_id=agent.id,
        resource_type="AGENT",
        payload={"agent_name": agent.name},
        new_state={"status": agent.status.value},
    )
    db.add(audit_evt)
    await db.commit()
    await db.refresh(agent)

    logger.info("agent_registered", agent_id=agent.id, name=agent.name)
    return agent


@router.post("/{agent_id}/status", response_model=AgentResponse)
async def update_agent_status(
    agent_id: str,
    update: AgentStatusUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> Agent:
    """Update agent status (e.g. SUSPENDED or REVOKED)."""
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    old_status = agent.status.value
    agent.status = update.status

    audit_evt = AuditEvent(
        event_id=f"aud_{uuid.uuid4().hex[:16]}",
        action=AuditAction.AGENT_STATUS_CHANGED,
        actor_id="ADMIN",
        actor_type="PRINCIPAL",
        resource_id=agent.id,
        resource_type="AGENT",
        payload={"reason": update.reason or ""},
        previous_state={"status": old_status},
        new_state={"status": agent.status.value},
    )
    db.add(audit_evt)
    await db.commit()
    await db.refresh(agent)
    return agent
