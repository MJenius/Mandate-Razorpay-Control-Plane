"""Tests for the Policy Engine and Rule Evaluators."""

from datetime import UTC, datetime, timedelta

import pytest

from packages.core.enums import AgentStatus, MandateStatus, OperationType
from packages.core.models import Agent, FinancialOperation, Mandate
from packages.policy.engine import PolicyEngine


@pytest.mark.asyncio
async def test_policy_engine_approval_under_budget() -> None:
    engine = PolicyEngine()
    agent = Agent(
        id="ag_1", name="Bot 1", owner_id="usr_1", status=AgentStatus.ACTIVE, api_key_hash="hash_1"
    )
    mandate = Mandate(
        id="mand_1",
        agent_id="ag_1",
        granted_by_id="usr_1",
        status=MandateStatus.ACTIVE,
        currency="INR",
        max_amount_per_op=50000,
        aggregate_spend_limit=200000,
        current_aggregate_spend=10000,
        reserved_spend=0,
        allowed_operations=["CREATE_ORDER", "CAPTURE_PAYMENT"],
        valid_until=datetime.now(UTC) + timedelta(days=30),
    )
    operation = FinancialOperation(
        operation_id="op_1",
        idempotency_key="idemp_1",
        agent_id="ag_1",
        mandate_id="mand_1",
        operation_type=OperationType.CREATE_ORDER,
        amount=25000,
        currency="INR",
    )

    result = await engine.evaluate(agent, mandate, operation)
    assert result.approved is True
    assert len(result.rejection_reasons) == 0


@pytest.mark.asyncio
async def test_policy_engine_rejection_over_per_op_limit() -> None:
    engine = PolicyEngine()
    agent = Agent(
        id="ag_1", name="Bot 1", owner_id="usr_1", status=AgentStatus.ACTIVE, api_key_hash="hash_1"
    )
    mandate = Mandate(
        id="mand_1",
        agent_id="ag_1",
        granted_by_id="usr_1",
        status=MandateStatus.ACTIVE,
        currency="INR",
        max_amount_per_op=5000,
        aggregate_spend_limit=50000,
        current_aggregate_spend=0,
        reserved_spend=0,
        allowed_operations=["CREATE_ORDER"],
        valid_until=datetime.now(UTC) + timedelta(days=30),
    )
    operation = FinancialOperation(
        operation_id="op_2",
        idempotency_key="idemp_2",
        agent_id="ag_1",
        mandate_id="mand_1",
        operation_type=OperationType.CREATE_ORDER,
        amount=10000,  # Exceeds 5000
        currency="INR",
    )

    result = await engine.evaluate(agent, mandate, operation)
    assert result.approved is False
    assert any("exceeds per-transaction limit" in r for r in result.rejection_reasons)


@pytest.mark.asyncio
async def test_policy_engine_rejection_unauthorized_op() -> None:
    engine = PolicyEngine()
    agent = Agent(
        id="ag_1", name="Bot 1", owner_id="usr_1", status=AgentStatus.ACTIVE, api_key_hash="hash_1"
    )
    mandate = Mandate(
        id="mand_1",
        agent_id="ag_1",
        granted_by_id="usr_1",
        status=MandateStatus.ACTIVE,
        currency="INR",
        max_amount_per_op=50000,
        aggregate_spend_limit=500000,
        current_aggregate_spend=0,
        reserved_spend=0,
        allowed_operations=["CREATE_ORDER"],  # CREATE_REFUND not allowed
        valid_until=datetime.now(UTC) + timedelta(days=30),
    )
    operation = FinancialOperation(
        operation_id="op_3",
        idempotency_key="idemp_3",
        agent_id="ag_1",
        mandate_id="mand_1",
        operation_type=OperationType.CREATE_REFUND,
        amount=1000,
        currency="INR",
    )

    result = await engine.evaluate(agent, mandate, operation)
    assert result.approved is False
    assert any("not authorized" in r for r in result.rejection_reasons)
