"""Shared atomic budget reservation primitive."""

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models import Mandate
from packages.shared.observability import CAS_BUDGET_RESERVATIONS_TOTAL


async def reserve_budget(db: AsyncSession, mandate_id: str, amount: int) -> bool:
    """Reserve funds only when the aggregate mandate limit still permits it."""
    result = await db.execute(
        update(Mandate)
        .where(
            Mandate.id == mandate_id,
            (Mandate.current_aggregate_spend + Mandate.reserved_spend + amount)
            <= Mandate.aggregate_spend_limit,
        )
        .values(reserved_spend=Mandate.reserved_spend + amount, version=Mandate.version + 1)
    )
    reserved = getattr(result, "rowcount", 0) == 1
    CAS_BUDGET_RESERVATIONS_TOTAL.labels(status="success" if reserved else "exhausted").inc()
    return reserved
