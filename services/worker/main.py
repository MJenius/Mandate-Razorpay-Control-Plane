"""Asynchronous background worker service with automated reconciliation for orphan budget reservations."""

import asyncio
import signal
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from packages.core.enums import AuditAction, OperationStatus, TransactionStatus
from packages.core.models import AuditEvent, FinancialOperation, Mandate, Transaction
from packages.events.bus import BaseEvent, InMemoryEventBus
from packages.razorpay.client import RazorpayClient
from packages.shared.config import get_settings
from packages.shared.database import get_session_factory
from packages.shared.logging import get_logger, setup_logging

setup_logging()
logger = get_logger("services.worker")

event_bus = InMemoryEventBus()
razorpay_client = RazorpayClient()


async def reconcile_stuck_reservations(
    timeout_seconds: int = 120,
    session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
) -> int:
    """
    Reconciliation Engine:
    Detects operations that remained in RESERVED or EXECUTING state beyond `timeout_seconds`
    (e.g., due to process crashes, network partitions, or unhandled server restarts)
    and verifies their actual state with Razorpay before releasing or committing reserved_spend.
    """
    session_maker = session_factory or get_session_factory()
    cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
    reconciled_count = 0

    async with session_maker() as db:
        stmt = select(FinancialOperation).where(
            FinancialOperation.status.in_([OperationStatus.RESERVED, OperationStatus.EXECUTING]),
            FinancialOperation.created_at <= cutoff_time,
        )
        res = await db.execute(stmt)
        stuck_ops = res.scalars().all()

        for op in stuck_ops:
            logger.warning("stuck_operation_detected", op_id=op.operation_id, status=op.status.value)
            mandate = await db.get(Mandate, op.mandate_id)
            if not mandate:
                continue

            tx_stmt = select(Transaction).where(Transaction.operation_id == op.id)
            tx_res = await db.execute(tx_stmt)
            tx = tx_res.scalar_one_or_none()

            # Case 1: Crashed before any gateway call was dispatched
            if not tx or (not tx.gateway_order_id and not tx.gateway_payment_id and not tx.gateway_payment_link_id):
                logger.info("releasing_crashed_unexecuted_reservation", op_id=op.operation_id, amount=op.amount)
                op.status = OperationStatus.FAILED
                op.error_message = "Reservation expired / process crashed before gateway dispatch"

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
                    actor_id="RECONCILIATION_WORKER",
                    actor_type="SYSTEM",
                    resource_id=mandate.id,
                    resource_type="MANDATE",
                    payload={"released_amount": op.amount, "reason": op.error_message},
                )
                db.add(audit)
                reconciled_count += 1

            # Case 2: Gateway order was created, check Razorpay status
            elif tx.gateway_order_id:
                try:
                    order_status = await razorpay_client.fetch_order(tx.gateway_order_id)
                    if order_status.status == "paid":
                        logger.info("committing_reconciled_paid_order", op_id=op.operation_id, order_id=tx.gateway_order_id)
                        op.status = OperationStatus.SUCCEEDED
                        tx.status = TransactionStatus.CAPTURED
                        await db.execute(
                            update(Mandate)
                            .where(Mandate.id == mandate.id)
                            .values(
                                reserved_spend=Mandate.reserved_spend - op.amount,
                                current_aggregate_spend=Mandate.current_aggregate_spend + op.amount,
                                version=Mandate.version + 1,
                            )
                        )
                        audit = AuditEvent(
                            event_id=f"aud_{uuid.uuid4().hex[:16]}",
                            action=AuditAction.BUDGET_COMMITTED,
                            actor_id="RECONCILIATION_WORKER",
                            actor_type="SYSTEM",
                            resource_id=mandate.id,
                            resource_type="MANDATE",
                            payload={"committed_amount": op.amount, "order_id": tx.gateway_order_id},
                        )
                        db.add(audit)
                        reconciled_count += 1
                except Exception as ex:
                    logger.error("reconciliation_fetch_failed", order_id=tx.gateway_order_id, error=str(ex))

        await db.commit()

    return reconciled_count
