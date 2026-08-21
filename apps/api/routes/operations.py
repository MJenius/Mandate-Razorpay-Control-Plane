"""Financial Operations API routes with deterministic policy engine, two-phase budget reservation, and atomic concurrency safety."""

import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from packages.core.enums import (
    AuditAction,
    OperationStatus,
    OperationType,
    PolicyDecisionType,
    TransactionStatus,
)
from packages.core.models import Agent, AuditEvent, FinancialOperation, Mandate, Transaction
from packages.core.schemas import (
    HumanApprovalRequest,
    OperationCreate,
    OperationResponse,
    PaymentVerifyRequest,
    RefundCreateRequest,
    TransactionResponse,
)
from packages.policy.engine import PolicyEngine
from packages.razorpay.client import (
    RazorpayClient,
    RazorpayOrderRequest,
    RazorpayPaymentLinkRequest,
    RazorpayRefundRequest,
)
from packages.shared.database import get_db_session
from packages.shared.logging import get_logger

logger = get_logger("api.operations")
router = APIRouter(prefix="/operations", tags=["Operations"])

policy_engine = PolicyEngine()
razorpay_client = RazorpayClient()


@router.get("", response_model=List[OperationResponse])
async def list_operations(
    db: AsyncSession = Depends(get_db_session),
) -> List[FinancialOperation]:
    """Retrieve financial operations."""
    stmt = select(FinancialOperation).order_by(FinancialOperation.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{operation_id}", response_model=OperationResponse)
async def get_operation(
    operation_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> FinancialOperation:
    """Retrieve an operation by operation_id."""
    stmt = select(FinancialOperation).where(FinancialOperation.operation_id == operation_id)
    res = await db.execute(stmt)
    op = res.scalar_one_or_none()
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operation not found")
    return op


@router.post("", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
async def request_financial_operation(
    payload: OperationCreate,
    db: AsyncSession = Depends(get_db_session),
) -> FinancialOperation:
    """
    Deterministic Financial Operation Request Pipeline:
    1. Idempotency Check
    2. Concurrency-safe Mandate Row Lock
    3. Deterministic Policy Evaluation (ALLOW / DENY / REQUIRE_HUMAN_REVIEW)
    4. Atomic Budget Reservation (Conditional Atomic CAS UPDATE)
    5. Zero-Gateway-Dispatch Invariant on Non-ALLOW
    6. Gateway Execution + State Sync (Commit or Release Budget)
    """
    # 1. Idempotency Check
    existing_stmt = select(FinancialOperation).where(
        FinancialOperation.idempotency_key == payload.idempotency_key
    )
    existing_res = await db.execute(existing_stmt)
    existing_op = existing_res.scalar_one_or_none()
    if existing_op:
        logger.info("idempotent_operation_hit", idempotency_key=payload.idempotency_key)
        return existing_op

    # 2. Acquire Mandate and Agent
    mandate_stmt = select(Mandate).where(Mandate.id == payload.mandate_id).with_for_update()
    mandate_res = await db.execute(mandate_stmt)
    mandate = mandate_res.scalar_one_or_none()
    if not mandate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")

    agent = await db.get(Agent, payload.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    op_id = f"op_{uuid.uuid4().hex[:16]}"
    operation = FinancialOperation(
        operation_id=op_id,
        idempotency_key=payload.idempotency_key,
        agent_id=payload.agent_id,
        mandate_id=payload.mandate_id,
        operation_type=payload.operation_type,
        status=OperationStatus.INITIATED,
        amount=payload.amount,
        currency=payload.currency.upper(),
        payload=payload.payload,
        policy_evaluation_details={},
    )
    db.add(operation)
    await db.flush()

    # 3. Deterministic Policy Evaluation
    policy_result = await policy_engine.evaluate(agent, mandate, operation)
    operation.policy_evaluation_details = policy_result.model_dump()

    # Audit the policy evaluation
    audit_evt = AuditEvent(
        event_id=f"aud_{uuid.uuid4().hex[:16]}",
        action=AuditAction.POLICY_EVALUATED,
        actor_id=payload.agent_id,
        actor_type="AGENT",
        resource_id=operation.operation_id,
        resource_type="FINANCIAL_OPERATION",
        payload={
            "amount": operation.amount,
            "decision": policy_result.decision.value,
            "reasons": policy_result.rejection_reasons if not policy_result.approved else policy_result.review_reasons,
        },
        new_state={"status": operation.status.value},
    )
    db.add(audit_evt)

    # 4. Handle Decision Branching
    if policy_result.decision == PolicyDecisionType.DENY:
        operation.status = OperationStatus.POLICY_REJECTED
        operation.error_message = "; ".join(policy_result.rejection_reasons)
        await db.commit()
        await db.refresh(operation)
        return operation

    if policy_result.decision == PolicyDecisionType.REQUIRE_HUMAN_REVIEW:
        operation.status = OperationStatus.REQUIRES_APPROVAL
        operation.error_message = "; ".join(policy_result.review_reasons)
        await db.commit()
        await db.refresh(operation)
        return operation

    # 5. Policy is ALLOW -> Atomic Budget Reservation via conditional CAS update
    # Ensures strictly zero overspending under high concurrency
    reserve_stmt = (
        update(Mandate)
        .where(
            Mandate.id == mandate.id,
            (Mandate.current_aggregate_spend + Mandate.reserved_spend + payload.amount) <= Mandate.aggregate_spend_limit,
        )
        .values(
            reserved_spend=Mandate.reserved_spend + payload.amount,
            version=Mandate.version + 1,
        )
    )
    reserve_result = await db.execute(reserve_stmt)

    if reserve_result.rowcount == 0:
        # Concurrent race condition caught: budget was exhausted by another concurrent thread
        operation.status = OperationStatus.POLICY_REJECTED
        operation.error_message = "Mandate aggregate budget limit exhausted during concurrent reservation"
        policy_result.decision = PolicyDecisionType.DENY
        policy_result.approved = False
        policy_result.rejection_reasons.append(operation.error_message)
        operation.policy_evaluation_details = policy_result.model_dump()
        await db.commit()
        await db.refresh(operation)
        return operation

    operation.status = OperationStatus.RESERVED

    reserve_audit = AuditEvent(
        event_id=f"aud_{uuid.uuid4().hex[:16]}",
        action=AuditAction.BUDGET_RESERVED,
        actor_id="POLICY_ENGINE",
        actor_type="SYSTEM",
        resource_id=mandate.id,
        resource_type="MANDATE",
        payload={"reserved_amount": operation.amount, "operation_id": operation.operation_id},
        new_state={"reserved_spend": mandate.reserved_spend + payload.amount},
    )
    db.add(reserve_audit)
    await db.flush()

    # 6. Execute against Razorpay Gateway
    await _execute_gateway_operation(db, mandate, operation, payload.payload)
    return operation


async def _execute_gateway_operation(
    db: AsyncSession,
    mandate: Mandate,
    operation: FinancialOperation,
    payload: Dict[str, Any],
) -> None:
    """Executes Razorpay API and handles two-phase budget commit or failure release."""
    try:
        if operation.operation_type == OperationType.CREATE_ORDER:
            order_req = RazorpayOrderRequest(
                amount=operation.amount,
                currency=operation.currency,
                receipt=payload.get("receipt", f"rcpt_{operation.operation_id[:10]}"),
                notes={"operation_id": operation.operation_id, "agent_id": operation.agent_id},
            )
            rzp_order = await razorpay_client.create_order(order_req)

            tx = Transaction(
                operation_id=operation.id,
                gateway_name="RAZORPAY",
                gateway_order_id=rzp_order.id,
                amount=rzp_order.amount,
                currency=rzp_order.currency,
                status=TransactionStatus.CREATED,
                gateway_response=rzp_order.model_dump(),
            )
            db.add(tx)
            operation.status = OperationStatus.EXECUTING

        elif operation.operation_type == OperationType.CREATE_PAYMENT_LINK:
            plink_req = RazorpayPaymentLinkRequest(
                amount=operation.amount,
                currency=operation.currency,
                description=payload.get("description", f"Mandate Link for {operation.agent_id}"),
                customer_name=payload.get("customer_name"),
                customer_email=payload.get("customer_email"),
                customer_contact=payload.get("customer_contact"),
                notes={"operation_id": operation.operation_id},
            )
            rzp_link = await razorpay_client.create_payment_link(plink_req)

            tx = Transaction(
                operation_id=operation.id,
                gateway_name="RAZORPAY",
                gateway_payment_link_id=rzp_link.id,
                gateway_payment_link_url=rzp_link.short_url,
                amount=rzp_link.amount,
                currency=rzp_link.currency,
                status=TransactionStatus.CREATED,
                gateway_response=rzp_link.model_dump(),
            )
            db.add(tx)
            operation.status = OperationStatus.EXECUTING

        elif operation.operation_type == OperationType.CREATE_REFUND:
            payment_id = payload.get("payment_id")
            if not payment_id:
                raise ValueError("Refund requires payment_id in payload")

            refund_req = RazorpayRefundRequest(
                payment_id=payment_id,
                amount=operation.amount,
                notes={"operation_id": operation.operation_id},
            )
            rzp_refund = await razorpay_client.create_refund(refund_req)

            tx = Transaction(
                operation_id=operation.id,
                gateway_name="RAZORPAY",
                gateway_payment_id=payment_id,
                gateway_refund_id=rzp_refund.id,
                amount=rzp_refund.amount,
                currency=rzp_refund.currency,
                status=TransactionStatus.REFUNDED if rzp_refund.status == "processed" else TransactionStatus.CREATED,
                gateway_response=rzp_refund.model_dump(),
            )
            db.add(tx)
            operation.status = OperationStatus.SUCCEEDED
            
            # Atomic commit of refund/spend
            await db.execute(
                update(Mandate)
                .where(Mandate.id == mandate.id)
                .values(
                    reserved_spend=Mandate.reserved_spend - operation.amount,
                    current_aggregate_spend=Mandate.current_aggregate_spend + operation.amount,
                )
            )

        await db.commit()
        await db.refresh(operation)

    except Exception as e:
        logger.error("gateway_dispatch_failed", operation_id=operation.operation_id, error=str(e))
        # Release budget reservation atomically on failure
        await db.execute(
            update(Mandate)
            .where(Mandate.id == mandate.id)
            .values(
                reserved_spend=Mandate.reserved_spend - operation.amount,
                version=Mandate.version + 1,
            )
        )
        operation.status = OperationStatus.FAILED
        operation.error_message = str(e)

        release_audit = AuditEvent(
            event_id=f"aud_{uuid.uuid4().hex[:16]}",
            action=AuditAction.BUDGET_RELEASED,
            actor_id="POLICY_ENGINE",
            actor_type="SYSTEM",
            resource_id=mandate.id,
            resource_type="MANDATE",
            payload={"released_amount": operation.amount, "reason": "Gateway dispatch failure"},
        )
        db.add(release_audit)
        await db.commit()
        await db.refresh(operation)


@router.post("/{operation_id}/approve", response_model=OperationResponse)
async def human_approve_operation(
    operation_id: str,
    approval: HumanApprovalRequest,
    db: AsyncSession = Depends(get_db_session),
) -> FinancialOperation:
    """Human approval sign-off for operations in REQUIRES_APPROVAL status."""
    stmt = select(FinancialOperation).where(FinancialOperation.operation_id == operation_id)
    res = await db.execute(stmt)
    operation = res.scalar_one_or_none()
    if not operation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operation not found")

    if operation.status != OperationStatus.REQUIRES_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Operation is in status {operation.status.value}, cannot approve",
        )

    mandate = await db.get(Mandate, operation.mandate_id)
    if not mandate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandate not found")

    if not approval.approved:
        operation.status = OperationStatus.POLICY_REJECTED
        operation.error_message = approval.reason or "Human review rejected operation"
        audit = AuditEvent(
            event_id=f"aud_{uuid.uuid4().hex[:16]}",
            action=AuditAction.HUMAN_APPROVAL_REJECTED,
            actor_id=approval.approved_by_id,
            actor_type="PRINCIPAL",
            resource_id=operation.operation_id,
            resource_type="FINANCIAL_OPERATION",
            payload={"reason": operation.error_message},
            new_state={"status": operation.status.value},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(operation)
        return operation

    # Human sign-off approved -> Reserve budget atomically & dispatch
    reserve_stmt = (
        update(Mandate)
        .where(
            Mandate.id == mandate.id,
            (Mandate.current_aggregate_spend + Mandate.reserved_spend + operation.amount) <= Mandate.aggregate_spend_limit,
        )
        .values(
            reserved_spend=Mandate.reserved_spend + operation.amount,
            version=Mandate.version + 1,
        )
    )
    reserve_result = await db.execute(reserve_stmt)
    if reserve_result.rowcount == 0:
        operation.status = OperationStatus.POLICY_REJECTED
        operation.error_message = "Budget limit exhausted before approval could reserve funds"
        await db.commit()
        await db.refresh(operation)
        return operation

    operation.approved_by_id = approval.approved_by_id
    operation.status = OperationStatus.RESERVED

    audit = AuditEvent(
        event_id=f"aud_{uuid.uuid4().hex[:16]}",
        action=AuditAction.HUMAN_APPROVAL_GRANTED,
        actor_id=approval.approved_by_id,
        actor_type="PRINCIPAL",
        resource_id=operation.operation_id,
        resource_type="FINANCIAL_OPERATION",
        payload={"approved_by": approval.approved_by_id, "amount": operation.amount},
        new_state={"status": operation.status.value},
    )
    db.add(audit)
    await db.flush()

    await _execute_gateway_operation(db, mandate, operation, operation.payload)
    return operation


@router.post("/{operation_id}/verify-payment", response_model=Dict[str, Any])
async def verify_payment(
    operation_id: str,
    payload: PaymentVerifyRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Verifies Razorpay payment signature, commits budget from reserved -> committed, and updates ledger."""
    stmt = select(FinancialOperation).where(FinancialOperation.operation_id == operation_id)
    res = await db.execute(stmt)
    operation = res.scalar_one_or_none()
    if not operation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial operation not found")

    is_valid = razorpay_client.verify_payment_signature(
        razorpay_order_id=payload.razorpay_order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        razorpay_signature=payload.razorpay_signature,
    )

    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Razorpay signature")

    # Atomic transition budget: reserved -> committed
    await db.execute(
        update(Mandate)
        .where(Mandate.id == operation.mandate_id)
        .values(
            reserved_spend=Mandate.reserved_spend - operation.amount,
            current_aggregate_spend=Mandate.current_aggregate_spend + operation.amount,
            version=Mandate.version + 1,
        )
    )

    commit_audit = AuditEvent(
        event_id=f"aud_{uuid.uuid4().hex[:16]}",
        action=AuditAction.BUDGET_COMMITTED,
        actor_id="SYSTEM",
        actor_type="SYSTEM",
        resource_id=operation.mandate_id,
        resource_type="MANDATE",
        payload={"committed_amount": operation.amount, "operation_id": operation.operation_id},
    )
    db.add(commit_audit)

    tx_stmt = select(Transaction).where(Transaction.operation_id == operation.id)
    tx_res = await db.execute(tx_stmt)
    tx = tx_res.scalar_one_or_none()
    if tx:
        tx.gateway_payment_id = payload.razorpay_payment_id
        tx.status = TransactionStatus.CAPTURED

    operation.status = OperationStatus.SUCCEEDED

    audit = AuditEvent(
        event_id=f"aud_{uuid.uuid4().hex[:16]}",
        action=AuditAction.TRANSACTION_RECORDED,
        actor_id=operation.agent_id,
        actor_type="AGENT",
        resource_id=operation.operation_id,
        resource_type="FINANCIAL_OPERATION",
        payload={
            "order_id": payload.razorpay_order_id,
            "payment_id": payload.razorpay_payment_id,
            "verified": True,
        },
        new_state={"status": operation.status.value},
    )
    db.add(audit)
    await db.commit()

    return {
        "verified": True,
        "operation_id": operation_id,
        "status": "SUCCEEDED",
        "payment_id": payload.razorpay_payment_id,
    }
