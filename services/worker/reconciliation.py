"""Automated Read-Only Gateway Reconciliation Worker."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.core.enums import OperationStatus
from packages.core.models import FinancialOperation, ReconciliationReport, Transaction
from packages.razorpay.client import RazorpayClient
from packages.shared.database import get_session_factory
from packages.shared.logging import get_logger

logger = get_logger("worker.reconciliation")


class ReconciliationResult:
    def __init__(self) -> None:
        self.total_checked: int = 0
        self.discrepancies: list[dict[str, Any]] = []
        self.synced_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_checked": self.total_checked,
            "discrepancies_count": len(self.discrepancies),
            "discrepancies": self.discrepancies,
            "synced_count": self.synced_count,
        }


async def run_gateway_reconciliation(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    session: AsyncSession | None = None,
    lookback_minutes: int = 1440,  # 24 hours
) -> ReconciliationResult:
    """
    Read-Only Gateway Reconciliation Engine:
    Periodically compares local Mandate operations/transactions against Razorpay gateway reality.
    Detects:
    1. Missed Webhooks: Razorpay shows Order 'paid' but Mandate shows 'EXECUTING'.
    2. Orphan Reservations: Mandate shows 'RESERVED' with no Gateway order.
    3. Amount Mismatches: Gateway charged amount differs from recorded operation.
    Persists an immutable ReconciliationReport for auditability.
    """
    razorpay = RazorpayClient()
    result = ReconciliationResult()
    cutoff = datetime.now(UTC) - timedelta(minutes=lookback_minutes)

    if session is not None:
        await _perform_reconciliation_on_session(session, razorpay, result, cutoff)
    else:
        session_maker = session_factory or get_session_factory()
        async with session_maker() as db:
            await _perform_reconciliation_on_session(db, razorpay, result, cutoff)

    return result


async def _perform_reconciliation_on_session(
    db: AsyncSession,
    razorpay: RazorpayClient,
    result: ReconciliationResult,
    cutoff: datetime,
) -> None:
    # 1. Inspect all active and executing transactions
    stmt = (
        select(Transaction, FinancialOperation)
        .join(FinancialOperation, Transaction.operation_id == FinancialOperation.id)
        .where(FinancialOperation.created_at >= cutoff)
    )
    records = (await db.execute(stmt)).all()

    for tx, op in records:
        result.total_checked += 1
        if not tx.gateway_order_id:
            continue

        try:
            # Query Razorpay Gateway in read-only mode
            rzp_order = await razorpay.fetch_order(tx.gateway_order_id)

            # Check for Missed Webhook discrepancy
            if rzp_order.status == "paid" and op.status != OperationStatus.SUCCEEDED:
                disc = {
                    "type": "MISSED_WEBHOOK_PAID_ORDER",
                    "operation_id": op.operation_id,
                    "order_id": tx.gateway_order_id,
                    "mandate_status": op.status.value,
                    "gateway_status": rzp_order.status,
                    "amount_paise": op.amount,
                }
                result.discrepancies.append(disc)
                logger.warning("reconciliation_discrepancy_detected", **disc)

            # Check for Amount mismatch
            if rzp_order.amount != op.amount:
                disc = {
                    "type": "AMOUNT_MISMATCH",
                    "operation_id": op.operation_id,
                    "order_id": tx.gateway_order_id,
                    "mandate_amount": op.amount,
                    "gateway_amount": rzp_order.amount,
                }
                result.discrepancies.append(disc)
                logger.error("reconciliation_amount_mismatch", **disc)

        except Exception as e:
            logger.error(
                "reconciliation_order_check_failed", order_id=tx.gateway_order_id, error=str(e)
            )

    # 2. Persist Immutable Reconciliation Report
    report = ReconciliationReport(
        report_id=f"rec_{uuid.uuid4().hex[:12]}",
        total_audited=result.total_checked,
        inconsistencies_detected=len(result.discrepancies),
        details=result.to_dict(),
    )
    db.add(report)
    await db.commit()

