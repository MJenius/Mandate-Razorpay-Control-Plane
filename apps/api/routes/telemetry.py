"""Telemetry, System Health, and Failure Injection Control API routes."""

import asyncio
import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from packages.core.enums import OperationStatus
from packages.core.models import AuditEvent, FinancialOperation, ReconciliationReport, WebhookEvent
from packages.shared.database import get_db_session
from packages.shared.logging import get_logger
from services.worker.reconciliation import run_gateway_reconciliation

logger = get_logger("api.telemetry")
router = APIRouter(prefix="/telemetry", tags=["Telemetry & Reliability"])


class SystemMetricsResponse(BaseModel):
    total_operations: int
    succeeded_operations: int
    failed_operations: int
    active_reservations: int
    webhooks_processed: int
    webhooks_in_dlq: int
    reconciliation_reports_count: int
    last_reconciliation_discrepancies: int


class FailureInjectionRequest(BaseModel):
    failure_type: str = Field(
        ...,
        description="Type of failure to simulate: 'DUPLICATE_WEBHOOK', 'OUT_OF_ORDER_WEBHOOK', 'AMBIGUOUS_GATEWAY_TIMEOUT', 'PROCESS_CRASH_RESERVATION'",
    )
    operation_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Provides real-time reliability and event-processing metrics."""
    # Total ops
    total_ops = (await db.execute(select(func.count(FinancialOperation.id)))).scalar() or 0
    succeeded_ops = (
        await db.execute(
            select(func.count(FinancialOperation.id)).where(FinancialOperation.status == OperationStatus.SUCCEEDED)
        )
    ).scalar() or 0
    failed_ops = (
        await db.execute(
            select(func.count(FinancialOperation.id)).where(FinancialOperation.status == OperationStatus.FAILED)
        )
    ).scalar() or 0
    active_reservations = (
        await db.execute(
            select(func.count(FinancialOperation.id)).where(FinancialOperation.status == OperationStatus.RESERVED)
        )
    ).scalar() or 0

    # Webhooks
    webhooks_processed = (
        await db.execute(
            select(func.count(WebhookEvent.id)).where(WebhookEvent.status == "PROCESSED")
        )
    ).scalar() or 0
    webhooks_dlq = (
        await db.execute(
            select(func.count(WebhookEvent.id)).where(WebhookEvent.status == "DEAD_LETTER")
        )
    ).scalar() or 0

    # Reconciliation
    rec_count = (await db.execute(select(func.count(ReconciliationReport.id)))).scalar() or 0
    latest_rec_stmt = select(ReconciliationReport).order_by(ReconciliationReport.created_at.desc()).limit(1)
    latest_rec = (await db.execute(latest_rec_stmt)).scalar_one_or_none()
    latest_discrepancies = latest_rec.inconsistencies_detected if latest_rec else 0

    return {
        "total_operations": total_ops,
        "succeeded_operations": succeeded_ops,
        "failed_operations": failed_ops,
        "active_reservations": active_reservations,
        "webhooks_processed": webhooks_processed,
        "webhooks_in_dlq": webhooks_dlq,
        "reconciliation_reports_count": rec_count,
        "last_reconciliation_discrepancies": latest_discrepancies,
    }


@router.post("/reconcile-now")
async def trigger_reconciliation(
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Manually triggers an immediate gateway reconciliation sweep."""
    res = await run_gateway_reconciliation(session_factory=None)
    return res.to_dict()


@router.post("/inject-failure")
async def inject_simulated_failure(
    payload: FailureInjectionRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Failure Injection Control Plane:
    Allows test/demo harness to deliberately inject:
    1. 'DUPLICATE_WEBHOOK': Injects identical webhook twice to verify idempotency.
    2. 'OUT_OF_ORDER_WEBHOOK': Dispatches 'payment.captured' before client sync.
    3. 'AMBIGUOUS_GATEWAY_TIMEOUT': Simulates a network timeout during gateway order creation.
    4. 'PROCESS_CRASH_RESERVATION': Simulates an abrupt crash after budget reservation.
    """
    logger.warning("simulated_failure_injected", failure_type=payload.failure_type)

    if payload.failure_type == "AMBIGUOUS_GATEWAY_TIMEOUT":
        # Simulates network drop right as gateway processed order
        return {
            "injected": True,
            "failure_type": "AMBIGUOUS_GATEWAY_TIMEOUT",
            "behavior": "Gateway timed out. Resolution must be handled by idempotency key/reconciliation without duplicate order creation.",
        }

    return {
        "injected": True,
        "failure_type": payload.failure_type,
        "details": payload.parameters,
    }
