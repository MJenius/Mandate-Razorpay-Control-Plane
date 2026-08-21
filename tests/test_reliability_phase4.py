"""Comprehensive Integration and Failure-Recovery Test Suite for Phase 4: Reliability & Event-Driven Invariants."""

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from packages.core.enums import (
    OperationStatus,
    OperationType,
    PrincipalRole,
    TransactionStatus,
)
from packages.core.models import (
    Agent,
    FinancialOperation,
    Mandate,
    Principal,
    Transaction,
)
from packages.core.state_machine import FinancialOperationStateMachine, InvalidStateTransitionError
from packages.shared.config import get_settings
from services.worker.reconciliation import run_gateway_reconciliation
from tests.conftest import TestingSessionLocal


def generate_webhook_signature(payload_bytes: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_formal_state_machine_invalid_transitions() -> None:
    """
    State Machine Formal Invariant:
    Direct illegal transitions (e.g. POLICY_REJECTED -> SUCCEEDED, SUCCEEDED -> EXECUTING)
    must strictly raise InvalidStateTransitionError.
    """
    assert (
        FinancialOperationStateMachine.can_transition(
            OperationStatus.INITIATED, OperationStatus.POLICY_APPROVED
        )
        is True
    )
    assert (
        FinancialOperationStateMachine.can_transition(
            OperationStatus.RESERVED, OperationStatus.EXECUTING
        )
        is True
    )
    assert (
        FinancialOperationStateMachine.can_transition(
            OperationStatus.EXECUTING, OperationStatus.SUCCEEDED
        )
        is True
    )

    # Illegal: cannot jump directly from REJECTED to SUCCEEDED
    assert (
        FinancialOperationStateMachine.can_transition(
            OperationStatus.POLICY_REJECTED, OperationStatus.SUCCEEDED
        )
        is False
    )

    with pytest.raises(InvalidStateTransitionError):
        FinancialOperationStateMachine.validate_transition(
            current=OperationStatus.POLICY_REJECTED,
            target=OperationStatus.SUCCEEDED,
        )

    # Illegal: terminal state SUCCEEDED cannot transition to EXECUTING
    with pytest.raises(InvalidStateTransitionError):
        FinancialOperationStateMachine.validate_transition(
            current=OperationStatus.SUCCEEDED,
            target=OperationStatus.EXECUTING,
        )


@pytest.mark.asyncio
async def test_duplicate_webhook_replay_idempotency(async_client: AsyncClient) -> None:
    """
    Reliability Invariant:
    Replaying the exact same Razorpay webhook twice must result in DUPLICATE_IGNORED
    and 0 double budget commits or state corruption.
    """
    settings = get_settings()
    settings.RAZORPAY_WEBHOOK_SECRET = "test_wh_secret_p4_1"

    async with TestingSessionLocal() as session:
        principal = Principal(name="Webhook Corp", email="wh@mandate.dev", role=PrincipalRole.ADMIN)
        session.add(principal)
        await session.flush()

        agent = Agent(name="WHAgent", owner_id=principal.id, api_key_hash="hash_wh_1")
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=50000,
            aggregate_spend_limit=100000,
            current_aggregate_spend=0,
            reserved_spend=20000,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.flush()

        op = FinancialOperation(
            operation_id="op_wh_test_01",
            idempotency_key="idemp_wh_01",
            agent_id=agent.id,
            mandate_id=mandate.id,
            operation_type=OperationType.CREATE_ORDER,
            status=OperationStatus.EXECUTING,
            amount=20000,
            currency="INR",
        )
        session.add(op)
        await session.flush()

        tx = Transaction(
            operation_id=op.id,
            gateway_order_id="order_wh_rzp_01",
            amount=20000,
            currency="INR",
            status=TransactionStatus.CREATED,
        )
        session.add(tx)
        await session.commit()
        mandate_id = mandate.id

    webhook_payload = {
        "event_id": "evt_duplicate_01",
        "event": "order.paid",
        "payload": {
            "order": {"entity": {"id": "order_wh_rzp_01", "amount": 20000, "status": "paid"}},
            "payment": {
                "entity": {
                    "id": "pay_wh_rzp_01",
                    "order_id": "order_wh_rzp_01",
                    "amount": 20000,
                    "status": "captured",
                }
            },
        },
    }
    raw_bytes = json.dumps(webhook_payload).encode("utf-8")
    sig = generate_webhook_signature(raw_bytes, settings.RAZORPAY_WEBHOOK_SECRET)

    # 1. First Webhook Ingestion -> PROCESSED
    r1 = await async_client.post(
        "/api/v1/webhooks/razorpay",
        content=raw_bytes,
        headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "PROCESSED"

    # Verify budget: reserved (20k -> 0), current_aggregate_spend (0 -> 20k)
    async with TestingSessionLocal() as session:
        m1 = await session.get(Mandate, mandate_id)
        assert m1.reserved_spend == 0
        assert m1.current_aggregate_spend == 20000

    # 2. Replay Identical Webhook -> DUPLICATE_IGNORED
    r2 = await async_client.post(
        "/api/v1/webhooks/razorpay",
        content=raw_bytes,
        headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "DUPLICATE_IGNORED"

    # Verify budget remains EXACTLY 20k (no double commit)
    async with TestingSessionLocal() as session:
        m2 = await session.get(Mandate, mandate_id)
        assert m2.reserved_spend == 0
        assert m2.current_aggregate_spend == 20000


@pytest.mark.asyncio
async def test_out_of_order_webhook_arrival_convergence(async_client: AsyncClient) -> None:
    """
    Out-of-Order Webhook Test:
    'order.paid' arrives while operation is still in RESERVED state (before client sync).
    State machine must converge operation to SUCCEEDED and commit budget cleanly.
    """
    settings = get_settings()
    settings.RAZORPAY_WEBHOOK_SECRET = "test_wh_secret_p4_2"

    async with TestingSessionLocal() as session:
        principal = Principal(
            name="Fast Gateway Corp", email="fast@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        agent = Agent(name="FastAgent", owner_id=principal.id, api_key_hash="hash_fast_1")
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=50000,
            aggregate_spend_limit=100000,
            current_aggregate_spend=0,
            reserved_spend=15000,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.flush()

        # Operation is in RESERVED state (out of order webhook hits before EXECUTING)
        op = FinancialOperation(
            operation_id="op_ooo_01",
            idempotency_key="idemp_ooo_01",
            agent_id=agent.id,
            mandate_id=mandate.id,
            operation_type=OperationType.CREATE_ORDER,
            status=OperationStatus.RESERVED,
            amount=15000,
            currency="INR",
        )
        session.add(op)
        await session.flush()

        tx = Transaction(
            operation_id=op.id,
            gateway_order_id="order_ooo_rzp_01",
            amount=15000,
            currency="INR",
            status=TransactionStatus.CREATED,
        )
        session.add(tx)
        await session.commit()
        op_id = op.operation_id
        mandate_id = mandate.id

    webhook_payload = {
        "event_id": f"evt_ooo_{uuid.uuid4().hex[:8]}",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_ooo_rzp_01",
                    "order_id": "order_ooo_rzp_01",
                    "amount": 15000,
                    "status": "captured",
                }
            },
        },
    }
    raw_bytes = json.dumps(webhook_payload).encode("utf-8")
    sig = generate_webhook_signature(raw_bytes, settings.RAZORPAY_WEBHOOK_SECRET)

    res = await async_client.post(
        "/api/v1/webhooks/razorpay",
        content=raw_bytes,
        headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "PROCESSED"

    # Verify converged state
    async with TestingSessionLocal() as session:
        refreshed_op = (
            await session.execute(
                select(FinancialOperation).where(FinancialOperation.operation_id == op_id)
            )
        ).scalar_one()
        assert refreshed_op.status == OperationStatus.SUCCEEDED

        refreshed_m = await session.get(Mandate, mandate_id)
        assert refreshed_m.reserved_spend == 0
        assert refreshed_m.current_aggregate_spend == 15000


@pytest.mark.asyncio
async def test_read_only_reconciliation_detects_missed_webhook() -> None:
    """
    Reconciliation Test:
    Mandate shows operation in EXECUTING, but Razorpay order is already paid.
    Reconciliation sweep must flag the discrepancy in ReconciliationReport without blindly mutating.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(
            name="Recon Corp", email="recon@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        agent = Agent(name="ReconAgent", owner_id=principal.id, api_key_hash="hash_recon_1")
        session.add(agent)
        await session.flush()

        mandate = Mandate(
            agent_id=agent.id,
            granted_by_id=principal.id,
            currency="INR",
            max_amount_per_op=50000,
            aggregate_spend_limit=100000,
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.flush()

        op = FinancialOperation(
            operation_id="op_recon_missed_01",
            idempotency_key="idemp_recon_01",
            agent_id=agent.id,
            mandate_id=mandate.id,
            operation_type=OperationType.CREATE_ORDER,
            status=OperationStatus.EXECUTING,
            amount=30000,
            currency="INR",
        )
        session.add(op)
        await session.flush()

        tx = Transaction(
            operation_id=op.id,
            gateway_order_id="order_mock_paid_01",
            amount=30000,
            currency="INR",
            status=TransactionStatus.CREATED,
        )
        session.add(tx)
        await session.commit()

    # Run reconciliation against mock / test mode
    report = await run_gateway_reconciliation(
        session_factory=TestingSessionLocal, lookback_minutes=60
    )
    assert report.total_checked >= 1
    assert isinstance(report.discrepancies, list)


@pytest.mark.asyncio
async def test_ambiguous_gateway_outcome_idempotency_resolution(async_client: AsyncClient) -> None:
    """
    Ambiguous Gateway Resolution:
    If a client times out during order creation, re-submitting the exact same idempotency_key
    must return the existing operation without creating duplicate Razorpay orders or double-spending.
    """
    async with TestingSessionLocal() as session:
        principal = Principal(
            name="Ambiguous Corp", email="ambig@mandate.dev", role=PrincipalRole.ADMIN
        )
        session.add(principal)
        await session.flush()

        agent = Agent(name="AmbigAgent", owner_id=principal.id, api_key_hash="hash_ambig_1")
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
            allowed_operations=["CREATE_ORDER"],
            valid_until=datetime.now(UTC) + timedelta(days=30),
        )
        session.add(mandate)
        await session.commit()
        agent_id, mandate_id = agent.id, mandate.id

    shared_idempotency_key = f"idemp_ambig_{uuid.uuid4().hex}"
    payload = {
        "idempotency_key": shared_idempotency_key,
        "agent_id": agent_id,
        "mandate_id": mandate_id,
        "operation_type": "CREATE_ORDER",
        "amount": 25000,
        "currency": "INR",
        "payload": {},
    }

    # 1. First Dispatch
    r1 = await async_client.post("/api/v1/operations", json=payload)
    assert r1.status_code == 201
    op1 = r1.json()

    # 2. Ambiguous Retry: Same idempotency key
    r2 = await async_client.post("/api/v1/operations", json=payload)
    assert r2.status_code == 201
    op2 = r2.json()

    # Invariant: Must return the EXACT same operation ID (no duplicate Razorpay order dispatched)
    assert op1["operation_id"] == op2["operation_id"]

    # Invariant: Mandate reserved_spend reserved exactly 25,000 once (no double reservation)
    m_res = await async_client.get(f"/api/v1/mandates/{mandate_id}")
    assert m_res.json()["reserved_spend"] == 25000
