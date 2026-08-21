"""Financial Operations API routes enforcing idempotency, policy evaluation, and Razorpay gateway execution."""

import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from packages.core.enums import AuditAction, OperationStatus, OperationType, TransactionStatus
from packages.core.models import Agent, AuditEvent, FinancialOperation, Mandate, Transaction
from packages.core.schemas import (
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


@router.post("", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
async def request_financial_operation(
    payload: OperationCreate,
    db: AsyncSession = Depends(get_db_session),
) -> FinancialOperation:
    """
    Request a bounded financial operation on behalf of an AI Agent.
    Evaluates policy checks before executing external Razorpay gateway operations.
    Guarantees at-most-once execution via idempotency key locks.
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

    if not policy_result.approved:
        operation.status = OperationStatus.POLICY_REJECTED
        operation.error_message = "; ".join(policy_result.rejection_reasons)
        
        audit_evt = AuditEvent(
            event_id=f"aud_{uuid.uuid4().hex[:16]}",
            action=AuditAction.POLICY_EVALUATED,
            actor_id=payload.agent_id,
            actor_type="AGENT",
            resource_id=operation.operation_id,
            resource_type="FINANCIAL_OPERATION",
            payload={"amount": operation.amount, "approved": False, "reasons": policy_result.rejection_reasons},
            new_state={"status": operation.status.value},
        )
        db.add(audit_evt)
        await db.commit()
        await db.refresh(operation)
        return operation

    # Policy Approved: Update status and accumulate spend
    operation.status = OperationStatus.POLICY_APPROVED
    mandate.current_aggregate_spend += operation.amount

    audit_evt = AuditEvent(
        event_id=f"aud_{uuid.uuid4().hex[:16]}",
        action=AuditAction.POLICY_EVALUATED,
        actor_id=payload.agent_id,
        actor_type="AGENT",
        resource_id=operation.operation_id,
        resource_type="FINANCIAL_OPERATION",
        payload={"amount": operation.amount, "approved": True},
        new_state={"status": operation.status.value},
    )
    db.add(audit_evt)

    # 4. Dispatch to Razorpay Gateway based on operation type
    try:
        if operation.operation_type == OperationType.CREATE_ORDER:
            order_req = RazorpayOrderRequest(
                amount=operation.amount,
                currency=operation.currency,
                receipt=payload.payload.get("receipt", f"rcpt_{operation.operation_id[:10]}"),
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
                description=payload.payload.get("description", f"Mandate Link for {operation.agent_id}"),
                customer_name=payload.payload.get("customer_name"),
                customer_email=payload.payload.get("customer_email"),
                customer_contact=payload.payload.get("customer_contact"),
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
            payment_id = payload.payload.get("payment_id")
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

        await db.commit()
        await db.refresh(operation)

    except Exception as e:
        logger.error("gateway_dispatch_failed", operation_id=operation.operation_id, error=str(e))
        operation.status = OperationStatus.FAILED
        operation.error_message = str(e)
        # Revert aggregate spend reservation on immediate client exception
        mandate.current_aggregate_spend = max(0, mandate.current_aggregate_spend - operation.amount)
        await db.commit()
        await db.refresh(operation)

    return operation


@router.post("/{operation_id}/verify-payment", response_model=Dict[str, Any])
async def verify_payment(
    operation_id: str,
    payload: PaymentVerifyRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Verifies Razorpay payment signature from client-side checkout and updates ledger.
    """
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

    # Update Transaction record
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
