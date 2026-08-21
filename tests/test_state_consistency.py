"""Tests for State-Consistency Edge Cases: Crash Recovery, Orphan Reservations, Refunds, and Gateway Failures."""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from packages.core.enums import MandateStatus, OperationStatus, OperationType, PrincipalRole, TransactionStatus
from packages.core.models import Agent, FinancialOperation, Mandate, Principal, Transaction
from services.worker.main import reconcile_stuck_reservations
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_reconciliation_releases_crashed_orphan_reservation() -> None:
    """
    Simulates a server crash right after budget was reserved, before gateway dispatch completed.
    The reconciliation engine must detect the orphan reservation, mark operation FAILED,
    and release reserved_spend back to the mandate budget.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(name="Crash Test Corp", email="crashtest@mandate.dev", role=PrincipalRole.ADMIN)
        session.add(principal)
        await session.flush()

        agent = Agent(name="CrashAgent", owner_id=principal.id, api_key_hash="hash_crash_1")
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=50000,
            aggregate_spend_limit=100000,
            current_aggregate_spend=0,
            reserved_spend=30000,  # 30,000 reserved
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        )
        session.add(mandate)
        await session.flush()

        # Create an orphan operation that was created 5 minutes ago (simulating a crash)
        past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        orphan_op = FinancialOperation(
            operation_id=f"op_orphan_{uuid.uuid4().hex[:10]}",
            idempotency_key=f"idemp_orphan_{uuid.uuid4().hex}",
            agent_id=agent.id,
            mandate_id=mandate.id,
            operation_type=OperationType.CREATE_ORDER,
            status=OperationStatus.RESERVED,
            amount=30000,
            currency="INR",
            created_at=past_time,
            updated_at=past_time,
        )
        session.add(orphan_op)
        await session.commit()
        mandate_id = mandate.id
        op_id = orphan_op.operation_id

    # Run reconciliation using test session factory
    reconciled_count = await reconcile_stuck_reservations(timeout_seconds=60, session_factory=TestingSessionLocal)
    assert reconciled_count == 1

    # Verify mandate reserved_spend is safely released to 0
    async with TestingSessionLocal() as session:
        refreshed_mandate = await session.get(Mandate, mandate_id)
        assert refreshed_mandate.reserved_spend == 0
        assert refreshed_mandate.current_aggregate_spend == 0

        op_stmt = select(FinancialOperation).where(FinancialOperation.operation_id == op_id)
        op_res = await session.execute(op_stmt)
        refreshed_op = op_res.scalar_one()
        assert refreshed_op.status == OperationStatus.FAILED
        assert "crashed before gateway dispatch" in refreshed_op.error_message


@pytest.mark.asyncio
async def test_failed_gateway_dispatch_immediately_releases_reservation(async_client: AsyncClient) -> None:
    """
    Verifies that if a gateway call fails during execution, reserved_spend is immediately
    released and does not stay stuck in RESERVED.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(name="Gateway Fail Corp", email="fail@mandate.dev", role=PrincipalRole.ADMIN)
        session.add(principal)
        await session.flush()

        agent = Agent(name="FailAgent", owner_id=principal.id, api_key_hash="hash_fail_1")
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=50000,
            aggregate_spend_limit=100000,
            current_aggregate_spend=0,
            reserved_spend=0,
            allowed_operations=["CREATE_REFUND"],
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()
        agent_id, mandate_id = agent.id, mandate.id

    # Intentionally trigger a failure (CREATE_REFUND without valid payment_id in payload)
    op_payload = {
        "idempotency_key": f"idemp_fail_{uuid.uuid4().hex}",
        "agent_id": agent_id,
        "mandate_id": mandate_id,
        "operation_type": "CREATE_REFUND",
        "amount": 10000,
        "currency": "INR",
        "payload": {},  # Missing payment_id -> raises ValueError
    }

    res = await async_client.post("/api/v1/operations", json=op_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "FAILED"

    # Verify reserved_spend returned to 0
    mandate_res = await async_client.get(f"/api/v1/mandates/{mandate_id}")
    assert mandate_res.status_code == 200
    m_data = mandate_res.json()
    assert m_data["reserved_spend"] == 0
    assert m_data["current_aggregate_spend"] == 0
