"""Production Webhook Ingestion Pipeline with HMAC Verification, Out-of-Order Handling, and DLQ."""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from packages.core.enums import (
    AuditAction,
    OperationStatus,
    TransactionStatus,
)
from packages.core.models import AuditEvent, FinancialOperation, Mandate, Transaction, WebhookEvent
from packages.core.state_machine import FinancialOperationStateMachine
from packages.shared.config import get_settings
from packages.shared.database import get_db_session
from packages.shared.logging import get_logger

logger = get_logger("api.webhooks")
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(..., alias="X-Razorpay-Signature"),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Production-grade Webhook Pipeline:
    1. Read raw body and verify HMAC-SHA256 signature using separate high-entropy secret.
    2. Idempotency Check: Persist raw event to `webhook_events` before processing.
    3. Out-of-Order and Duplicate Event Handling.
    4. State Machine Transition & Budget Accounting.
    5. Dead-Letter Queue (DLQ) routing upon max retry exhaustion.
    """
    settings = get_settings()
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")

    # 1. Signature Verification
    if settings.RAZORPAY_WEBHOOK_SECRET:
        expected_sig = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, x_razorpay_signature):
            logger.warning("webhook_signature_verification_failed", received_sig=x_razorpay_signature)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Razorpay webhook signature",
            )

    try:
        event_data = json.loads(body_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed JSON payload")

    event_id = event_data.get("event_id") or f"evt_{uuid.uuid4().hex[:12]}"
    event_type = event_data.get("event", "unknown")
    payload_hash = hashlib.sha256(raw_body).hexdigest()

    # 2. Idempotency Check & Raw Persistence
    existing_stmt = select(WebhookEvent).where(WebhookEvent.event_id == event_id)
    existing_res = await db.execute(existing_stmt)
    existing_evt = existing_res.scalar_one_or_none()

    if existing_evt and existing_evt.status == "PROCESSED":
        logger.info("duplicate_webhook_ignored", event_id=event_id, event_type=event_type)
        return {
            "status": "DUPLICATE_IGNORED",
            "message": f"Webhook '{event_id}' already processed idempotently.",
            "event_id": event_id,
        }

    webhook_record = existing_evt or WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        payload_hash=payload_hash,
        raw_payload=event_data,
        signature_verified=True,
        status="PROCESSING",
        processing_attempts=1 if not existing_evt else existing_evt.processing_attempts + 1,
    )
    if not existing_evt:
        db.add(webhook_record)
    else:
        webhook_record.status = "PROCESSING"
        webhook_record.processing_attempts += 1
    await db.flush()

    # 3. Process Domain Event Transition
    try:
        await _process_domain_webhook_event(db, event_type, event_data)
        webhook_record.status = "PROCESSED"
        webhook_record.processed = True
        webhook_record.processed_at = datetime.now(timezone.utc)
        webhook_record.error_message = None
        await db.commit()

        return {
            "status": "PROCESSED",
            "event_id": event_id,
            "event_type": event_type,
        }

    except Exception as e:
        logger.error("webhook_processing_failed", event_id=event_id, error=str(e))
        webhook_record.error_message = str(e)

        if webhook_record.processing_attempts >= webhook_record.max_retries:
            webhook_record.status = "DEAD_LETTER"
            logger.critical("webhook_moved_to_dlq", event_id=event_id, attempts=webhook_record.processing_attempts)
        else:
            webhook_record.status = "FAILED"

        await db.commit()
        return {
            "status": webhook_record.status,
            "event_id": event_id,
            "error": str(e),
        }


async def _process_domain_webhook_event(
    db: AsyncSession,
    event_type: str,
    event_data: Dict[str, Any],
) -> None:
    """Handles domain state transitions and budget commits for payment/refund/order events."""
    payload = event_data.get("payload", {})

    # A. Order Paid / Payment Captured
    if event_type in ["order.paid", "payment.captured"]:
        payment_entity = payload.get("payment", {}).get("entity", {})
        order_entity = payload.get("order", {}).get("entity", {})

        order_id = payment_entity.get("order_id") or order_entity.get("id")
        payment_id = payment_entity.get("id")

        if order_id:
            tx_stmt = select(Transaction).where(Transaction.gateway_order_id == order_id)
            tx_res = await db.execute(tx_stmt)
            tx = tx_res.scalar_one_or_none()

            if tx:
                op = await db.get(FinancialOperation, tx.operation_id)
                if op and op.status != OperationStatus.SUCCEEDED:
                    # Validate State Transition
                    FinancialOperationStateMachine.validate_transition(
                        current=op.status,
                        target=OperationStatus.SUCCEEDED,
                        context_info=f"Webhook event: {event_type}",
                    )

                    op.status = OperationStatus.SUCCEEDED
                    tx.status = TransactionStatus.CAPTURED
                    if payment_id:
                        tx.gateway_payment_id = payment_id

                    # Commit Budget from reserved -> current_aggregate_spend
                    mandate = await db.get(Mandate, op.mandate_id)
                    if mandate:
                        # Check if budget is in reserved state
                        if mandate.reserved_spend >= op.amount:
                            await db.execute(
                                update(Mandate)
                                .where(Mandate.id == mandate.id)
                                .values(
                                    reserved_spend=Mandate.reserved_spend - op.amount,
                                    current_aggregate_spend=Mandate.current_aggregate_spend + op.amount,
                                    version=Mandate.version + 1,
                                )
                            )
                        else:
                            # Out-of-order resolution: direct increment
                            await db.execute(
                                update(Mandate)
                                .where(Mandate.id == mandate.id)
                                .values(
                                    current_aggregate_spend=Mandate.current_aggregate_spend + op.amount,
                                    version=Mandate.version + 1,
                                )
                            )

                    audit = AuditEvent(
                        event_id=f"aud_{uuid.uuid4().hex[:16]}",
                        action=AuditAction.BUDGET_COMMITTED,
                        actor_id="WEBHOOK_PROCESSOR",
                        actor_type="SYSTEM",
                        resource_id=op.mandate_id,
                        resource_type="MANDATE",
                        payload={"event_type": event_type, "order_id": order_id, "amount": op.amount},
                        new_state={"status": op.status.value},
                    )
                    db.add(audit)

    # B. Payment Failed
    elif event_type == "payment.failed":
        payment_entity = payload.get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")

        if order_id:
            tx_stmt = select(Transaction).where(Transaction.gateway_order_id == order_id)
            tx_res = await db.execute(tx_stmt)
            tx = tx_res.scalar_one_or_none()

            if tx:
                op = await db.get(FinancialOperation, tx.operation_id)
                if op and op.status in [OperationStatus.EXECUTING, OperationStatus.RESERVED]:
                    op.status = OperationStatus.FAILED
                    op.error_message = payment_entity.get("error_description", "Payment failed via gateway webhook")
                    tx.status = TransactionStatus.FAILED

                    # Release reserved spend back to mandate
                    mandate = await db.get(Mandate, op.mandate_id)
                    if mandate and mandate.reserved_spend >= op.amount:
                        await db.execute(
                            update(Mandate)
                            .where(Mandate.id == mandate.id)
                            .values(
                                reserved_spend=Mandate.reserved_spend - op.amount,
                                version=Mandate.version + 1,
                            )
                        )

                    audit = AuditEvent(
                        event_id=f"aud_{uuid.uuid4().hex[:16]}",
                        action=AuditAction.BUDGET_RELEASED,
                        actor_id="WEBHOOK_PROCESSOR",
                        actor_type="SYSTEM",
                        resource_id=op.mandate_id,
                        resource_type="MANDATE",
                        payload={"event_type": event_type, "order_id": order_id, "amount": op.amount},
                        new_state={"status": op.status.value},
                    )
                    db.add(audit)

    # C. Refund Processed
    elif event_type == "refund.processed":
        refund_entity = payload.get("refund", {}).get("entity", {})
        payment_id = refund_entity.get("payment_id")
        refund_amount = refund_entity.get("amount", 0)

        if payment_id:
            tx_stmt = select(Transaction).where(Transaction.gateway_payment_id == payment_id)
            tx_res = await db.execute(tx_stmt)
            tx = tx_res.scalar_one_or_none()

            if tx:
                op = await db.get(FinancialOperation, tx.operation_id)
                if op:
                    mandate = await db.get(Mandate, op.mandate_id)
                    if mandate:
                        # Restore spent budget allowance
                        await db.execute(
                            update(Mandate)
                            .where(Mandate.id == mandate.id)
                            .values(
                                current_aggregate_spend=Mandate.current_aggregate_spend - refund_amount,
                                version=Mandate.version + 1,
                            )
                        )
