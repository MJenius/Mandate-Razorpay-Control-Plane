"""Mandate management API routes with full lifecycle controls."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from packages.core.enums import AuditAction, MandateStatus
from packages.core.models import Agent, AuditEvent, Mandate, Principal
from packages.core.schemas import MandateCreate, MandateResponse, MandateStatusUpdate
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


@router.get("/{mandate_id}", response_model=MandateResponse)
async def get_mandate(
    mandate_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Mandate:
    """Retrieve a single financial mandate by ID."""
    mandate = await db.get(Mandate, mandate_id)
    if not mandate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")
    return mandate


@router.post("", response_model=MandateResponse, status_code=status.HTTP_201_CREATED)
async def create_mandate(
    payload: MandateCreate,
    db: AsyncSession = Depends(get_db_session),
) -> Mandate:
    """Issue a bounded financial mandate to an AI agent."""
    from datetime import datetime, timezone

    agent = await db.get(Agent, payload.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent '{payload.agent_id}' not found")

    principal = await db.get(Principal, payload.granted_by_id)
    if not principal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Principal '{payload.granted_by_id}' not found")

    mandate = Mandate(
        agent_id=payload.agent_id,
        granted_by_id=payload.granted_by_id,
        status=MandateStatus.ACTIVE,
        currency=payload.currency.upper(),
        max_amount_per_op=payload.max_amount_per_op,
        aggregate_spend_limit=payload.aggregate_spend_limit,
        current_aggregate_spend=0,
        reserved_spend=0,
        review_threshold_amount=payload.review_threshold_amount,
        allowed_operations=[op.value for op in payload.allowed_operations],
        policy_config=payload.policy_config,
        valid_from=payload.valid_from or datetime.now(timezone.utc),
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
            "review_threshold": mandate.review_threshold_amount,
        },
        new_state={"status": mandate.status.value},
    )
    db.add(audit_evt)
    await db.commit()
    await db.refresh(mandate)

    logger.info("mandate_created", mandate_id=mandate.id, agent_id=mandate.agent_id)
    return mandate


@router.post("/{mandate_id}/suspend", response_model=MandateResponse)
async def suspend_mandate(
    mandate_id: str,
    update: MandateStatusUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> Mandate:
    """Temporarily suspends a mandate; prevents any further agent operations."""
    mandate = await db.get(Mandate, mandate_id)
    if not mandate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")

    old_status = mandate.status.value
    mandate.status = MandateStatus.SUSPENDED
    mandate.suspension_reason = update.reason or "Administrative suspension"
    mandate.version += 1

    audit_evt = AuditEvent(
        event_id=f"aud_{uuid.uuid4().hex[:16]}",
        action=AuditAction.MANDATE_SUSPENDED,
        actor_id="ADMIN",
        actor_type="PRINCIPAL",
        resource_id=mandate.id,
        resource_type="MANDATE",
        payload={"reason": mandate.suspension_reason},
        previous_state={"status": old_status},
        new_state={"status": mandate.status.value},
    )
    db.add(audit_evt)
    await db.commit()
    await db.refresh(mandate)
    return mandate


@router.post("/{mandate_id}/activate", response_model=MandateResponse)
async def activate_mandate(
    mandate_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Mandate:
    """Reactivates a previously suspended mandate."""
    mandate = await db.get(Mandate, mandate_id)
    if not mandate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")

    if mandate.status == MandateStatus.REVOKED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot activate a permanently revoked mandate")

    old_status = mandate.status.value
    mandate.status = MandateStatus.ACTIVE
    mandate.suspension_reason = None
    mandate.version += 1

    audit_evt = AuditEvent(
        event_id=f"aud_{uuid.uuid4().hex[:16]}",
        action=AuditAction.MANDATE_ACTIVATED,
        actor_id="ADMIN",
        actor_type="PRINCIPAL",
        resource_id=mandate.id,
        resource_type="MANDATE",
        payload={},
        previous_state={"status": old_status},
        new_state={"status": mandate.status.value},
    )
    db.add(audit_evt)
    await db.commit()
    await db.refresh(mandate)
    return mandate


@router.post("/{mandate_id}/revoke", response_model=MandateResponse)
async def revoke_mandate(
    mandate_id: str,
    update: MandateStatusUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> Mandate:
    """Permanently revokes a mandate; cannot be reactivated."""
    mandate = await db.get(Mandate, mandate_id)
    if not mandate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")

    old_status = mandate.status.value
    mandate.status = MandateStatus.REVOKED
    mandate.suspension_reason = update.reason or "Permanent revocation"
    mandate.version += 1

    audit_evt = AuditEvent(
        event_id=f"aud_{uuid.uuid4().hex[:16]}",
        action=AuditAction.MANDATE_REVOKED,
        actor_id="ADMIN",
        actor_type="PRINCIPAL",
        resource_id=mandate.id,
        resource_type="MANDATE",
        payload={"reason": mandate.suspension_reason},
        previous_state={"status": old_status},
        new_state={"status": mandate.status.value},
    )
    db.add(audit_evt)
    await db.commit()
    await db.refresh(mandate)
    return mandate
