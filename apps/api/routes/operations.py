"""Financial Operations API routes enforcing idempotency and policy checks."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from packages.core.enums import AuditAction, OperationStatus
from packages.core.models import Agent, AuditEvent, FinancialOperation, Mandate
from packages.core.schemas import OperationCreate, OperationResponse
from packages.policy.engine import PolicyEngine
from packages.shared.database import get_db_session
from packages.shared.logging import get_logger

logger = get_logger("api.operations")
router = APIRouter(prefix="/operations", tags=["Operations"])

policy_engine = PolicyEngine()


@router.get("", response_model=List[OperationResponse])
async def list_operations(
    db: AsyncSession = Depends(get_db_session),
) -> List[FinancialOperation]:
    """Retrieve financial operations."""
    stmt = select(FinancialOperation).order_by(FinancialOperation.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
async def request_financial_operation(
    payload: OperationCreate,
    db: AsyncSession = Depends(get_db_session),
) -> FinancialOperation:
    """Request a bounded financial operation on behalf of an AI Agent."""
    # 1. Idempotency Check
    existing_stmt = select(FinancialOperation).where(
        FinancialOperation.idempotency_key == payload.idempotency_key
    )
    existing_res = await db.execute(existing_stmt)
    existing_op = existing_res.scalar_one_or_none()
    if existing_op:
        logger.info("idempotent_operation_hit", idempotency_key=payload.idempotency_key)
        return existing_op

    # 2. Fetch Agent & Mandate
    agent = await db.get(Agent, payload.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    mandate = await db.get(Mandate, payload.mandate_id)
    if not mandate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")

    op_id = f"op_{uuid.uuid4().hex[:16]}"
    operation = FinancialOperation(
        operation_id=op_id,
        idempotency_key=payload.idempotency_key,
        agent_id=payload.agent_id,
        mandate_id=payload.mandate_id,
        operation_type=payload.operation_type,
        status=OperationStatus.INITIATED,
        amount=payload.amount,
        currency=payload.currency,
        payload=payload.payload,
        policy_evaluation_details={},
    )
    db.add(operation)
    await db.flush()

    # 3. Policy Evaluation Check
    policy_result = await policy_engine.evaluate_operation(mandate, operation)
    operation.policy_evaluation_details = policy_result.model_dump()

    if policy_result.approved:
        operation.status = OperationStatus.POLICY_APPROVED
        # Accumulate spend against mandate
        mandate.current_aggregate_spend += operation.amount
    else:
        operation.status = OperationStatus.POLICY_REJECTED
        operation.error_message = "; ".join(policy_result.rejection_reasons)

    # 4. Record Immutable Audit Event
    audit_evt = AuditEvent(
        event_id=f"aud_{uuid.uuid4().hex[:16]}",
        action=AuditAction.POLICY_EVALUATED,
        actor_id=payload.agent_id,
        actor_type="AGENT",
        resource_id=operation.operation_id,
        resource_type="FINANCIAL_OPERATION",
        payload={
            "amount": operation.amount,
            "approved": policy_result.approved,
            "status": operation.status.value,
        },
        new_state={"status": operation.status.value},
    )
    db.add(audit_evt)
    await db.commit()
    await db.refresh(operation)

    logger.info("operation_evaluated", op_id=operation.operation_id, approved=policy_result.approved)
    return operation
