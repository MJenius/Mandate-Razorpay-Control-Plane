"""Mandate management API routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from packages.core.enums import AuditAction, MandateStatus
from packages.core.models import Agent, AuditEvent, Mandate, Principal
from packages.core.schemas import MandateCreate, MandateResponse
from packages.shared.database import get_db_session
from packages.shared.logging import get_logger

logger = get_logger("api.mandates")
router = APIRouter(prefix="/mandates", tags=["Mandates"])


@router.get("", response_model=List[MandateResponse])
async def list_mandates(
    db: AsyncSession = Depends(get_db_session),
) -> List[Mandate]:
    """Retrieve all financial authorization mandates."""
    stmt = select(Mandate).order_by(Mandate.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=MandateResponse, status_code=status.HTTP_201_CREATED)
async def create_mandate(
    payload: MandateCreate,
    db: AsyncSession = Depends(get_db_session),
) -> Mandate:
    """Issue a bounded financial mandate to an AI agent."""
    import uuid

    # Validate agent and principal existence
    agent = await db.get(Agent, payload.agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{payload.agent_id}' not found",
        )

    principal = await db.get(Principal, payload.granted_by_id)
    if not principal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Principal '{payload.granted_by_id}' not found",
        )

    mandate = Mandate(
        agent_id=payload.agent_id,
        granted_by_id=payload.granted_by_id,
        status=MandateStatus.ACTIVE,
        currency=payload.currency,
        max_amount_per_op=payload.max_amount_per_op,
        aggregate_spend_limit=payload.aggregate_spend_limit,
        current_aggregate_spend=0,
        allowed_operations=[op.value for op in payload.allowed_operations],
        policy_config=payload.policy_config,
        valid_until=payload.valid_until,
    )
    db.add(mandate)
    await db.flush()

    audit_evt = AuditEvent(
        event_id=f"aud_{uuid.uuid4().hex[:16]}",
        action=AuditAction.MANDATE_ISSUED,
        actor_id=payload.granted_by_id,
        actor_type="PRINCIPAL",
        resource_id=mandate.id,
        resource_type="MANDATE",
        payload={
            "agent_id": mandate.agent_id,
            "aggregate_limit": mandate.aggregate_spend_limit,
            "max_per_op": mandate.max_amount_per_op,
        },
        new_state={"status": mandate.status.value},
    )
    db.add(audit_evt)
    await db.commit()
    await db.refresh(mandate)

    logger.info("mandate_created", mandate_id=mandate.id, agent_id=mandate.agent_id)
    return mandate
