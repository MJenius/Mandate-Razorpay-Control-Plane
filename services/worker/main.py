"""Asynchronous background worker service with automated reconciliation for orphan budget reservations."""

import asyncio
import signal
import sys
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.core.enums import AuditAction, OperationStatus, TransactionStatus
from packages.core.models import AuditEvent, FinancialOperation, Mandate, Transaction
from packages.events.bus import InMemoryEventBus
from packages.razorpay.client import RazorpayClient
from packages.shared.config import get_settings
from packages.shared.database import get_engine, get_session_factory
from packages.shared.logging import get_logger, setup_logging

setup_logging()
logger = get_logger("services.worker")

event_bus = InMemoryEventBus()
razorpay_client = RazorpayClient()

# Global worker state and concurrency sweep lock
_sweep_lock = asyncio.Lock()
_worker_running = True
_worker_heartbeat: dict[str, Any] = {
    "status": "stopped",
    "last_heartbeat_utc": None,
    "total_reconciled": 0,
    "last_sweep_duration_ms": 0.0,
}


def get_worker_heartbeat() -> dict[str, Any]:
    """Returns current worker status and heartbeat metadata."""
    return dict(_worker_heartbeat)


async def reconcile_stuck_reservations(
    timeout_seconds: int = 120,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> int:
    """
    Reconciliation Engine with Concurrency Sweep Protection:
    Detects operations that remained in RESERVED or EXECUTING state beyond `timeout_seconds`
    (e.g., due to process crashes, network partitions, or unhandled server restarts)
    and verifies their actual state with Razorpay before releasing or committing reserved_spend.
    """
    if _sweep_lock.locked():
        logger.info("reconciliation_sweep_skipped_already_in_progress")
        return 0

    async with _sweep_lock:
        start_time = datetime.now(UTC)
        session_maker = session_factory or get_session_factory()
        cutoff_time = datetime.now(UTC) - timedelta(seconds=timeout_seconds)
        reconciled_count = 0

        async with session_maker() as db:
            stmt = select(FinancialOperation).where(
                FinancialOperation.status.in_([OperationStatus.RESERVED, OperationStatus.EXECUTING]),
                FinancialOperation.created_at <= cutoff_time,
            ).with_for_update(skip_locked=True)
            res = await db.execute(stmt)
            stuck_ops = res.scalars().all()

            for op in stuck_ops:
                logger.warning(
                    "stuck_operation_detected", op_id=op.operation_id, status=op.status.value
                )
                mandate = await db.get(Mandate, op.mandate_id)
                if not mandate:
                    continue

                tx_stmt = select(Transaction).where(Transaction.operation_id == op.id)
                tx_res = await db.execute(tx_stmt)
                tx = tx_res.scalar_one_or_none()

                # Case 1: Crashed before any gateway call was dispatched
                if not tx or (
                    not tx.gateway_order_id
                    and not tx.gateway_payment_id
                    and not tx.gateway_payment_link_id
                ):
                    logger.info(
                        "releasing_crashed_unexecuted_reservation",
                        op_id=op.operation_id,
                        amount=op.amount,
                    )
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
                            logger.info(
                                "committing_reconciled_paid_order",
                                op_id=op.operation_id,
                                order_id=tx.gateway_order_id,
                            )
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
                                payload={
                                    "committed_amount": op.amount,
                                    "order_id": tx.gateway_order_id,
                                },
                            )
                            db.add(audit)
                            reconciled_count += 1
                        elif order_status.status in ("attempted", "created") and (datetime.now(UTC) - op.created_at).total_seconds() > 300:
                            # Order created but unpaid after 5 minutes -> release reservation
                            logger.info(
                                "releasing_unpaid_expired_order_reservation",
                                op_id=op.operation_id,
                                order_id=tx.gateway_order_id,
                            )
                            op.status = OperationStatus.FAILED
                            op.error_message = "Order unpaid within timeout window"
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
                                payload={"released_amount": op.amount, "reason": "Order unpaid timeout"},
                            )
                            db.add(audit)
                            reconciled_count += 1
                    except Exception as ex:
                        logger.error(
                            "reconciliation_fetch_failed", order_id=tx.gateway_order_id, error=str(ex)
                        )

            await db.commit()

        duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000.0
        _worker_heartbeat["last_sweep_duration_ms"] = round(duration_ms, 2)
        _worker_heartbeat["last_heartbeat_utc"] = datetime.now(UTC).isoformat()
        _worker_heartbeat["total_reconciled"] += reconciled_count

        return reconciled_count


async def run_worker_loop(interval_seconds: int = 30) -> None:
    """Continuous background worker loop with startup retries, initial sweep, and graceful shutdown."""
    global _worker_running
    settings = get_settings()
    logger.info("background_worker_starting", interval=interval_seconds, env=settings.ENVIRONMENT)
    _worker_heartbeat["status"] = "starting"

    # 1. Startup retry loop for PostgreSQL connection
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            engine = get_engine()
            async with engine.begin() as conn:
                if settings.AUTO_MIGRATE_ON_STARTUP:
                    from packages.core.models import Base
                    await conn.run_sync(Base.metadata.create_all)
            logger.info("worker_database_ready", attempt=attempt)
            break
        except Exception as exc:
            logger.warning("worker_db_retry", attempt=attempt, max_retries=max_retries, error=str(exc))
            if attempt < max_retries:
                await asyncio.sleep(1.0 * attempt)
            else:
                if settings.ENVIRONMENT.lower() == "production":
                    logger.critical("fatal_worker_db_failure", error=str(exc))
                    raise RuntimeError(f"Worker could not reach database: {exc}") from exc

    _worker_heartbeat["status"] = "running"
    _worker_heartbeat["last_heartbeat_utc"] = datetime.now(UTC).isoformat()

    # 2. Immediate Initial Startup Recovery Sweep
    try:
        initial_reconciled = await reconcile_stuck_reservations(timeout_seconds=60)
        if initial_reconciled > 0:
            logger.info("startup_orphan_recovery_sweep_completed", reconciled=initial_reconciled)
    except Exception as e:
        logger.error("startup_reconciliation_error", error=str(e))

    # 3. Continuous worker loop
    while _worker_running:
        try:
            reconciled = await reconcile_stuck_reservations(timeout_seconds=120)
            if reconciled > 0:
                logger.info("reconciliation_cycle_completed", reconciled_count=reconciled)
            _worker_heartbeat["last_heartbeat_utc"] = datetime.now(UTC).isoformat()
        except Exception as e:
            logger.error("worker_loop_error", error=str(e))
        
        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            break

    _worker_heartbeat["status"] = "stopped"
    logger.info("background_worker_shutdown_complete")


def shutdown_handler(signum: int, frame: Any) -> None:
    """Handles OS signals for graceful shutdown."""
    global _worker_running
    logger.info("worker_shutdown_signal_received", signal=signum)
    _worker_running = False


if __name__ == "__main__":
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, shutdown_handler)
        signal.signal(signal.SIGINT, shutdown_handler)

    try:
        asyncio.run(run_worker_loop())
    except (KeyboardInterrupt, SystemExit):
        logger.info("background_worker_stopped")
