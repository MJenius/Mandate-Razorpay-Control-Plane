"""Razorpay Webhook ingestion and idempotent event processing pipeline."""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from packages.core.enums import AuditAction, OperationStatus, TransactionStatus
from packages.core.models import AuditEvent, FinancialOperation, Mandate, Transaction, WebhookEvent
from packages.razorpay.client import RazorpayClient
from packages.shared.database import get_db_session
from packages.shared.logging import get_logger

logger = get_logger("api.webhooks")
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

razorpay_client = RazorpayClient()


@router.post("/razorpay", status_code=status.HTTP_200_OK)
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(..., alias="X-Razorpay-Signature"),
    x_razorpay_event_id: str | None = Header(None, alias="X-Razorpay-Event-Id"),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Ingests, verifies HMAC-SHA256 signature, deduplicates, and processes Razorpay webhooks idempotently.
    """
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")

    # 1. Cryptographic Signature Verification
    if not razorpay_client.verify_webhook_signature(body_str, x_razorpay_signature):
        logger.warning("invalid_webhook_signature", signature=x_razorpay_signature)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Razorpay webhook signature",
        )

    payload = await request.json()
    event_type = payload.get("event", "unknown")
    event_id = x_razorpay_event_id or payload.get("id") or f"wh_evt_{uuid.uuid4().hex[:12]}"
    payload_hash = hashlib.sha256(body_bytes).hexdigest()

    logger.info("webhook_received", event_id=event_id, event_type=event_type)

    # 2. Duplicate Event Protection / Idempotency Check
    existing_stmt = select(WebhookEvent).where(WebhookEvent.event_id == event_id)
    existing_res = await db.execute(existing_stmt)
    existing_wh = existing_res.scalar_one_or_none()

    if existing_wh:
        logger.info("duplicate_webhook_event_detected", event_id=event_id, processed=existing_wh.processed)
        existing_wh.processing_attempts += 1
        await db.commit()
        return {
            "status": "duplicate_acknowledged",
            "event_id": event_id,
            "processed": existing_wh.processed,
        }

    # Record Webhook receipt in DB
    wh_event = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        payload_hash=payload_hash,
        raw_payload=payload,
        signature_verified=True,
        processed=False,
        processing_attempts=1,
    )
    db.add(wh_event)
    await db.flush()

    # 3. Process Domain State Transitions
    event_payload = payload.get("payload", {})
    try:
        if event_type in ["payment.captured", "order.paid", "payment.authorized"]:
            payment_entity = event_payload.get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id")
            payment_id = payment_entity.get("id")
            status_str = payment_entity.get("status")

            # Lookup corresponding transaction
            stmt = select(Transaction).where(
                (Transaction.gateway_order_id == order_id) | (Transaction.gateway_payment_id == payment_id)
            )
            res = await db.execute(stmt)
            tx = res.scalar_one_or_none()

            if tx:
                old_status = tx.status.value
                new_status = TransactionStatus.CAPTURED if event_type in ["payment.captured", "order.paid"] else TransactionStatus.AUTHORIZED
                tx.status = new_status
                tx.gateway_payment_id = payment_id
                tx.gateway_response = payment_entity

                # Update Financial Operation
                op = await db.get(FinancialOperation, tx.operation_id)
                if op and op.status != OperationStatus.SUCCEEDED:
                    op.status = OperationStatus.SUCCEEDED

                # Record Immutable Audit Event
                audit = AuditEvent(
                    event_id=f"aud_{uuid.uuid4().hex[:16]}",
                    action=AuditAction.TRANSACTION_RECORDED,
                    actor_id=event_id,
                    actor_type="WEBHOOK",
                    resource_id=tx.id,
                    resource_type="TRANSACTION",
                    payload={"event_type": event_type, "payment_id": payment_id, "order_id": order_id},
                    previous_state={"status": old_status},
                    new_state={"status": tx.status.value},
                )
                db.add(audit)

        elif event_type in ["payment.failed"]:
            payment_entity = event_payload.get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id")
            payment_id = payment_entity.get("id")

            stmt = select(Transaction).where(
                (Transaction.gateway_order_id == order_id) | (Transaction.gateway_payment_id == payment_id)
            )
            res = await db.execute(stmt)
            tx = res.scalar_one_or_none()
            if tx:
                tx.status = TransactionStatus.FAILED
                tx.error_code = payment_entity.get("error_code")
                tx.error_description = payment_entity.get("error_description")

                op = await db.get(FinancialOperation, tx.operation_id)
                if op:
                    op.status = OperationStatus.FAILED
                    op.error_message = tx.error_description

                audit = AuditEvent(
                    event_id=f"aud_{uuid.uuid4().hex[:16]}",
                    action=AuditAction.TRANSACTION_RECORDED,
                    actor_id=event_id,
                    actor_type="WEBHOOK",
                    resource_id=tx.id,
                    resource_type="TRANSACTION",
                    payload={"event_type": event_type, "error": tx.error_description},
                    new_state={"status": tx.status.value},
                )
                db.add(audit)

        elif event_type in ["refund.processed", "refund.created"]:
            refund_entity = event_payload.get("refund", {}).get("entity", {})
            refund_id = refund_entity.get("id")
            payment_id = refund_entity.get("payment_id")
            refund_amount = refund_entity.get("amount", 0)

            stmt = select(Transaction).where(
                (Transaction.gateway_refund_id == refund_id) | (Transaction.gateway_payment_id == payment_id)
            )
            res = await db.execute(stmt)
            tx = res.scalar_one_or_none()
            if tx:
                old_status = tx.status.value
                tx.status = TransactionStatus.REFUNDED
                tx.gateway_refund_id = refund_id

                op = await db.get(FinancialOperation, tx.operation_id)
                if op:
                    op.status = OperationStatus.SUCCEEDED

                # Credit back mandate spend
                if op:
                    mandate = await db.get(Mandate, op.mandate_id)
                    if mandate and refund_amount:
                        mandate.current_aggregate_spend = max(0, mandate.current_aggregate_spend - refund_amount)

                audit = AuditEvent(
                    event_id=f"aud_{uuid.uuid4().hex[:16]}",
                    action=AuditAction.TRANSACTION_RECORDED,
                    actor_id=event_id,
                    actor_type="WEBHOOK",
                    resource_id=tx.id,
                    resource_type="TRANSACTION",
                    payload={"event_type": event_type, "refund_id": refund_id, "amount": refund_amount},
                    previous_state={"status": old_status},
                    new_state={"status": tx.status.value},
                )
                db.add(audit)

        elif event_type in ["payment_link.paid"]:
            link_entity = event_payload.get("payment_link", {}).get("entity", {})
            link_id = link_entity.get("id")

            stmt = select(Transaction).where(Transaction.gateway_payment_link_id == link_id)
            res = await db.execute(stmt)
            tx = res.scalar_one_or_none()
            if tx:
                tx.status = TransactionStatus.CAPTURED
                op = await db.get(FinancialOperation, tx.operation_id)
                if op:
                    op.status = OperationStatus.SUCCEEDED

                audit = AuditEvent(
                    event_id=f"aud_{uuid.uuid4().hex[:16]}",
                    action=AuditAction.TRANSACTION_RECORDED,
                    actor_id=event_id,
                    actor_type="WEBHOOK",
                    resource_id=tx.id,
                    resource_type="TRANSACTION",
                    payload={"event_type": event_type, "link_id": link_id},
                    new_state={"status": tx.status.value},
                )
                db.add(audit)

        wh_event.processed = True
        wh_event.processed_at = datetime.now(timezone.utc)
        await db.commit()

    except Exception as exc:
        logger.error("webhook_processing_failed", event_id=event_id, error=str(exc))
        wh_event.error_message = str(exc)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing webhook event",
        )

    logger.info("webhook_processed_successfully", event_id=event_id)
    return {
        "status": "processed",
        "event_id": event_id,
        "event_type": event_type,
    }
