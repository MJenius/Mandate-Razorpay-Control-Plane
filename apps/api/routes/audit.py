"""Audit trail API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models import AuditEvent
from packages.core.schemas import AuditEventResponse
from packages.shared.database import get_db_session

router = APIRouter(prefix="/audit", tags=["Audit Log"])


@router.get("", response_model=list[AuditEventResponse])
async def list_audit_events(
    actor_id: str | None = Query(None, description="Filter by actor ID"),
    resource_id: str | None = Query(None, description="Filter by resource ID"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> list[AuditEvent]:
    """Retrieve immutable audit event trail."""
    stmt = select(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(limit)

    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if resource_id:
        stmt = stmt.where(AuditEvent.resource_id == resource_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/resources/{resource_type}/{resource_id}", response_model=list[AuditEventResponse])
async def get_audit_trail_for_resource(
    resource_type: str,
    resource_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> list[AuditEvent]:
    """Retrieve all audit events for a specific resource type and ID."""
    stmt = (
        select(AuditEvent)
        .where(AuditEvent.resource_id == resource_id)
        .order_by(AuditEvent.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
