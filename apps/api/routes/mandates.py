"""Hierarchical Mandate Lifecycle and Delegation API routes."""

import uuid
from datetime import UTC
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.enums import AuditAction, MandateStatus
from packages.core.models import Agent, AuditEvent, Mandate
from packages.core.schemas import (
    MandateCreate,
    MandateDelegateRequest,
    MandateResponse,
    MandateStatusUpdate,
)
from packages.shared.database import get_db_session
from packages.shared.logging import get_logger

logger = get_logger("api.mandates")
router = APIRouter(prefix="/mandates", tags=["Mandates & Delegation"])


@router.post("", response_model=MandateResponse, status_code=status.HTTP_201_CREATED)
async def create_mandate(
    payload: MandateCreate,
    db: AsyncSession = Depends(get_db_session),
) -> Mandate:
    """Issue a root financial mandate for an agent."""
    # 1. Resolve Agent by ID, Name, Substring, or extracted ID
    import re
    cleaned_id = payload.agent_id.strip()
    extracted_match = re.search(r"(agt_[a-zA-Z0-9_]+)", cleaned_id)
    target_lookup = extracted_match.group(1) if extracted_match else cleaned_id

    agent = await db.get(Agent, target_lookup)
    if not agent:
        name_stmt = select(Agent).where(
            (Agent.name.ilike(f"%{target_lookup}%"))
            | (Agent.id.ilike(f"%{target_lookup}%"))
            | (Agent.agent_type.ilike(f"%{target_lookup}%"))
        )
        agent = (await db.execute(name_stmt)).scalar_one_or_none()

    if not agent:
        existing = (await db.execute(select(Agent.name, Agent.id))).all()
        existing_names = [f"'{row[0]}' ({row[1]})" for row in existing]
        avail_str = ", ".join(existing_names) if existing_names else "None"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{payload.agent_id}' not found. Available agents: {avail_str}. Please select an existing agent or create one on the Agents page.",
        )

    mandate = Mandate(
        agent_id=agent.id,
        granted_by_id=payload.granted_by_id,
        status=MandateStatus.ACTIVE,
        currency=payload.currency.upper(),
        max_amount_per_op=payload.max_amount_per_op,
        aggregate_spend_limit=payload.aggregate_spend_limit,
        review_threshold_amount=payload.review_threshold_amount,
        allowed_operations=payload.allowed_operations,
        policy_config=payload.policy_config,
        valid_until=payload.valid_until,
    )
    db.add(mandate)
    await db.flush()

    audit_evt = AuditEvent(
        event_id=f"aud_{uuid.uuid4().hex[:16]}",
        action=AuditAction.MANDATE_CREATED,
        actor_id=payload.granted_by_id,
        actor_type="PRINCIPAL",
        resource_id=mandate.id,
        resource_type="MANDATE",
        payload={
            "agent_id": mandate.agent_id,
            "currency": mandate.currency,
            "max_amount_per_op": mandate.max_amount_per_op,
            "aggregate_spend_limit": mandate.aggregate_spend_limit,
        },
        new_state={"status": mandate.status.value},
    )
    db.add(audit_evt)
    await db.commit()
    await db.refresh(mandate)
    return mandate


def _validate_delegation_invariants(parent: Mandate, payload: MandateDelegateRequest) -> str:
    """Validates mathematical non-escalation invariants for child mandate delegation."""
    if parent.delegation_depth >= parent.max_delegation_depth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Max delegation depth ({parent.max_delegation_depth}) reached for this mandate tree",
        )

    child_currency = (payload.currency or parent.currency).upper()
    if child_currency != parent.currency.upper():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Privilege escalation: Child currency '{child_currency}' does not match parent bound '{parent.currency}'",
        )

    if payload.max_amount_per_op > parent.max_amount_per_op:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Privilege escalation: Requested max_amount_per_op ({payload.max_amount_per_op}) exceeds parent ceiling ({parent.max_amount_per_op})",
        )

    if parent.allowed_operations:
        for op_type in payload.allowed_operations:
            if op_type not in parent.allowed_operations:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Privilege escalation: Operation '{op_type}' is not authorized in parent mandate whitelist",
                )

    parent_until = (
        parent.valid_until if parent.valid_until.tzinfo else parent.valid_until.replace(tzinfo=UTC)
    )
    child_until = (
        payload.valid_until
        if payload.valid_until.tzinfo
        else payload.valid_until.replace(tzinfo=UTC)
    )
    if child_until > parent_until:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Privilege escalation: Child validity ({child_until.isoformat()}) exceeds parent expiration ({parent_until.isoformat()})",
        )

    parent_available = max(
        0,
        parent.aggregate_spend_limit
        - (
            parent.current_aggregate_spend
            + parent.reserved_spend
            + parent.delegated_child_budget_allocated
        ),
    )
    if payload.aggregate_spend_limit > parent_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Privilege escalation: Requested aggregate limit ({payload.aggregate_spend_limit}) exceeds parent remaining unallocated budget ({parent_available})",
        )

    return child_currency


@router.post(
    "/{parent_id}/delegate", response_model=MandateResponse, status_code=status.HTTP_201_CREATED
)
async def delegate_child_mandate(
    parent_id: str,
    payload: MandateDelegateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Mandate:
    """Delegates a bounded sub-mandate from parent -> child agent with strict non-escalation invariants."""
    parent_stmt = select(Mandate).where(Mandate.id == parent_id).with_for_update()
    parent_res = await db.execute(parent_stmt)
    parent = parent_res.scalar_one_or_none()
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Parent mandate not found"
        )

    if parent.status != MandateStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delegate from parent mandate in status '{parent.status.value}'",
        )

    target_agent = await db.get(Agent, payload.target_agent_id)
    if not target_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Target child agent not found"
        )

    child_currency = _validate_delegation_invariants(parent, payload)

    # Atomically reserve budget from parent for this child delegation tree
    parent.delegated_child_budget_allocated += payload.aggregate_spend_limit
    parent.version += 1

    child_mandate = Mandate(
        agent_id=payload.target_agent_id,
        granted_by_id=parent.granted_by_id,
        parent_mandate_id=parent.id,
        delegation_depth=parent.delegation_depth + 1,
        max_delegation_depth=parent.max_delegation_depth,
        status=MandateStatus.ACTIVE,
        currency=child_currency,
        max_amount_per_op=payload.max_amount_per_op,
        aggregate_spend_limit=payload.aggregate_spend_limit,
        review_threshold_amount=payload.review_threshold_amount or parent.review_threshold_amount,
        allowed_operations=payload.allowed_operations or parent.allowed_operations,
        policy_config=parent.policy_config,
        valid_until=payload.valid_until,
    )
    db.add(child_mandate)
    await db.flush()

    audit_evt = AuditEvent(
        event_id=f"aud_{uuid.uuid4().hex[:16]}",
        action=AuditAction.MANDATE_CREATED,
        actor_id=parent.agent_id,
        actor_type="AGENT",
        resource_id=child_mandate.id,
        resource_type="MANDATE",
        payload={
            "parent_mandate_id": parent.id,
            "target_agent_id": payload.target_agent_id,
            "delegation_depth": child_mandate.delegation_depth,
            "allocated_budget": child_mandate.aggregate_spend_limit,
        },
        new_state={"status": child_mandate.status.value},
    )
    db.add(audit_evt)
    await db.commit()
    await db.refresh(child_mandate)
    return child_mandate


@router.get("", response_model=list[MandateResponse])
async def list_mandates(
    agent_id: str | None = None,
    status_filter: MandateStatus | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[Mandate]:
    """List financial mandates."""
    stmt = select(Mandate).order_by(Mandate.created_at.desc())
    if agent_id:
        stmt = stmt.where(Mandate.agent_id == agent_id)
    if status_filter:
        stmt = stmt.where(Mandate.status == status_filter)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{mandate_id}", response_model=MandateResponse)
async def get_mandate(
    mandate_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Mandate:
    """Retrieve mandate details by ID."""
    mandate = await db.get(Mandate, mandate_id)
    if not mandate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")
    return mandate


@router.post("/{mandate_id}/suspend", response_model=MandateResponse)
async def suspend_mandate_cascade(
    mandate_id: str,
    payload: MandateStatusUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> Mandate:
    """Suspends mandate and immediately cascades suspension to all child mandates in the tree."""
    mandate = await db.get(Mandate, mandate_id)
    if not mandate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")

    await _cascade_mandate_status(
        db=db,
        root_mandate_id=mandate.id,
        target_status=MandateStatus.SUSPENDED,
        reason=payload.reason or "Parent mandate suspended",
    )
    await db.commit()
    await db.refresh(mandate)
    return mandate


@router.post("/{mandate_id}/activate", response_model=MandateResponse)
async def activate_mandate(
    mandate_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Mandate:
    """Reactivates a suspended mandate."""
    mandate = await db.get(Mandate, mandate_id)
    if not mandate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")

    if mandate.parent_mandate_id:
        parent = await db.get(Mandate, mandate.parent_mandate_id)
        if parent and parent.status != MandateStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot activate child mandate while parent mandate is suspended or revoked",
            )

    mandate.status = MandateStatus.ACTIVE
    mandate.suspension_reason = None
    mandate.version += 1
    await db.commit()
    await db.refresh(mandate)
    return mandate


@router.post("/{mandate_id}/revoke", response_model=MandateResponse)
async def revoke_mandate_cascade(
    mandate_id: str,
    payload: MandateStatusUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> Mandate:
    """Permanently revokes mandate and immediately cascades revocation down all child mandates."""
    mandate = await db.get(Mandate, mandate_id)
    if not mandate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")

    await _cascade_mandate_status(
        db=db,
        root_mandate_id=mandate.id,
        target_status=MandateStatus.REVOKED,
        reason=payload.reason or "Parent mandate permanently revoked",
    )
    await db.commit()
    await db.refresh(mandate)
    return mandate


async def _cascade_mandate_status(
    db: AsyncSession,
    root_mandate_id: str,
    target_status: MandateStatus,
    reason: str,
) -> None:
    """Recursively updates all descendant child mandates down the tree."""
    visited = set()
    queue = [root_mandate_id]

    while queue:
        curr_id = queue.pop(0)
        visited.add(curr_id)

        m = await db.get(Mandate, curr_id)
        if m:
            m.status = target_status
            m.suspension_reason = reason
            m.version += 1

            audit = AuditEvent(
                event_id=f"aud_{uuid.uuid4().hex[:16]}",
                action=AuditAction.MANDATE_REVOKED
                if target_status == MandateStatus.REVOKED
                else AuditAction.MANDATE_SUSPENDED,
                actor_id="SYSTEM",
                actor_type="SYSTEM",
                resource_id=m.id,
                resource_type="MANDATE",
                payload={"reason": reason, "cascaded_from": root_mandate_id},
                new_state={"status": target_status.value},
            )
            db.add(audit)

        child_stmt = select(Mandate.id).where(Mandate.parent_mandate_id == curr_id)
        child_res = await db.execute(child_stmt)
        for child_id in child_res.scalars().all():
            if child_id not in visited:
                queue.append(child_id)


@router.get("/graph/tree", response_model=list[dict[str, Any]])
async def get_delegation_tree(
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Returns the full hierarchical delegation tree of all mandates and agents."""
    stmt = select(Mandate).order_by(Mandate.delegation_depth.asc(), Mandate.created_at.desc())
    res = await db.execute(stmt)
    all_mandates = res.scalars().all()

    tree_nodes = []
    for m in all_mandates:
        agent = await db.get(Agent, m.agent_id)
        tree_nodes.append(
            {
                "id": m.id,
                "parent_id": m.parent_mandate_id,
                "agent_id": m.agent_id,
                "agent_name": agent.name if agent else "Unknown",
                "agent_type": agent.agent_type if agent else "CUSTOM",
                "status": m.status.value,
                "currency": m.currency,
                "max_amount_per_op": m.max_amount_per_op,
                "aggregate_spend_limit": m.aggregate_spend_limit,
                "current_spend": m.current_aggregate_spend,
                "reserved_spend": m.reserved_spend,
                "delegated_budget": m.delegated_child_budget_allocated,
                "depth": m.delegation_depth,
                "valid_until": m.valid_until.isoformat(),
            }
        )

    return tree_nodes
